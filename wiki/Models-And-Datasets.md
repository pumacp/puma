# Models and Datasets

PUMA ships with a curated catalog of open-weight models and two anchor
datasets. Both are selected for licensing clarity, scientific reproducibility,
and a range of hardware demands.

## Models

| Model | Size | Best for | Indicative F1 (triage) |
|-------|------|----------|------------------------|
| `qwen2.5:1.5b` | 1.5 B | cpu-lite smoke tests | 0.42 |
| `qwen2.5:3b` | 3 B | cpu-standard general | 0.55 |
| `qwen2.5:7b` | 7 B | gpu-entry quality | 0.62 |
| `llama3.1:8b` | 8 B | gpu-entry quality | 0.61 |
| `mistral:7b` | 7 B | gpu-entry quality | 0.59 |
| `gemma3:2b` | 2 B | cpu-standard balanced | 0.51 |
| `gemma3:9b` | 9 B | gpu-mid quality | 0.64 |
| `deepseek-r1:7b` | 7 B | gpu-entry reasoning | 0.63 |

Indicative numbers are from PUMA's reference runs on the Jira SR balanced 200
set with `--strategy contextual_anchoring`. Your numbers will vary; that's
the entire point of running your own benchmarks.

## Hardware profiles

PUMA selects one of five profiles via `puma preflight`:

| Profile | GPU | RAM | Suitable models |
|---------|-----|-----|-----------------|
| `cpu-lite` | none | ≤ 16 GB | 1.5–3 B parameter models |
| `cpu-standard` | none | > 16 GB | up to 7 B (slower) |
| `gpu-entry` | 4–8 GB VRAM | any | up to 8 B fp16 / 13 B int4 |
| `gpu-mid` | 12–24 GB VRAM | any | up to 13 B fp16 / 30 B int4 |
| `gpu-pro` | ≥ 24 GB VRAM | any | 30 B+ fp16, multi-model concurrent |

The profile sets reasonable defaults for batch size, request timeout, and the
suggested model list. You can always override via `--profile`.

## Datasets

- **Jira Social Repository (Jira SR)** — a balanced 200-issue subset drawn
  from public Apache Software Foundation projects, used by both
  `triage_jira` (classification) and `prioritization_jira` (pairwise
  ranking). Source: [Jira SR dataset on Zenodo](https://zenodo.org/record/5901804).
- **TAWOS** — Tickets from Apache, WebObjects, and Other Suite open-source
  projects, used by `effort_tawos` for story-point regression. Source:
  [TAWOS on GitHub](https://github.com/SOLAR-group/TAWOS).

Both datasets are downloaded on first use and cached under `data/cache/`.
Re-running with the same `--seed` reproduces the identical instance sample.
