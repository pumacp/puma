"""Estimation scenario: story-point regression on TAWOS issues."""

import json
import logging
import os
import re
import signal
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
TAWOS_INPUT = DATA_DIR / "tawos_clean.csv"
CACHE_FILE = RESULTS_DIR / "estimation_cache.json"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("LLM_MODEL", "qwen2.5:3b")

ESTIMATION_TARGET_MAE = float(os.environ.get("ESTIMATION_TARGET_MAE", "3.0"))
ESTIMATION_PROJECT = os.environ.get("ESTIMATION_PROJECT", "MESOS")
ESTIMATION_TEMPERATURE = float(os.environ.get("ESTIMATION_TEMPERATURE", "0.0"))
ESTIMATION_SEED = int(os.environ.get("ESTIMATION_SEED", "42"))
ESTIMATION_NUM_ITEMS = int(os.environ.get("ESTIMATION_NUM_ITEMS", "0"))
EVALUATION_TIMEOUT = int(os.environ.get("EVALUATION_TIMEOUT", "0"))

DETERMINISTIC_OPTIONS = {
    "temperature": ESTIMATION_TEMPERATURE,
    "seed": ESTIMATION_SEED,
    "num_predict": 50,
}

FIBONACCI_SERIES = [1, 2, 3, 5, 8, 13, 21]

FEW_SHOT_EXAMPLES = [
    {
        "title": "Fix typo in login button label",
        "description": "The login button text says 'Subit' instead of 'Submit'. Minor cosmetic issue.",
        "story_points": 1,
    },
    {
        "title": "Implement user session timeout",
        "description": (
            "Users are logged out after 30 minutes of inactivity. Need to add session "
            "management and redirect to login page. Include unit tests for session validation."
        ),
        "story_points": 5,
    },
    {
        "title": "Design and implement microservices architecture",
        "description": (
            "Migrate monolithic application to microservices. Include API gateway, service "
            "discovery, load balancing, and database sharding. Must maintain backward "
            "compatibility during transition."
        ),
        "story_points": 21,
    },
]

SYSTEM_PROMPT = (
    "You are an expert in agile effort estimation. "
    "Analyze the title and description of the user story. "
    "Respond ONLY with an integer representing Story Points. "
    "Story Points follow the modified Fibonacci series: 1, 2, 3, 5, 8, 13, 21. "
    "Do not add any explanation or extra text."
)


def _build_few_shot_prompt(title: str, description: str) -> str:
    examples = "\n".join(
        f"\nExample {i}:\nTitle: {ex['title']}\nDescription: {ex['description']}\n"
        f"Story Points: {ex['story_points']}"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1)
    )
    return f"{examples}\n\nNow estimate:\nTitle: {title}\nDescription: {description}\nStory Points:"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            logger.warning("Estimation cache corrupted, starting fresh")
    return {}


def _save_cache(cache: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)


def parse_story_points(response: str) -> float | None:
    numbers = re.findall(r"\d+\.?\d*", response.strip())
    if not numbers:
        return None
    try:
        value = float(numbers[0])
        if value in FIBONACCI_SERIES:
            return value
        closest = min(FIBONACCI_SERIES, key=lambda x: abs(x - value))
        return closest if abs(closest - value) <= 1 else value
    except ValueError:
        return None


class EstimationEvaluator:
    def __init__(self, model: str = MODEL_NAME, timeout: int = 0) -> None:
        import ollama

        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = model
        self.timeout = timeout
        self.start_time = time.time()
        self._shutdown = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        logger.info("EstimationEvaluator initialized with model: %s", model)

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Shutdown signal received")
        self._shutdown = True

    def _timed_out(self) -> bool:
        return self.timeout > 0 and (time.time() - self.start_time) >= self.timeout

    def evaluate_item(self, item_id: str, title: str, description: str) -> float | None:
        if self._shutdown or self._timed_out():
            return None
        prompt = _build_few_shot_prompt(title, description)
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options=DETERMINISTIC_OPTIONS,
            )
            return parse_story_points(response["message"]["content"])
        except Exception as exc:
            logger.error("Error evaluating item %s: %s", item_id, exc)
            return None

    def evaluate_batch(
        self, df: pd.DataFrame, project_filter: str | None = None, max_items: int = 0
    ) -> list:
        cache = _load_cache()
        if project_filter:
            df = df[df.get("project", "Unknown") == project_filter].copy()
        if max_items > 0:
            df = df.head(max_items)

        results = []
        processed = skipped = 0

        for idx, row in df.iterrows():
            if self._shutdown or self._timed_out():
                break
            item_id = str(row.get("item_id", f"item_{idx}"))
            if item_id in cache and cache[item_id].get("prediction") is not None:
                skipped += 1
                results.append({
                    "item_id": item_id,
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "story_points": cache[item_id].get("story_points", row.get("story_points", 0)),
                    "prediction": cache[item_id]["prediction"],
                })
                continue

            prediction = self.evaluate_item(
                item_id, str(row.get("title", "")), str(row.get("description", ""))
            )
            entry = {
                "item_id": item_id,
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "story_points": row.get("story_points", 0),
                "prediction": prediction,
            }
            cache[item_id] = {"story_points": entry["story_points"], "prediction": prediction}
            results.append(entry)
            processed += 1
            if processed % 10 == 0:
                _save_cache(cache)

        _save_cache(cache)
        logger.info("Estimation batch done: %d new, %d cached", processed, skipped)
        return results


def calculate_metrics(results: list) -> dict:
    pairs = [(r["story_points"], r["prediction"]) for r in results if r["prediction"] is not None]
    if not pairs:
        return {}
    y_true, y_pred = zip(*pairs, strict=True)
    errors = [abs(t - p) for t, p in zip(y_true, y_pred, strict=True)]
    return {
        "mae": mean_absolute_error(list(y_true), list(y_pred)),
        "mdae": sorted(errors)[len(errors) // 2],
        "total_samples": len(pairs),
        "model": MODEL_NAME,
        "options": DETERMINISTIC_OPTIONS,
        "few_shot_examples": len(FEW_SHOT_EXAMPLES),
    }


class EstimationTawosScenario:
    """Story-point regression on TAWOS issues — Scenario interface."""

    name = "estimation_tawos"
    dataset = "tawos"
    task_type = "regression"
    labels: list = []

    def sample(self, n: int, seed: int = 42) -> pd.DataFrame:
        from puma.datasets.tawos import load, sample

        return sample(load(), n, seed=seed)

    def parse_response(self, raw: str) -> float | None:
        return parse_story_points(raw)

    def gold_label(self, instance: dict) -> float:
        return float(instance.get("story_points", 0))
