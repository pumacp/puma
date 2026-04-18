"""Unit tests for puma.runtime.cache — inference cache."""

from __future__ import annotations

import time

import pytest

from puma.runtime.cache import InferenceCache
from puma.runtime.client import GenerationResult


def _make_result(response="Critical") -> GenerationResult:
    return GenerationResult(
        model="qwen2.5:3b", response=response, logprobs=[],
        total_duration_ns=1_000_000, load_duration_ns=0,
        prompt_eval_count=5, eval_count=1, eval_duration_ns=200_000, raw={},
    )


@pytest.mark.unit
class TestInferenceCache:
    def test_miss_returns_none(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        assert cache.get("nonexistent-key") is None

    def test_put_then_get(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        result = _make_result("Critical")
        cache.put("key1", result)
        retrieved = cache.get("key1")
        assert retrieved is not None
        assert retrieved.response == "Critical"
        assert retrieved.model == "qwen2.5:3b"

    def test_cache_hit_fast(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        result = _make_result("Major")
        cache.put("fast-key", result)

        start = time.perf_counter()
        retrieved = cache.get("fast-key")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert retrieved is not None
        assert elapsed_ms < 50  # cache hit must be well under 50 ms

    def test_stats_returns_dict(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        stats = cache.stats()
        assert "total_entries" in stats
        assert stats["total_entries"] == 0

    def test_stats_count_after_put(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        cache.put("k1", _make_result())
        cache.put("k2", _make_result("Minor"))
        assert cache.stats()["total_entries"] == 2

    def test_clear_empties_cache(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        cache.put("k1", _make_result())
        cache.clear()
        assert cache.stats()["total_entries"] == 0
        assert cache.get("k1") is None

    def test_overwrite_existing_key(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        cache.put("k", _make_result("Critical"))
        cache.put("k", _make_result("Major"))
        assert cache.get("k").response == "Major"

    def test_build_key_deterministic(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        k1 = cache.build_key("model", "prompt", 0.0, 42, False, None)
        k2 = cache.build_key("model", "prompt", 0.0, 42, False, None)
        assert k1 == k2

    def test_build_key_differs_on_param_change(self, tmp_path):
        cache = InferenceCache(db_path=tmp_path / "test.db")
        k1 = cache.build_key("model", "prompt", 0.0, 42, False, None)
        k2 = cache.build_key("model", "prompt", 0.7, 42, False, None)
        assert k1 != k2
