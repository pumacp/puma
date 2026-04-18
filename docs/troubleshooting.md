# Troubleshooting

## Docker issues

### `docker compose run` fails with "no such service"

Check you are in the repo root (where `docker-compose.yml` lives) and that you typed the service name correctly: `puma_runner`, not `puma-runner`.

### Container exits immediately

Run with `docker compose logs puma_runner` to see the error. Common causes:
- Missing `requirements.txt` — regenerate with `pip freeze > requirements.txt` inside a working container.
- Syntax error in a Python file introduced before the image was rebuilt: `docker compose build puma_runner`.

### Port 11434 already in use

Another Ollama instance is running locally. Either stop it (`pkill ollama`) or change the port mapping in `docker-compose.yml`.

---

## Ollama issues

### `ollama: command not found` inside the runner container

The runner container does not bundle Ollama. Use the `puma_ollama` service for inference. Ensure `OLLAMA_HOST=http://puma_ollama:11434` is set (already in `docker-compose.yml`).

### Model not found: `pull model manifest: file does not exist`

Pull the model first:

```bash
docker compose run --rm puma_runner puma models pull qwen2.5:3b
```

Or from the host: `ollama pull qwen2.5:3b` (if Ollama is installed locally and shares the volume).

---

## Dataset issues

### `FileNotFoundError: data/jira_balanced_200.csv`

Run the dataset download step:

```bash
docker compose run --rm puma_runner python scripts/download_datasets.py
```

### `verify_jira` fails with checksum mismatch

The CSV may have been modified. Re-download: delete `data/jira_balanced_200.csv` and re-run the download script.

---

## Test failures

### `UNIQUE constraint failed: instances.dataset, instances.source_id`

The database already contains predictions for the same instance from a prior run. Use a fresh `tmp_path` DB in tests (already enforced in unit tests via `tmp_path` fixture).

### `NotADirectoryError` in preflight tests on CI

The host `ollama` binary path collides with a directory. Fixed in `detect.py` by catching `NotADirectoryError`.

---

## CLI issues

### `puma: command not found`

The package is not installed. Inside Docker it is on `PATH` via the pip install. Locally, activate the virtualenv or run `pip install -e .`.

### `Invalid run-spec: 1 validation error for RunSpec`

Check the YAML against `src/puma/orchestrator/runspec.py`:
- `scenario` must be one of `triage_jira`, `estimation_tawos`, `prioritization_jira`.
- `models` must be a non-empty list.
- `sample_size` must be between 1 and 10 000.
- `self-consistency` strategy requires `temperature > 0`.

---

## Performance

### Inference is very slow (>5 min per instance)

- Check that the correct hardware profile was selected: `puma preflight`.
- Ensure the model fits in RAM/VRAM: `puma models list` shows size requirements.
- For CPU-only machines, use models ≤7B parameters.

### High parse failure rate (>20%)

- Increase `max_tokens` in the run-spec (`inference.max_tokens: 512`).
- Switch to a simpler prompting strategy (zero-shot before few-shot).
- Check that prompt templates exist for your scenario and strategy.
