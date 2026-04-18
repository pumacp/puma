# Troubleshooting

Common problems encountered when running PUMA and how to fix them.

---

## Docker and container issues

### `puma: command not found` inside the container

The CLI entrypoint is registered via `pip install -e .` during the Docker image build. If you see this error, rebuild the image:

```bash
docker compose build puma_runner
docker compose run --rm puma_runner puma --help
```

### `docker compose run` exits immediately with no output

Check the container logs:

```bash
docker compose logs puma_runner
```

Common causes:
- A Python syntax error in a recently edited file — fix it and rebuild.
- `requirements.txt` is missing a dependency — add it and rebuild.

### `no such service: puma_runner`

You are not in the repository root (where `docker-compose.yml` lives). `cd` to the repo root and retry.

### Port 11434 already in use

A local Ollama instance is running alongside the Docker service. Options:

```bash
# Stop local Ollama
pkill ollama

# Or change the host-side port in docker-compose.yml
ports:
  - "11435:11434"   # use host port 11435 instead
```

### Port 8501 already in use (dashboard)

Change the dashboard port:

```bash
docker compose run --rm puma_runner puma dashboard --port 8502
# or edit docker-compose.yml: "8502:8501"
```

### Permission denied on `data/` or `results/`

Files written by a prior Docker run may be owned by root. Fix:

```bash
sudo chown -R $USER:$USER data/ results/
```

---

## Ollama issues

### `ollama: command not found` inside `puma_runner`

`puma_runner` does not bundle Ollama. All inference goes through the `puma_ollama` service at `http://puma_ollama:11434`. This is already set via the `OLLAMA_HOST` environment variable in `docker-compose.yml`.

To call Ollama directly:

```bash
docker compose exec puma_ollama ollama list
```

### `pull model manifest: file does not exist`

The model has not been pulled yet:

```bash
puma models pull qwen2.5:3b
# or
docker compose exec puma_ollama ollama pull qwen2.5:3b
```

### Inference returns empty or garbled responses

- The model may be loading from disk for the first time (cold start). Retry after 30 seconds.
- Check Ollama logs: `docker compose logs puma_ollama`.
- Increase the timeout in the run-spec: `inference.max_tokens: 512`.

### GPU not detected by Docker

Verify NVIDIA container toolkit is installed:

```bash
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

If this fails, install `nvidia-container-toolkit` following the official guide, then restart the Docker daemon.

AMD/ROCm: ensure `rocm-docker` is installed and the `puma_ollama` service includes the correct `devices` entry.

Apple Silicon: GPU acceleration works automatically through the `metal` backend inside the Ollama container; no extra configuration needed.

---

## Dataset issues

### `FileNotFoundError: data/jira_balanced_200.csv`

Download the datasets:

```bash
docker compose run --rm puma_runner python scripts/download_datasets.py
```

Or run the full verification which triggers download on failure:

```bash
./start_puma.sh --skip-models
```

### `puma datasets verify` fails with checksum mismatch

The CSV file has been modified since download. Re-download:

```bash
rm data/jira_balanced_200.csv
docker compose run --rm puma_runner python scripts/download_datasets.py
```

### TAWOS download blocked or extremely slow

TAWOS is a large dataset (~4.3 GB SQL dump). The `tawos_clean.csv` pre-processed file (9 020 rows) is generated from it. If the automatic download fails:

1. Download `tawos_clean.csv` manually from the TAWOS project page.
2. Place it in `data/tawos_clean.csv`.
3. Re-run `puma datasets verify`.

---

## Run-spec validation errors

### `1 validation error for RunSpec — scenario`

```
scenario: Input should be 'triage_jira', 'estimation_tawos' or 'prioritization_jira'
```

The `scenario` field must be exactly one of the three registered IDs. Check for typos.

### `self-consistency requires temperature > 0`

```yaml
# Wrong:
adaptation:
  strategy: [self-consistency]
inference:
  temperature: 0.0

# Correct:
inference:
  temperature: 0.7
```

### `models: List should have at least 1 item`

The `models:` key must be a non-empty list:

```yaml
models:
  - qwen2.5:3b    # at least one entry
```

### `sample_size: Input should be less than or equal to 10000`

Reduce `sample_size`. The Jira dataset has 200 rows; `sample_size > 200` for triage will cause sampling with replacement.

---

## Benchmark run issues

### High parse failure rate (> 20%)

The model is not following the output format.

- Switch to a simpler strategy: `zero-shot` before `few-shot-*`.
- Increase response length: `inference.max_tokens: 512`.
- Check prompt templates in `specs/prompts/<scenario>/` for formatting issues.
- Try a different model: smaller models often follow instructions less reliably.

### All predictions have `parse_failure_rate: 1.0` after a dry run

This is **expected behaviour**. In dry-run mode the runner returns `"[dry-run]"` as the response, which no parser can match. The dry run is only for testing the pipeline, not the model.

### `UNIQUE constraint failed: instances.dataset, instances.source_id`

This should not occur in production (fixed in v2.0.0). If you see it, clear the database:

```bash
puma db migrate         # re-apply schema to a fresh db
# or delete the file:
rm data/puma.db && puma db migrate
```

### Very slow inference (> 5 min per instance)

- Verify the hardware profile: `puma preflight` — ensure the correct profile is active.
- Check that the model fits in VRAM: `puma models list`.
- On CPU-only machines, prefer models ≤ 3B parameters.
- Verify OLLAMA_HOST is reachable: `curl http://localhost:11434/api/version`.

---

## Dashboard issues

### Dashboard shows "No run data found"

No runs are in the database yet. Run a benchmark first:

```bash
puma run specs/runs/smoke_triage.yaml --dry-run
```

Then refresh the dashboard.

### Dashboard fails to start

Check Streamlit is installed in the container:

```bash
docker compose run --rm puma_runner python -c "import streamlit; print(streamlit.__version__)"
```

If missing, rebuild the image: `docker compose build puma_runner`.

### Charts do not appear

Some views require data that is only available after a live run (e.g., logprobs for the Reliability view, perturbations for Robustness). The dashboard shows informational messages when data is absent.

---

## Inference cache issues

### Cache hit but result looks wrong

If a model was updated (new version pulled), old cached responses may no longer be valid:

```bash
puma cache clear
```

Then re-run the benchmark.

### `sqlite3.DatabaseError` on cache access

The cache database is corrupted:

```bash
rm data/cache/inferences.db
puma cache stats     # recreates the DB automatically
```

---

## Test failures

### `ModuleNotFoundError: puma`

Tests require `PYTHONPATH=src`. This is set automatically when running via Docker (`make test`). If running locally:

```bash
PYTHONPATH=src pytest tests/unit/
```

### `NotADirectoryError` in preflight tests

Fixed in v2.0.0 — `detect.py` now catches `NotADirectoryError` in all subprocess helpers. Ensure you are on the latest version.

### Integration tests fail with `FileNotFoundError`

Integration tests require real datasets in `data/`. Download them first:

```bash
docker compose run --rm puma_runner python scripts/download_datasets.py
```

---

## Getting further help

1. Run `puma --help` or `puma <command> --help` for command-specific options.
2. Check `logs/startup_*.log` for provisioning errors.
3. Review structured logs in `structlog` JSON format — parse with `jq`:
   ```bash
   docker compose logs puma_runner | grep '"event"' | jq .
   ```
4. Open an issue at the repository with the full error message and the output of `puma preflight`.
