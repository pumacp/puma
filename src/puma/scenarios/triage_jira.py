"""Triage scenario: multi-class priority classification on Jira issues."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from puma.scenarios.base import Scenario

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
JIRA_INPUT = DATA_DIR / "jira_balanced_200.csv"
CACHE_FILE = RESULTS_DIR / "triage_cache.json"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("LLM_MODEL", "qwen2.5:3b")

TRIAGE_TARGET_F1 = float(os.environ.get("TRIAGE_TARGET_F1", "0.55"))
TRIAGE_TEMPERATURE = float(os.environ.get("TRIAGE_TEMPERATURE", "0.0"))
TRIAGE_SEED = int(os.environ.get("TRIAGE_SEED", "42"))

SYSTEM_PROMPT = (
    "You are an expert in ICT project management. "
    "Analyze the title and description of the issue and respond ONLY "
    "with one of these exact words: Critical, Major, Minor or Trivial. "
    "Do not add any explanation or extra punctuation."
)

DETERMINISTIC_OPTIONS = {
    "temperature": TRIAGE_TEMPERATURE,
    "seed": TRIAGE_SEED,
    "num_predict": 10,
}

VALID_PRIORITIES = ["Critical", "Major", "Minor", "Trivial"]

_PRIORITY_RE = re.compile(r"\b(critical|major|minor|trivial)\b", re.IGNORECASE)


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            logger.warning("Triage cache corrupted, starting fresh")
    return {}


def _save_cache(cache: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def parse_prediction(response: str) -> str | None:
    m = _PRIORITY_RE.search(response)
    if m:
        return m.group(0).capitalize()
    logger.warning("Could not parse triage response: %r", response)
    return None


class TriageJiraScenario(Scenario):
    """Multi-class priority classification on Jira Social Repository issues."""

    name = "triage_jira"
    dataset = "jira_sr"
    task_type = "classification"
    labels = VALID_PRIORITIES

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        from puma.datasets.jira_sr import load, sample

        return sample(load(), n, seed=seed)

    def parse_response(self, raw: str) -> str | None:
        return parse_prediction(raw)

    def gold_label(self, instance: dict) -> str:
        return str(instance.get("priority", ""))


class TriageEvaluator:
    def __init__(self, model: str = MODEL_NAME) -> None:
        import ollama

        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = model
        logger.info("TriageEvaluator initialized with model: %s", model)

    def evaluate_issue(self, issue_key: str, title: str, description: str) -> str | None:
        prompt = f"Title: {title}\n\nDescription: {description}"
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options=DETERMINISTIC_OPTIONS,
            )
            return parse_prediction(response["message"]["content"])
        except Exception as exc:
            logger.error("Error evaluating issue %s: %s", issue_key, exc)
            return None

    def evaluate_batch(self, df: pd.DataFrame) -> list:
        cache = _load_cache()
        results = []
        processed = skipped = 0

        for idx, row in df.iterrows():
            issue_key = str(row.get("issue_key", f"issue_{idx}"))
            if issue_key in cache:
                skipped += 1
                results.append({
                    "issue_key": issue_key,
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "priority": row.get("priority", ""),
                    "prediction": cache[issue_key]["prediction"],
                })
                continue

            prediction = self.evaluate_issue(
                issue_key,
                str(row.get("title", "")),
                str(row.get("description", "")),
            )
            entry = {
                "issue_key": issue_key,
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "priority": row.get("priority", ""),
                "prediction": prediction,
            }
            cache[issue_key] = {"priority": entry["priority"], "prediction": prediction}
            results.append(entry)
            processed += 1
            if processed % 10 == 0:
                _save_cache(cache)

        _save_cache(cache)
        logger.info("Triage batch done: %d new, %d cached", processed, skipped)
        return results


def calculate_metrics(results: list) -> dict:
    y_true = [r["priority"] for r in results if r["priority"] and r["prediction"]]
    y_pred = [r["prediction"] for r in results if r["priority"] and r["prediction"]]
    if not y_true:
        return {}

    return {
        "f1_macro": f1_score(y_true, y_pred, labels=VALID_PRIORITIES, average="macro"),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=VALID_PRIORITIES).tolist(),
        "labels": VALID_PRIORITIES,
        "classification_report": classification_report(
            y_true, y_pred, labels=VALID_PRIORITIES, output_dict=True
        ),
        "total_samples": len(y_true),
        "model": MODEL_NAME,
        "options": DETERMINISTIC_OPTIONS,
    }
