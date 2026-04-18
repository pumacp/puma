"""Runner: orchestrates dataset → prompt → inference → parse → persist → metrics."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from puma.orchestrator.runspec import RunSpec

logger = structlog.get_logger(__name__)

RESULTS_ROOT = Path("results")


class Runner:
    """Execute a RunSpec end-to-end and persist results to SQLite + results/<run_id>/."""

    def __init__(
        self,
        spec: RunSpec,
        *,
        db_path: Path | str = "data/puma.db",
        ollama_host: str = "http://localhost:11434",
        dry_run: bool = False,
    ) -> None:
        self.spec = spec
        self.db_path = Path(db_path)
        self.ollama_host = ollama_host
        self.dry_run = dry_run
        self.run_id = f"{spec.id}__{spec.spec_hash()}__{_ts()}"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Execute the full run. Returns a summary dict."""
        from puma.storage.db import init_db, session_scope
        from puma.storage.models import Metric, Run

        init_db(self.db_path)
        results_dir = RESULTS_ROOT / self.run_id
        results_dir.mkdir(parents=True, exist_ok=True)

        _save_frozen_spec(self.spec, results_dir)

        logger.info("run.start", run_id=self.run_id, spec_hash=self.spec.spec_hash())

        with session_scope() as db:
            run_record = Run(
                run_id=self.run_id,
                spec_hash=self.spec.spec_hash(),
                spec_yaml=json.dumps(self.spec.model_dump(), default=str),
                profile=self.spec.profile_required,
                started_at=datetime.now(UTC),
                status="running",
            )
            db.add(run_record)

        predictions: list[dict] = []
        start_wall = time.time()

        try:
            predictions = self._execute_inferences(results_dir)
        except Exception as exc:
            logger.error("run.error", run_id=self.run_id, error=str(exc))
            with session_scope() as db:
                r = db.get(Run, self.run_id)
                if r:
                    r.status = "error"
                    r.finished_at = datetime.now(UTC)
            raise

        duration_s = time.time() - start_wall
        metrics = self._compute_metrics(predictions)
        self._persist_metrics(metrics, results_dir)
        self._persist_predictions(predictions)

        with session_scope() as db:
            r = db.get(Run, self.run_id)
            if r:
                r.status = "done"
                r.finished_at = datetime.now(UTC)
            for metric_name, value in _flatten_metrics(metrics):
                db.add(Metric(
                    run_id=self.run_id,
                    scope="global",
                    metric_name=metric_name,
                    value=float(value),
                ))
            _add_profile_snapshot(db, self.run_id)

        _save_metrics_json(metrics, results_dir)
        logger.info("run.end", run_id=self.run_id, duration_s=round(duration_s, 1),
                    n_predictions=len(predictions))
        return {"run_id": self.run_id, "metrics": metrics, "n_predictions": len(predictions)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_inferences(self, results_dir: Path) -> list[dict]:
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        from puma.adaptation.strategies import get_strategy
        from puma.runtime.cache import InferenceCache
        from puma.runtime.client import OllamaClient
        from puma.scenarios.estimation_tawos import EstimationTawosScenario
        from puma.scenarios.prioritization_jira import PrioritizationJiraScenario
        from puma.scenarios.triage_jira import TriageJiraScenario

        scenario_map = {
            "triage_jira": TriageJiraScenario,
            "estimation_tawos": EstimationTawosScenario,
            "prioritization_jira": PrioritizationJiraScenario,
        }
        scenario = scenario_map[self.spec.scenario]()

        try:
            df = scenario.sample(self.spec.sample_size, seed=self.spec.inference.seed)
        except Exception as exc:
            logger.warning("dataset.sample_failed", error=str(exc))
            df = _empty_dataframe()

        client = OllamaClient(
            base_url=self.ollama_host,
            timeout_s=120.0,
        )
        InferenceCache(db_path=Path("data/cache/inferences.db"))

        perturb_fns = _build_perturbation_fns(
            self.spec.perturbations, self.spec.inference.seed
        )

        all_predictions: list[dict] = []
        rows = df.to_dict("records")
        total_tasks = len(rows) * len(self.spec.models) * len(self.spec.adaptation.strategy)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:
            task_id = progress.add_task(f"[cyan]{self.run_id}", total=total_tasks)

            for model in self.spec.models:
                for strategy_name in self.spec.adaptation.strategy:
                    strategy = get_strategy(strategy_name)
                    for row in rows:
                        instance = dict(row)
                        gold = str(scenario.gold_label(instance))

                        for perturb_name, perturb_fn in [("original", None)] + list(perturb_fns.items()):  # noqa: E501
                            perturbed = _apply_perturbation(instance, perturb_fn)
                            prompt = strategy.build_prompt(scenario, perturbed)
                            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

                            if self.dry_run:
                                raw_response = "[dry-run]"
                                latency_ms = 0.0
                                tokens_in = tokens_out = 0
                            else:
                                t0 = time.time()
                                try:
                                    result = client.generate_sync(
                                        model=model,
                                        prompt=prompt,
                                        temperature=self.spec.inference.temperature,
                                        seed=self.spec.inference.seed,
                                        max_tokens=self.spec.inference.max_tokens,
                                        logprobs=self.spec.inference.logprobs,
                                        top_logprobs=self.spec.inference.top_logprobs,
                                    )
                                    raw_response = result.response
                                    latency_ms = (time.time() - t0) * 1000
                                    tokens_in = result.prompt_eval_count
                                    tokens_out = result.eval_count
                                except Exception as exc:
                                    logger.warning("inference.error", model=model, error=str(exc))
                                    raw_response = ""
                                    latency_ms = (time.time() - t0) * 1000
                                    tokens_in = tokens_out = 0

                            parsed = scenario.parse_response(raw_response)
                            all_predictions.append({
                                "run_id": self.run_id,
                                "instance_id": str(row.get("issue_key", row.get("item_id", uuid.uuid4().hex[:8]))),
                                "model": model,
                                "strategy": strategy_name,
                                "prompt_hash": prompt_hash,
                                "raw_response": raw_response,
                                "parsed_label": str(parsed) if parsed is not None else None,
                                "gold_label": gold,
                                "latency_ms": latency_ms,
                                "tokens_in": tokens_in,
                                "tokens_out": tokens_out,
                                "perturbation": perturb_name if perturb_name != "original" else None,
                                "seed": self.spec.inference.seed,
                            })

                        progress.advance(task_id)

        return all_predictions

    def _compute_metrics(self, predictions: list[dict]) -> dict[str, Any]:
        from puma.metrics.accuracy import classification_metrics, regression_metrics
        from puma.metrics.efficiency import percentiles

        if not predictions:
            return {}

        orig = [p for p in predictions if p["perturbation"] is None]
        if not orig:
            orig = predictions

        y_true = [p["gold_label"] for p in orig if p["parsed_label"] is not None]
        y_pred = [p["parsed_label"] for p in orig if p["parsed_label"] is not None]

        if not y_true:
            return {"parse_failure_rate": 1.0}

        result: dict[str, Any] = {}
        scenario = self.spec.scenario

        if scenario == "triage_jira":
            labels = ["Critical", "Major", "Minor", "Trivial"]
            result.update(classification_metrics(y_true, y_pred, labels))
        elif scenario == "estimation_tawos":
            try:
                yt = [float(v) for v in y_true]
                yp = [float(v) for v in y_pred]
                result.update(regression_metrics(yt, yp))
            except ValueError:
                result["parse_error"] = "could not convert to float"
        else:
            result["accuracy"] = sum(a == b for a, b in zip(y_true, y_pred, strict=False)) / len(y_true)

        latencies = [p["latency_ms"] for p in orig if p.get("latency_ms") is not None]
        if latencies:
            result["latency"] = percentiles(latencies)

        parse_failures = sum(1 for p in orig if p["parsed_label"] is None)
        result["parse_failure_rate"] = parse_failures / len(orig) if orig else 0.0
        result["n_predictions"] = len(orig)

        return result

    def _persist_predictions(self, predictions: list[dict]) -> None:
        from puma.storage.db import session_scope
        from puma.storage.models import Instance, Prediction

        with session_scope() as db:
            seen_instances: set[str] = set()
            for p in predictions:
                iid = p["instance_id"]
                if iid not in seen_instances and not db.get(Instance, iid):
                    seen_instances.add(iid)
                    db.add(Instance(
                        instance_id=iid,
                        dataset=self.spec.scenario,
                        source_id=iid,
                        input_text="",
                        gold_label=p["gold_label"],
                    ))
                db.add(Prediction(
                    run_id=p["run_id"],
                    instance_id=iid,
                    model=p["model"],
                    strategy=p["strategy"],
                    prompt_hash=p["prompt_hash"],
                    raw_response=p["raw_response"],
                    parsed_label=p["parsed_label"],
                    latency_ms=p["latency_ms"],
                    tokens_in=p["tokens_in"],
                    tokens_out=p["tokens_out"],
                    perturbation=p["perturbation"],
                    seed=p["seed"],
                ))

    def _persist_metrics(self, metrics: dict, results_dir: Path) -> None:
        pass  # JSON saved separately; SQLAlchemy rows added in run()


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S")


def _save_frozen_spec(spec: RunSpec, results_dir: Path) -> None:
    import yaml
    path = results_dir / "runspec.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(spec.model_dump(mode="json"), fh, default_flow_style=False)


def _save_metrics_json(metrics: dict, results_dir: Path) -> None:
    path = results_dir / "metrics.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, default=str)


def _empty_dataframe():
    import pandas as pd
    return pd.DataFrame()


def _build_perturbation_fns(perturbations: list[str], seed: int) -> dict:
    from puma.perturbations.text import case_change, tech_noise, truncate, typos

    fns = {}
    for name in perturbations:
        if name == "typos_5pct":
            fns[name] = lambda text, s=seed: typos(text, rate=0.05, seed=s)
        elif name == "case_upper":
            fns[name] = lambda text: case_change(text, mode="upper")
        elif name == "case_lower":
            fns[name] = lambda text: case_change(text, mode="lower")
        elif name == "truncate_50pct":
            fns[name] = lambda text: truncate(text, keep=0.5, from_="end")
        elif name == "tech_noise":
            fns[name] = lambda text, s=seed: tech_noise(text, seed=s)
    return fns


def _apply_perturbation(instance: dict, perturb_fn) -> dict:
    if perturb_fn is None:
        return instance
    perturbed = dict(instance)
    for key in ("title", "description", "summary"):
        if key in perturbed and isinstance(perturbed[key], str):
            perturbed[key] = perturb_fn(perturbed[key])
    return perturbed


def _flatten_metrics(metrics: dict, prefix: str = "") -> list[tuple[str, float]]:
    result = []
    for k, v in metrics.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, (int, float)):
            result.append((full_key, float(v)))
        elif isinstance(v, dict):
            result.extend(_flatten_metrics(v, prefix=full_key))
    return result


def _add_profile_snapshot(db, run_id: str) -> None:
    from puma.storage.models import ProfileSnapshot

    try:
        from puma.preflight.detect import detect_capabilities
        caps = detect_capabilities()
        db.add(ProfileSnapshot(
            run_id=run_id,
            os=caps.os_system,
            cpu=caps.cpu_model,
            ram_gb=caps.ram_total_gb,
            gpu=caps.gpu_name,
            vram_gb=caps.gpu_vram_gb,
            ollama_version=caps.ollama_version,
            puma_version="2.0.0-dev",
        ))
    except Exception:
        db.add(ProfileSnapshot(run_id=run_id, puma_version="2.0.0-dev"))
