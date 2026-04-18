"""SQLite-backed inference cache for GenerationResult objects."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from puma.runtime.client import GenerationResult, TokenLogprob

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path("data/cache/inferences.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS inferences (
    key      TEXT PRIMARY KEY,
    value    TEXT NOT NULL,
    created  REAL NOT NULL DEFAULT (unixepoch('now'))
);
"""


def _result_to_json(result: GenerationResult) -> str:
    def _logprob_to_dict(tl: TokenLogprob) -> dict:
        return {
            "token": tl.token,
            "logprob": tl.logprob,
            "top_logprobs": [_logprob_to_dict(t) for t in tl.top_logprobs],
        }

    data = {
        "model": result.model,
        "response": result.response,
        "logprobs": [_logprob_to_dict(tl) for tl in result.logprobs],
        "total_duration_ns": result.total_duration_ns,
        "load_duration_ns": result.load_duration_ns,
        "prompt_eval_count": result.prompt_eval_count,
        "eval_count": result.eval_count,
        "eval_duration_ns": result.eval_duration_ns,
        "raw": result.raw,
    }
    return json.dumps(data, ensure_ascii=False)


def _json_to_result(text: str) -> GenerationResult:
    data = json.loads(text)

    def _dict_to_logprob(d: dict) -> TokenLogprob:
        return TokenLogprob(
            token=d["token"],
            logprob=d["logprob"],
            top_logprobs=[_dict_to_logprob(t) for t in d.get("top_logprobs", [])],
        )

    return GenerationResult(
        model=data["model"],
        response=data["response"],
        logprobs=[_dict_to_logprob(t) for t in data.get("logprobs", [])],
        total_duration_ns=data["total_duration_ns"],
        load_duration_ns=data["load_duration_ns"],
        prompt_eval_count=data["prompt_eval_count"],
        eval_count=data["eval_count"],
        eval_duration_ns=data["eval_duration_ns"],
        raw=data.get("raw", {}),
    )


class InferenceCache:
    def __init__(self, db_path: Path = _DEFAULT_PATH) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    @staticmethod
    def build_key(
        model: str,
        prompt: str,
        temperature: float,
        seed: int,
        logprobs: bool,
        format_schema: Any,
    ) -> str:
        parts = f"{model}\x00{prompt}\x00{temperature}\x00{seed}\x00{logprobs}\x00{format_schema}"
        return hashlib.sha256(parts.encode()).hexdigest()

    def get(self, key: str) -> GenerationResult | None:
        try:
            row = self._conn.execute(
                "SELECT value FROM inferences WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return _json_to_result(row[0])
        except (sqlite3.DatabaseError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Cache read error for key %s: %s", key[:8], exc)
        return None

    def put(self, key: str, result: GenerationResult) -> None:
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO inferences (key, value) VALUES (?, ?)",
                (key, _result_to_json(result)),
            )
            self._conn.commit()
        except sqlite3.DatabaseError as exc:
            logger.warning("Cache write error: %s", exc)

    def stats(self) -> dict:
        count = self._conn.execute("SELECT COUNT(*) FROM inferences").fetchone()[0]
        size_bytes = self._path.stat().st_size if self._path.exists() else 0
        return {"total_entries": count, "db_size_bytes": size_bytes}

    def clear(self) -> None:
        self._conn.execute("DELETE FROM inferences")
        self._conn.commit()
        logger.info("Inference cache cleared")

    def close(self) -> None:
        self._conn.close()
