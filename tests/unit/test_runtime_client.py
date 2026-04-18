"""Unit tests for puma.runtime.client — Ollama HTTP client (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from puma.runtime.client import GenerationResult, OllamaClient, TokenLogprob


@pytest.mark.unit
class TestTokenLogprob:
    def test_basic_fields(self):
        tl = TokenLogprob(token="Critical", logprob=-0.1, top_logprobs=[])
        assert tl.token == "Critical"
        assert tl.logprob == -0.1

    def test_frozen(self):
        tl = TokenLogprob(token="A", logprob=-1.0, top_logprobs=[])
        with pytest.raises((AttributeError, TypeError)):
            tl.token = "B"  # type: ignore[misc]


@pytest.mark.unit
class TestGenerationResult:
    def test_fields_accessible(self):
        gr = GenerationResult(
            model="qwen2.5:3b",
            response="Critical",
            logprobs=[],
            total_duration_ns=1_000_000,
            load_duration_ns=500_000,
            prompt_eval_count=10,
            eval_count=1,
            eval_duration_ns=200_000,
            raw={},
        )
        assert gr.model == "qwen2.5:3b"
        assert gr.response == "Critical"

    def test_frozen(self):
        gr = GenerationResult(
            model="m", response="r", logprobs=[],
            total_duration_ns=0, load_duration_ns=0,
            prompt_eval_count=0, eval_count=0, eval_duration_ns=0, raw={},
        )
        with pytest.raises((AttributeError, TypeError)):
            gr.response = "hacked"  # type: ignore[misc]


@pytest.mark.unit
class TestOllamaClientSync:
    def _make_response_json(self, text="Critical"):
        return {
            "response": text,
            "model": "qwen2.5:3b",
            "total_duration": 1_000_000_000,
            "load_duration": 100_000_000,
            "prompt_eval_count": 10,
            "eval_count": 1,
            "eval_duration": 200_000_000,
        }

    def test_generate_sync_returns_generation_result(self):
        client = OllamaClient(base_url="http://localhost:11434")
        resp_json = self._make_response_json("Critical")

        with patch("httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = resp_json
            mock_response.raise_for_status = MagicMock()
            mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response

            result = client.generate_sync(
                model="qwen2.5:3b",
                prompt="Classify this issue",
                temperature=0.0,
                seed=42,
            )

        assert isinstance(result, GenerationResult)
        assert result.response == "Critical"
        assert result.model == "qwen2.5:3b"

    def test_generate_sync_payload_contains_options(self):
        client = OllamaClient(base_url="http://localhost:11434")
        captured_payload = {}

        def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": "ok", "model": "m",
                "total_duration": 0, "load_duration": 0,
                "prompt_eval_count": 0, "eval_count": 0, "eval_duration": 0,
            }
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.side_effect = capture_post
            client.generate_sync(
                model="qwen2.5:3b", prompt="test",
                temperature=0.0, seed=42, max_tokens=10,
            )

        assert "options" in captured_payload
        assert captured_payload["options"]["temperature"] == 0.0
        assert captured_payload["options"]["seed"] == 42

    def test_logprobs_flag_added_when_requested(self):
        client = OllamaClient(base_url="http://localhost:11434")
        captured_payload = {}

        def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "response": "ok", "model": "m",
                "total_duration": 0, "load_duration": 0,
                "prompt_eval_count": 0, "eval_count": 0, "eval_duration": 0,
            }
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.side_effect = capture_post
            client.generate_sync(
                model="qwen2.5:3b", prompt="test",
                temperature=0.0, seed=42, logprobs=True, top_logprobs=5,
            )

        assert captured_payload.get("logprobs") is True
        assert captured_payload.get("top_logprobs") == 5
