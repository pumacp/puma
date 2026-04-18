"""Integration tests — OllamaClient against a real Ollama server."""

from __future__ import annotations

import time

import pytest

from puma.runtime.cache import InferenceCache
from puma.runtime.client import GenerationResult, OllamaClient


@pytest.mark.integration
@pytest.mark.ollama
class TestOllamaClientReal:
    """Requires Ollama running with qwen2.5:1.5b or qwen2.5:3b available."""

    def _client(self):
        import os
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        return OllamaClient(base_url=host, timeout_s=120.0)

    def _model(self):
        import os
        return os.environ.get("LLM_MODEL", "qwen2.5:3b")

    def test_generate_sync_returns_result(self):
        client = self._client()
        result = client.generate_sync(
            model=self._model(),
            prompt="Respond with only the word: Critical",
            temperature=0.0,
            seed=42,
            max_tokens=10,
        )
        assert isinstance(result, GenerationResult)
        assert len(result.response) > 0
        assert result.eval_count > 0

    def test_generate_sync_with_logprobs(self):
        client = self._client()
        result = client.generate_sync(
            model=self._model(),
            prompt="Respond with only the word: Critical",
            temperature=0.0,
            seed=42,
            max_tokens=10,
            logprobs=True,
            top_logprobs=5,
        )
        assert isinstance(result, GenerationResult)
        assert result.response != ""

    def test_determinism_same_seed(self):
        client = self._client()
        r1 = client.generate_sync(
            model=self._model(), prompt="Classify: bug", temperature=0.0, seed=42, max_tokens=5
        )
        r2 = client.generate_sync(
            model=self._model(), prompt="Classify: bug", temperature=0.0, seed=42, max_tokens=5
        )
        assert r1.response == r2.response

    def test_cache_accelerates_second_call(self, tmp_path):
        client = self._client()
        cache = InferenceCache(db_path=tmp_path / "test.db")
        model = self._model()
        prompt = "Test cache speed"

        key = cache.build_key(model, prompt, 0.0, 42, False, None)

        t0 = time.perf_counter()
        result = client.generate_sync(model=model, prompt=prompt, temperature=0.0, seed=42, max_tokens=5)
        first_ms = (time.perf_counter() - t0) * 1000

        cache.put(key, result)

        t1 = time.perf_counter()
        cached = cache.get(key)
        cache_ms = (time.perf_counter() - t1) * 1000

        assert cached is not None
        assert cached.response == result.response
        assert cache_ms < 10  # cache hit < 10 ms
        assert cache_ms < first_ms
