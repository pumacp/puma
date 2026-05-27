<p align="center">
  <img src="assets/img/PUMA.png" alt="PUMA logo" width="240">
</p>

<p align="center"><strong>Local, reproducible, sustainable benchmarking for LLMs in ICT Project Management.</strong></p>

<p align="center">
  <a href="https://github.com/pumacp/puma/actions/workflows/lint-and-test.yml"><img src="https://github.com/pumacp/puma/actions/workflows/lint-and-test.yml/badge.svg" alt="Lint and test"></a>
  <a href="https://github.com/pumacp/puma/actions/workflows/docs.yml"><img src="https://github.com/pumacp/puma/actions/workflows/docs.yml/badge.svg?branch=develop" alt="Docs CI"></a>
  <img src="https://img.shields.io/badge/python-3.11+-111111" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-111111" alt="License: MIT">
  <img src="https://img.shields.io/badge/runs%20on-Docker-111111" alt="Runs on Docker">
  <br>
  <img src="https://img.shields.io/badge/reproducible-seed%3D42-111111" alt="Reproducible">
  <img src="https://img.shields.io/badge/sustainability-CodeCarbon-111111" alt="CodeCarbon">
  <img src="https://img.shields.io/badge/inference-Ollama-111111" alt="Ollama">
  <br>
  <a href="https://huggingface.co/spaces/pumaproject/puma-leaderboard"><img src="https://img.shields.io/badge/%F0%9F%A4%97-Leaderboard-111111" alt="Leaderboard"></a>
  <a href="https://zenodo.org/communities/pumacp"><img src="https://img.shields.io/badge/Zenodo-DOI-111111" alt="Zenodo"></a>
  <a href="https://github.com/pumacp/puma-community"><img src="https://img.shields.io/badge/PUMA-Community-111111" alt="PUMA Community"></a>
</p>

<!-- PUMA-ACROSTIC-BLOCK START — DO NOT MODIFY — IMMUTABLE -->
---
**F**ollowing empirical evidence, ICT project management faces triage, estimation, and learning inefficiencies.<br>
**O**bserved widely, these persist despite abundant historical data.<br>
**L**aying a rigorous foundation requires reproducible benchmarking.<br>
**L**everaging labeled datasets enables systematic evaluation of LLM performance.<br>
**O**utcomes are compared using quantitative metrics and statistical analysis.<br>
**W**ith an incremental design, a minimal viable benchmark is defined.<br>
**T**hrough open-source release, results become reproducible and verifiable.<br>
**H**ence, the framework supports extensibility across models and tasks.<br>
**E**ventually, it enables integration into real organizational settings.<br>
**W**ithin ICT environments, recurring inefficiencies hinder effective decision-making.<br>
**H**eterogeneous data sources complicate prioritization and estimation processes.<br>
**I**n response, this work builds a reproducible LLM-based benchmark.<br>
**T**he focus is on issue triage and story-point estimation tasks.<br>
**E**valuation follows controlled experiments with statistical validation.<br>
**P**rotocols ensure reproducibility through fixed parameters and configurations.<br>
**U**sing carbon tracking, the framework measures energy impact.<br>
**M**oreover, the MVP delivers a valid and original contribution.<br>
**A**ll artefacts are released as open source for replication and extension.<br>
---
<!-- PUMA-ACROSTIC-BLOCK END -->

<p align="center">
  <a href="#quick-start"><strong>Get started</strong></a> ·
  <a href="#citation"><strong>Cite PUMA</strong></a> ·
  <a href="#community"><strong>Join the community</strong></a>
</p>

## What is PUMA?

