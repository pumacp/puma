# Installation

PUMA ships as a Docker Compose stack that bundles a Python runner, an Ollama
inference server, and an optional Streamlit dashboard. The recommended path is
Docker; a native install is also possible for advanced users who want to run
PUMA directly on their host Python interpreter.

## Prerequisites

- **Docker** 24+ with the `docker compose` plugin.
- **RAM**: ~16 GB minimum for small models (1.5B–3B parameters); 32 GB or more
  is comfortable when running 7B–8B models or many concurrent runs.
- **GPU (optional)**: NVIDIA with a recent CUDA driver, or Apple Silicon. PUMA
  also runs entirely on CPU; performance scales accordingly.
- **Disk**: ~10 GB free for the base stack plus ~2–8 GB per model image.

## Install (recommended path: Docker)

```bash
git clone https://github.com/pumacp/puma.git
cd puma
docker compose up -d
```

This starts the Ollama service and prepares the PUMA runner container. To
benchmark anything you need at least one model pulled into Ollama:

```bash
docker compose exec puma_ollama ollama pull qwen2.5:3b
```

Verify everything is wired up correctly:

```bash
docker compose run --rm puma_runner puma preflight
```

`preflight` inspects your host, picks a hardware profile, and reports whether
your environment is ready to run benchmarks.

## Install (native, advanced)

A native install requires Python 3.11+ and a separately running Ollama instance
on `http://localhost:11434`. After cloning the repo:

```bash
pip install -e .
```

Then run `puma` directly without `docker compose run`. See `CONTRIBUTING.md`
for the full development setup (test runner, linters, pre-commit hooks).

## Hardware detection

`puma preflight` selects one of five hardware profiles automatically based on
your detected RAM and GPU: `cpu-lite`, `cpu-standard`, `gpu-entry`, `gpu-mid`,
or `gpu-pro`. Each profile sets sensible defaults for concurrency, batch size,
and memory budget. See [Models and Datasets](Models-And-Datasets) for the full
profile matrix.
