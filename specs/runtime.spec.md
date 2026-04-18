---
id: spec-runtime-v1
title: Runtime — Ollama HTTP Client and Inference Cache
phase: F2
status: approved
---

# Runtime Spec

## puma.runtime.client — OllamaClient

Async HTTP client over Ollama's `/api/generate` and `/api/chat` endpoints.

### Dataclasses
- `TokenLogprob(token, logprob, top_logprobs: list[TokenLogprob])`
- `GenerationResult(model, response, logprobs, total_duration_ns, load_duration_ns,
  prompt_eval_count, eval_count, eval_duration_ns, raw)`

### OllamaClient
- `__init__(base_url, timeout_s=120.0, retries=3)`
- `async generate(model, prompt, *, temperature, seed, max_tokens, logprobs,
  top_logprobs, format, system) -> GenerationResult`
- Retries with exponential backoff on 5xx / TimeoutException (max 3)
- Always passes `options: {temperature, seed, num_predict}` in payload
- Adds `logprobs: true, top_logprobs: N` at payload root when requested
- Sync wrapper `generate_sync(...)` for non-async callers

## puma.runtime.cache — InferenceCache

SQLite-backed cache at `data/cache/inferences.db`.

- Key: `sha256(model + prompt + str(temperature) + str(seed) + str(logprobs) + format_schema)`
- Value: serialized `GenerationResult` JSON
- `get(key) -> GenerationResult | None`
- `put(key, result) -> None`
- `stats() -> dict` — total entries, size on disk
- `clear() -> None`

## Gate checklist
- [ ] Unit tests with respx mock pass
- [ ] Integration test with real Ollama (qwen2.5:1.5b) returns logprobs
- [ ] Cache hit measured < 10 ms vs first call