PUMA is a local-first, open-source benchmarking platform that evaluates
open-weight large language models (LLMs) on **ICT Project Management** tasks —
specifically **issue triage** (classifying a ticket's priority) and
**story-point estimation** (predicting effort). It runs entirely on your own
hardware through [Ollama](https://ollama.com): no API calls, no accounts, and no
data ever leaves your machine. Every run is **deterministic** (fixed seed `42`,
temperature `0.0`), so the same inputs produce byte-identical predictions, and
every run is **sustainability-aware** — energy use and carbon are measured with
[CodeCarbon](https://codecarbon.io).

PUMA was built to test a hypothesis: that AI systems can be evaluated rigorously,
and that the evaluation itself can be reproducible, auditable, and free. Around
the tool sits **PUMA Community**, a public archive where any researcher or
practitioner can publish their results with cryptographic integrity — turning a
private benchmark into a shared, verifiable body of evidence.

## The questions PUMA addresses

PUMA began as a set of open questions about research, software, and AI:

- Can rigorous academic research be conducted using AI tools?
- Can scientific studies conducted with AI tools be scientifically replicated?
- What is the state of the art in software development built with AI tools?
- Can software built with AI tools be efficiently audited?
- Can a local, free, automated project-management evaluation platform be built?
- Is there a paradigm shift underway in research, software development, and project management?
- What is the cost — financial and environmental — of adopting LLMs in business or project-management processes?
- Can LLM capabilities on a concrete scenario be measured scientifically, alongside their environmental consequences?
- Can gaps in the literature be detected using AI tools — can AI surface new problems and new solutions?
- Can a research project be documented in a live, automated, reproducible, real-time way?
- Can the resulting knowledge be shared publicly, without authorship, investment, or time restrictions?
- Can AI tools be studied *using* AI tools — can the object of study also be an instrument of its own study?

PUMA is one concrete, working answer to these questions: a reproducible artefact
whose construction and evidence are public end-to-end.

## The two phases of PUMA's development

!!! info "PUMA was built in two openly documented phases"
    **1 — Research.** A structured literature review (Keshav's three-pass method,
    PRISMA 2020 review structure), methodology design (Design Science Research),
    hypothesis formulation, and experimental design.

    **2 — Artefact construction.** Two artefacts: the **PUMA benchmark tool**
    (this repository) and **PUMA Community** (the public submission hub). Both
    phases are published with full reproducibility.

## How PUMA works

PUMA is organized as a six-layer architecture, each layer with a single
responsibility:

| Layer | Responsibility |
|---|---|
| **Orchestrator** | Drives a run-spec end to end (load → infer → evaluate → persist). |
| **Runtime** | Talks to Ollama locally, with deterministic, bounded retry. |
| **Models** | Discovers and describes the local model catalog (read-only). |
| **Evaluation** | Computes task metrics (F1-macro, MAE, calibration, latency). |
| **Diagnostics** | `puma doctor` / `puma env` — health and environment checks. |
| **Community** | Builds, validates, and publishes submissions with integrity hashes. |

Results are stored in a bi-temporal **SQLite** database; a **Streamlit** dashboard
visualizes runs; and **CodeCarbon** records energy and emissions on every run.
Crucially, execution is **local-only** — PUMA never makes an external inference
call.

## What PUMA measures

- **F1-macro** — issue triage (multi-class classification).
- **MAE** — story-point estimation (numeric prediction).
- **Per-class precision / recall / F1** — where the model succeeds or fails.
- **Calibration (ECE)** — when log-probabilities are available.
- **Latency** — p50, p95, p99 per inference.
- **Sustainability** — grams of CO₂-equivalent and kWh, via CodeCarbon.
- **Reproducibility** — byte-identical predictions across repeated runs.

## Why use PUMA?

- **100% local** — code and data never leave your machine.
- **Reproducible** — same inputs produce the same outputs, byte for byte.
- **Sustainable** — measures and reports its own environmental impact.
- **Free** — no API keys, no paywalls, no commercial licenses.
- **Open** — MIT-licensed and community-contributed.
- **Multi-model** — Qwen, Mistral, Llama, and Gemma families.
- **Multi-hardware** — CPU-only or GPU profiles, auto-detected.
- **Verifiable** — cryptographic integrity on every submission.
- **Statistically rigorous** — Wilcoxon validation and falsifiable hypotheses.

## Quick start

```bash
# 1. Install (a PyPI package is in progress; install from source today)
git clone https://github.com/pumacp/puma && cd puma
pip install -e ".[dev]"

# 2. Check your environment (Ollama, models, hardware, database)
puma doctor

# 3. See which models are available locally
puma models list

# 4. Run your first benchmark
puma run specs/runs/baseline_triage.yaml

# 5. Package the result for sharing (local dry-run, no network)
puma share-results --dry-run --run-id <run_id> --yes
```

1. **Install** the package and its development extras.
2. **`puma doctor`** confirms Ollama is reachable, a model is present, and the hardware profile is detected.
3. **`puma models list`** shows the models pulled locally.
4. **`puma run`** executes a run-spec and prints `Run complete: <run_id>`.
5. **`puma share-results --dry-run`** builds a submission package on disk without touching the network.

## Practical tutorials

=== "1 · Baseline triage"

    ```bash
    puma run specs/runs/baseline_triage.yaml
    ```
    Runs the canonical triage benchmark (200 instances). The summary prints
    F1-macro and the run id you can feed into later commands.

=== "2 · Compare two models"

    ```bash
    puma run specs/runs/baseline_triage.yaml        # model A (edit the spec's model)
    puma run specs/runs/baseline_triage.yaml        # model B
    puma compare <run_id_a> <run_id_b>
    ```
    Lays the two runs' metrics side by side so you can see which model wins on
    the same task and data.

=== "3 · Reproduce a submission"

    ```bash
    puma community pull
    puma community verify-hash <submission>.json --predictions <submission>.predictions.jsonl
    ```
    Downloads community submissions and re-derives the integrity hash locally to
    confirm a published result is exactly what it claims to be.

=== "4 · Check hardware"

    ```bash
    puma doctor
    ```
    A read-only health sweep: Python, CodeCarbon, Ollama, models, hardware
    profile, database, and baseline specs. Exits non-zero if anything is wrong.

=== "5 · List models"

    ```bash
    puma models list
    puma models recommended
    ```
    `list` shows what is pulled locally; `recommended` shows the curated catalog
    and which entries you still need to `ollama pull`.

=== "6 · Generate a submission"

    ```bash
    puma share-results --dry-run --run-id <run_id> --yes
    ```
    Produces a `submission.json` + `predictions.jsonl` package locally for review
    before any external publication.

=== "7 · Verify integrity"

    ```bash
    puma community verify-hash submission.json --predictions predictions.jsonl
    ```
    Recomputes the predictions hash and compares it to the declared value —
    exit `0` means verified, exit `1` means the file does not match.

## Use cases

- **Academic research** — rigorously evaluate model capabilities for PMO tasks and publish the findings.
- **Pre-production evaluation** — test which open-weight LLM fits your use case before committing to it.
- **Model comparison** — benchmark several models on the same task with statistical validation.
- **Sustainability auditing** — measure the environmental cost of AI-enabled workflows.
- **Reproducibility verification** — independently confirm a published result.

## PUMA Community

[PUMA Community](https://github.com/pumacp/puma-community) is the public archive of
community-contributed benchmark results.

- **What it is** — a public, governance-first repository of submissions.
- **How it works** — you open a pull request with a submission JSON; CI validates it against the schema and integrity hash, auto-merges if valid, and mirrors it to Hugging Face, Zenodo, and Kaggle.
- **Why it matters** — submissions are cryptographically verifiable, follow FAIR data principles, and receive citable DOIs.
- **How to contribute** — see the [contributing guide](https://github.com/pumacp/puma-community/blob/main/CONTRIBUTING.md).
- **Status** — browse the [public leaderboard](https://huggingface.co/spaces/pumaproject/puma-leaderboard).

## Research with PUMA Vault

[PUMA Vault](https://github.com/pumacp/puma-vault) is the public knowledge graph
behind the research process. It is built with Obsidian using PARA, GTD, and
Zettelkasten methods, linking literature notes, methodology decisions, and
findings into a navigable web. Browse it at
[pumacp.github.io/puma-vault](https://pumacp.github.io/puma-vault/).

## Methodologies

- **Design Science Research (DSR)** — for artefact construction.
- **Spec-Driven Development (SDD)** — for the codebase.
- **Keshav's three-pass method** — for reading the literature.
- **PRISMA 2020** — for the systematic-review structure.
- **Wilcoxon signed-rank test** — for non-parametric statistical validation.
- **Marco Veritas protocol** — disciplined AI-tool use in research: verify primary sources, never cite what cannot be checked.
- **APA 7th edition** — for citations.

## Cost analysis

- **Financial cost** — zero: no API keys, no paywalls, no commercial licenses.
- **Environmental cost** — on the `gpu-entry` profile, a 200-instance triage run is on the order of **0.1–0.2 gCO₂-equivalent** (CodeCarbon-measured; CPU-only profiles draw more energy and take longer).
- **Hardware** — 16 GB RAM minimum for the CPU-only profile; a GPU is optional and speeds runs up substantially.

## Community

- **Discord** — [discord.gg/fVhcpHREJv](https://discord.gg/fVhcpHREJv)
- **GitHub Discussions** — on the [puma-community](https://github.com/pumacp/puma-community/discussions) repository.
- **Contribute** — start with the [contributing guide](https://github.com/pumacp/puma-community/blob/main/CONTRIBUTING.md).
- **Report issues** — open an issue on the relevant repository.

## Resources

### Code repositories
- **PUMA benchmark tool** — <https://github.com/pumacp/puma>
- **PUMA Community** — <https://github.com/pumacp/puma-community>
- **PUMA Vault** — <https://github.com/pumacp/puma-vault>

### Documentation sites
- **PUMA docs** — <https://pumacp.github.io/puma/>
- **PUMA Community** — <https://pumacp.github.io/puma-community/>
- **PUMA Vault** — <https://pumacp.github.io/puma-vault/>
- **Wiki (tool)** — <https://github.com/pumacp/puma/wiki> · **Wiki (community)** — <https://github.com/pumacp/puma-community/wiki>

### Hugging Face Hub
- **Organization** — <https://huggingface.co/pumaproject>
- **Dataset of submissions** — <https://huggingface.co/datasets/pumaproject/puma-community-submissions>
- **Leaderboard (Gradio Space)** — <https://huggingface.co/spaces/pumaproject/puma-leaderboard>
- **Verifier (private endpoint)** — <https://huggingface.co/spaces/pumaproject/puma-verifier>
- **Personal namespace** — <https://huggingface.co/pumacp>

### Persistent archives & catalogs
- **Zenodo community (production)** — <https://zenodo.org/communities/pumacp>
- **Zenodo community (sandbox)** — <https://sandbox.zenodo.org/communities/pumacp>
- **Source dataset (Jira Social Repository)** — <https://doi.org/10.5281/zenodo.5901893>
- **Kaggle dataset** — <https://www.kaggle.com/datasets/pumacp/puma-community-submissions>

### Knowledge management & research
- **Zotero library** — <https://www.zotero.org/pumacp/library>
- **Google Drive (PDF repository)** — <https://drive.google.com/drive/folders/1TKbYhYqLIrq7liAPISF7ztS2Bv0l7vZS?usp=sharing>
- **ResearchRabbit map 1** — <https://app.researchrabbit.ai/folder-shares/d8244f17-47f7-4f6c-a589-473876578b54>
- **ResearchRabbit map 2** — <https://app.researchrabbit.ai/folder-shares/b6c00471-2f28-4c66-85f5-ab5399470228>

### Conversation
- **Discord** — <https://discord.gg/fVhcpHREJv>
- **Contact** — pumacapstoneproject@gmail.com

## Citation

If you use PUMA in your work, please cite it:

```bibtex
@software{puma_benchmark,
  title        = {PUMA: Local, reproducible benchmarking for LLMs in ICT Project Management},
  author       = {{The PUMA Project}},
  year         = {2026},
  url          = {https://github.com/pumacp/puma},
  note         = {Zenodo DOI forthcoming}
}
```

APA (7th edition):

> The PUMA Project. (2026). *PUMA: Local, reproducible benchmarking for LLMs in ICT Project Management* [Computer software]. https://github.com/pumacp/puma

!!! note
    A Zenodo DOI is forthcoming and will be appended here after the first
    DOI-backed snapshot.

---

<!-- PUMA-ACROSTIC-BLOCK START — DO NOT MODIFY — IMMUTABLE -->
---
**F**ollowing empirical evidence, ICT project management faces triage, estimation, and learning inefficiencies.<br>
**O**bserved widely, these persist despite abundant historical data.<br>
**L**aying a rigorous foundation requires reproducible benchmarking.<br>
**L**everaging labeled datasets enables systematic evaluation of LLM performance.<br>
**O**utcomes are compared using quantitative metrics and statistical analysis.<br>
**W**ith an incremental design, a minimal viable benchmark is defined.<br>
**T**hrough open-source release, results become reproducible and verifiable.<br>
**H**ence, the framework supports extensibility across models and tasks.<br>
**E**ventually, it enables integration into real organizational settings.<br>
**W**ithin ICT environments, recurring inefficiencies hinder effective decision-making.<br>
**H**eterogeneous data sources complicate prioritization and estimation processes.<br>
**I**n response, this work builds a reproducible LLM-based benchmark.<br>
**T**he focus is on issue triage and story-point estimation tasks.<br>
**E**valuation follows controlled experiments with statistical validation.<br>
**P**rotocols ensure reproducibility through fixed parameters and configurations.<br>
**U**sing carbon tracking, the framework measures energy impact.<br>
**M**oreover, the MVP delivers a valid and original contribution.<br>
**A**ll artefacts are released as open source for replication and extension.<br>
---
<!-- PUMA-ACROSTIC-BLOCK END -->

PUMA is released under the **MIT License**. Built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/).
