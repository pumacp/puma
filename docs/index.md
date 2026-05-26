# PUMA — Local LLM benchmarks for project management

PUMA is a local-first benchmarking platform for evaluating small language models
on project-management tasks: issue **triage** (classification) and story-point
**estimation** (regression). Every run is reproducible — fixed seed and
temperature, content-hashed predictions — and energy use is tracked per run via
CodeCarbon. Models run locally through Ollama; nothing leaves your machine.
PUMA is released under the Apache 2.0 license.

## Quick start

```bash
pip install -e .                         # from a source checkout
puma doctor                              # verify environment (Ollama, models, hardware)
puma run specs/runs/baseline_triage.yaml # run a baseline benchmark
```

## Navigation

- **[CLI Reference](cli_reference.md)** — the complete `puma` command surface.
- **[Sustainability](sustainability.md)** — emissions-tracking methodology and energy results.
- **[Known Debt](known_debt.md)** — tracked findings (the D-series) and P1 captures.
- **Releases** — release notes, starting with the current `v3.1.0`.

## How this site is built

This documentation is built with [MkDocs](https://www.mkdocs.org/) and the
Material theme, and published automatically to GitHub Pages on every push to
`develop`. A [GitHub Actions workflow](https://github.com/pumacp/puma/blob/develop/.github/workflows/docs.yml)
builds the site with `mkdocs build --strict` — which fails on broken links or
nav issues — and deploys the result to the `gh-pages` branch. To preview the
site locally, run `bash scripts/serve_docs.sh` and open <http://127.0.0.1:8000>.
