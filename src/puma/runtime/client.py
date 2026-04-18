"""Ollama HTTP client with logprobs, retries, and sync/async interfaces."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {500, 502, 503, 504}


@dataclass(frozen=True)
class TokenLogprob:
    token: str
    logprob: float
    top_logprobs: list[TokenLogprob] = field(default_factory=list)


@dataclass(frozen=True)
class GenerationResult:
    model: str
    response: str
    logprobs: list[TokenLogprob]
    total_duration_ns: int
    load_duration_ns: int
    prompt_eval_count: int
    eval_count: int
    eval_duration_ns: int
    raw: dict


def _parse_logprobs(raw: dict) -> list[TokenLogprob]:
    """Parse Ollama logprobs payload into TokenLogprob list."""
    tokens = raw.get("logprobs") or []
    if not tokens:
        return []
    result = []
    for tok in tokens:
        top = [
            TokenLogprob(token=t["token"], logprob=t["logprob"], top_logprobs=[])
            for t in (tok.get("top_logprobs") or [])
        ]
        result.append(TokenLogprob(token=tok["token"], logprob=tok["logprob"], top_logprobs=top))
    return result


def _build_payload(
    model: str,
    prompt: str,
    *,
    temperature: float,
    seed: int,
    max_tokens: int,
    logprobs: bool,
    top_logprobs: int,
    format: dict | str | None,
    system: str | None,
    stream: bool,
) -> dict:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system
    if format is not None:
        payload["format"] = format
    if logprobs:
        payload["logprobs"] = True
        payload["top_logprobs"] = top_logprobs
    return payload


def _result_from_json(raw: dict) -> GenerationResult:
    return GenerationResult(
        model=raw.get("model", ""),
        response=raw.get("response", ""),
        logprobs=_parse_logprobs(raw),
        total_duration_ns=raw.get("total_duration", 0),
        load_duration_ns=raw.get("load_duration", 0),
        prompt_eval_count=raw.get("prompt_eval_count", 0),
        eval_count=raw.get("eval_count", 0),
        eval_duration_ns=raw.get("eval_duration", 0),
        raw=raw,
    )


class OllamaClient:
    """Synchronous and asynchronous Ollama client with retry logic."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 120.0,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.retries = retries

    def generate_sync(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        seed: int = 42,
        max_tokens: int = 256,
        logprobs: bool = False,
        top_logprobs: int = 0,
        format: dict | str | None = None,
        system: str | None = None,
    ) -> GenerationResult:
        """Synchronous generate call with retries."""
        payload = _build_payload(
            model, prompt,
            temperature=temperature, seed=seed, max_tokens=max_tokens,
            logprobs=logprobs, top_logprobs=top_logprobs,
            format=format, system=system, stream=False,
        )
        url = f"{self.base_url}/api/generate"
        last_exc: Exception | None = None

        for attempt in range(self.retries):
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.post(url, json=payload)
                    if response.status_code in _RETRY_STATUSES:
                        wait = 2 ** attempt
                        logger.warning("HTTP %s on attempt %d, retrying in %ds", response.status_code, attempt + 1, wait)
                        time.sleep(wait)
                        continue
                    response.raise_for_status()
                    raw = response.json()
                    logger.debug("inference done model=%s eval_count=%s", model, raw.get("eval_count"))
                    return _result_from_json(raw)
            except httpx.TimeoutException as exc:
                wait = 2 ** attempt
                logger.warning("Timeout on attempt %d, retrying in %ds", attempt + 1, wait)
                last_exc = exc
                time.sleep(wait)
            except httpx.HTTPStatusError as exc:
                logger.error("HTTP error: %s", exc)
                raise

        raise RuntimeError(f"Ollama request failed after {self.retries} retries") from last_exc

    async def generate(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        seed: int = 42,
        max_tokens: int = 256,
        logprobs: bool = False,
        top_logprobs: int = 0,
        format: dict | str | None = None,
        system: str | None = None,
    ) -> GenerationResult:
        """Async generate call with retries."""
        payload = _build_payload(
            model, prompt,
            temperature=temperature, seed=seed, max_tokens=max_tokens,
            logprobs=logprobs, top_logprobs=top_logprobs,
            format=format, system=system, stream=False,
        )
        url = f"{self.base_url}/api/generate"
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            for attempt in range(self.retries):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code in _RETRY_STATUSES:
                        wait = 2 ** attempt
                        logger.warning("HTTP %s retry in %ds", response.status_code, wait)
                        await asyncio.sleep(wait)
                        continue
                    response.raise_for_status()
                    raw = response.json()
                    return _result_from_json(raw)
                except httpx.TimeoutException as exc:
                    wait = 2 ** attempt
                    logger.warning("Timeout attempt %d, retry in %ds", attempt + 1, wait)
                    last_exc = exc
                    await asyncio.sleep(wait)

        raise RuntimeError(f"Ollama async request failed after {self.retries} retries") from last_exc
