# PUMA — Project Index

![PUMA Logo](https://raw.githubusercontent.com/pumacp/puma/main/assets/img/PUMA.png)

> **PUMA — PUMA Understanding & Management w Agents**
>
> *Can language models manage ICT projects? An empirical benchmark of local LLM agents for issue triage and effort estimation in ICT projects.*

This document is the project index. It provides a snapshot of the
current state, the architecture, and the entry points to documentation,
results, and releases.

---

## Project status

**Current version**: v3.1.0 (released 2026-05-25)

| Phase | Description | Status |
|-------|-------------|--------|
| A | Initial cleanup and v2.0.0 release | ✓ COMPLETE |
| B | Multi-model evaluation + comparative analysis | ✓ COMPLETE |
| C | Professional dashboard (Streamlit) | ✓ COMPLETE (Sprint 4 core + Sprint 6 polish) |
| D | Technical depth (calibration, statistics, bias) | ✓ ~95% (Sprints 1, 2, 3, 5 closed; ROCm n/a) |
| E | Documentation and release consolidation | ✓ COMPLETE (v2.0.0–v3.1.0) |
| F | Hardening (post-v2.4.0 inconsistencies I5–I10) | ✓ COMPLETE (Sprint 8, v2.5.0) |
| G | Apple Silicon M3/M4/M5 support — detection + native mode | ✓ INFRASTRUCTURE COMPLETE (Sprint 9, v2.6.0); empirical validation pending Mac hardware |
| H | Catalog expansion — Qwen3 dense + MoE | ✓ INFRASTRUCTURE COMPLETE (Sprint 10, v2.7.0); empirical validation pending gpu-high hardware |

**v2.7.0-academic** is a local-only Git tag that freezes the
repository state used as the academic snapshot for the TFG
memoria. It is deliberately not pushed to `origin`. Do not
delete; restore via
`git rev-list -n 1 v2.7.0-academic`
if recovery is ever needed.

## Releases

| Tag | Date | Highlights |
|-----|------|------------|
| [v3.1.0](https://github.com/pumacp/puma/releases/tag/v3.1.0) | 2026-05-25 | Sprint 11' — post-v3.0.0 reconciliation + `puma community` CLI (browse/pull/verify-hash/validate) + wiki/Verifier minimal repairs + docs cleanup; deuda técnica D23 documented (deferred to v4.x) |
| [v3.0.0](https://github.com/pumacp/puma/releases/tag/v3.0.0) | 2026-05-20 | First public release — public documentation overhaul (Wiki + README + sync workflow) + mypy remediation from 104 errors to zero |
| [v2.7.0](https://github.com/pumacp/puma/releases/tag/v2.7.0) | 2026-05-16 | Catalog expansion (Sprint 10) — `qwen3:30b` dense + `qwen3:30b-a3b` MoE at gpu-high; Kimi K2.6 formally excluded after 13-tag Ollama registry probe; schema preserved at 8 fields; 407 tests; empirical validation pending gpu-high hardware |
| [v2.6.0](https://github.com/pumacp/puma/releases/tag/v2.6.0) | 2026-05-16 | Apple Silicon M3/M4/M5 (Sprint 9) — 9 profile identifiers, detection module, `--native` mode, macOS CodeCarbon, cross-arch docs; 402 tests; empirical validation pending Mac hardware |
| [v2.5.0](https://github.com/pumacp/puma/releases/tag/v2.5.0) | 2026-05-16 | Hardening (Sprint 8) — I5–I10 resolved; macOS modes, gpu-entry tolerance, versioned catalog, CI Ollama job, validate-baseline MAE, coverage breakdown; 354 tests |
| [v2.4.0](https://github.com/pumacp/puma/releases/tag/v2.4.0) | 2026-05-13 | CLI completeness (Sprint 7) — Anexo F § A.2 implemented; 6 new commands, 348 tests |
| [v2.3.0](https://github.com/pumacp/puma/releases/tag/v2.3.0) | 2026-05-13 | Dashboard polish (`app.py` 803→168 LOC, 10 improvements, guided tour) + documentation structure |
| [v2.2.0](https://github.com/pumacp/puma/releases/tag/v2.2.0) | 2026-05-13 | Statistical pipeline (ECE, multi-seed, Wilcoxon) + dashboard core + empirical bias evaluation |
| [v2.1.0](https://github.com/pumacp/puma/releases/tag/v2.1.0) | 2026-05-10 | Multi-model evaluation (9 models × 3 scenarios) + critical debt cleanup |
| [v2.0.0](https://github.com/pumacp/puma/releases/tag/v2.0.0) | 2026-05-09 | Initial published release with reproducible baseline |

## Architecture

> For detailed architectural reference (scenarios, strategies, metrics,
> model catalog, hardware profiles, storage schema, success criteria),
> see [docs/overview.md](docs/overview.md).

PUMA is organized in modular layers under `src/puma/`:

| Layer | Module | Purpose |
|-------|--------|---------|
| Orchestration | `orchestrator/` | Run lifecycle, spec execution |
| Runtime | `runtime/` | Ollama client, inference, timeout propagation |
| Scenarios | `scenarios/` | Task-specific parsers (triage_jira, estimation_tawos, prioritization_jira) |
| Adaptation | `adaptation/` | Prompt strategies (zero-shot, few-shot-N, contextual-anchoring, CoT) |
| Metrics | `metrics/` | F1, MAE, accuracy, ECE, fairness, statistical tests |
| Storage | `storage/` | SQLite + Alembic + ORM (runs, metrics, predictions, emissions, instances) |
| Sustainability | `sustainability/` | CodeCarbon integration (CPU + RAM + GPU energy) |
| Perturbations | `perturbations/` | Surface and semantic perturbations (typos, case, gender_swap_prefix, register_shift) |
| Preflight | `preflight/` | Hardware detection, profile selection, model catalog SoT |
| Dashboard | `dashboard/` | Streamlit interface (8 views) |
| Reporting | `reporting/` | Markdown / PDF report generation |

## Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Entry point, quickstart, model catalog |
| [docs/overview.md](docs/overview.md) | Project overview: architecture, scenarios, model catalog, hardware profiles, storage schema, success criteria |
| [docs/cli_reference.md](docs/cli_reference.md) | CLI command catalog (implemented + proposed extensions) |
| [CHANGELOG.md](CHANGELOG.md) | Version history (Keep-a-Changelog format) |
| [docs/HARDWARE.md](docs/HARDWARE.md) | Reference hardware specification + gpu-entry tolerance bands |
| [docs/MACOS_NOTES.md](docs/MACOS_NOTES.md) | macOS operational notes — Docker (CPU) vs native Ollama (Metal) |
| [docs/CATALOG_HISTORY.md](docs/CATALOG_HISTORY.md) | Models-catalog version history (catalog_version 2.5.0+) |
| [docs/CROSS_ARCH_REPRODUCIBILITY.md](docs/CROSS_ARCH_REPRODUCIBILITY.md) | x86_64 ↔ arm64 reproducibility — open question, testing protocol (v2.6.0) |
| [docs/baseline_references.md](docs/baseline_references.md) | Canonical empirical baselines for `validate-baseline` (F1 + MAE) |
| [docs/TESTING.md](docs/TESTING.md) | Test layout, markers, per-module coverage breakdown |
| [docs/known_debt.md](docs/known_debt.md) | Methodological findings + technical debt tracker |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development workflow, pre-commit setup |
| [docs/results/](docs/results/) | Empirical analyses (phase_b_analysis, multi_seed_baseline, bias_evaluation, wilcoxon_demo) |
| [docs/RELEASES/](docs/RELEASES/) | Release notes per published version |

## Empirical results

- **Reproducibility**: F1-macro = 0.5867 ± 0.01 on canonical baseline (qwen2.5:3b + contextual-anchoring + N=200, seed=42, T=0.0). Bit-exact in warm state; cold-vs-warm drift ≤ 0.006.
- **Multi-model sweep**: 9 models × 3 PMO scenarios × 100 instances = 2,700 inferences on gpu-entry hardware. Compute budget 67.5 Wh / 11.75 g CO₂.
- **Calibration**: ECE = 0.39 on qwen2.5:3b — significant out-of-the-box miscalibration, typical of LLMs without post-hoc calibration.
- **Bias evaluation**: qwen2.5:3b shows ~3× less directional gender bias than qwen2.5:1.5b under signal injection (Caliskan et al. 2017 methodology); models robust to register shift.
- **Multi-seed validation**: zero variance under T=0.0 with seeds {42, 123, 456} — confirms deterministic reproducibility.

## Quality

- Tests: 407 passing (`-m "not ollama"`; 7 ollama-marked tests run in the push-only CI job introduced in v2.5.0)
- Pre-commit: 10/10 hooks green
- CI: green on main and develop
- Coverage: 61 % (per-module breakdown in [docs/TESTING.md](docs/TESTING.md))

## Debt tracking

| Category | Count |
|----------|-------|
| Closed methodological findings (F1–F8) | 8 |
| Resolved technical debt | 15 |
| Open technical debt | 7 (0 critical, 5 medium, 2 low; 1 DECIDED-NO-ACTION) |
| Inconsistencies resolved in v2.5.0 (I5–I10) | 6 |
| Total tracked | 30 |

See [docs/known_debt.md](docs/known_debt.md) for full per-item evidence and resolution traceability.

## Related repositories

- 📚 [PUMA Research Vault](https://github.com/pumacp/puma-vault) — Unified knowledge management system for the project (PARA + GTD + Zettelkasten + Johnny Decimal integration)
- 🌐 [Vault Published](https://pumacp.github.io/puma-vault/) — Published knowledge garden
- 📦 [PUMA Releases](https://github.com/pumacp/puma/releases) — All published versions with curated release notes

## Methodology

PUMA follows Design Science Research (DSR) methodology with Wilcoxon
statistical validation. All experiments use:

- Deterministic configuration (seed=42, temperature=0.0)
- Reproducibility tested across multiple seeds and across cold-vs-warm
  runtime states
- Sustainability tracked via CodeCarbon (CPU + RAM + GPU energy)
- Statistical significance tested via Wilcoxon signed-rank (Demšar
  2006 methodology)
- Calibration assessed via ECE (Guo et al. 2017)
- Bias assessed via perturbation-based evaluation (Caliskan et al.
  2017, Bolukbasi et al. 2016, Tatman 2017)

## License

MIT License. See [LICENSE](LICENSE) for details.
