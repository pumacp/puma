# Models catalog — version history

This document tracks changes to `config/models_catalog.yaml` across
PUMA releases. Each entry corresponds to a `catalog_version` value
published in a tagged release.

The catalog uses a list-of-dicts shape (`models: [...]`) keyed on
`ollama_tag`. The loader (`src/puma/preflight/catalog.py`) reads
`raw.get("models", [])` so the addition of root-level fields such as
`catalog_version` is backward-compatible.

## catalog_version 2.6.0 — 2026-05-16 (PUMA v2.6.0)

### Added

- 9 Apple Silicon profile identifiers in `config/profiles.yaml`:
  `apple-silicon-m3`, `-m3-pro`, `-m3-max`, `-m4`, `-m4-pro`,
  `-m4-max`, `-m5`, `-m5-pro`, `-m5-max`, `-m5-ultra`. All declare
  `empirical_validation: pending` — PUMA has no Mac hardware in the
  validation set as of v2.6.0; the dispatch infrastructure ships
  here so empirical validation can be performed when hardware
  becomes available. See
  [`CROSS_ARCH_REPRODUCIBILITY.md`](CROSS_ARCH_REPRODUCIBILITY.md)
  for the testing protocol.
- Schema extension to `profiles.yaml` requirements (non-breaking):
  `apple_silicon_required: bool`, `chip_brand_match: str`,
  `min_unified_memory_gb: int`. The existing 5 NVIDIA/CPU profiles
  leave them at their defaults and are unaffected.
- Model `profiles_compatible[]` extended conservatively per a
  memory-headroom rule (≈ 2× GGUF + OS overhead). Summary:
  - `qwen2.5:1.5b`, `gemma3:1b` → compatible with all 10 apple-silicon-*
  - `qwen2.5:3b`, `gemma3:4b` → skip m3 base (8 GB tight)
  - 7B–8B models (`qwen2.5:7b`, `mistral:7b`, `llama3.1:8b`,
    `deepseek-r1:7b`) → require Pro/Max/Ultra (≥ 18 GB)
  - 14B models (`qwen2.5:14b`, `deepseek-r1:14b`) → require Max/Ultra
    (≥ 36 GB)
  - `gemma3:12b` → requires ≥ 24 GB (Pro/Max/Ultra of m3-max,
    m4-pro+, m5-pro+)
  - `gemma3:27b` → requires Max/Ultra (≥ 36 GB)
- New unit tests in `tests/unit/test_catalog_metadata.py`:
  `test_valid_profiles_includes_all_apple_silicon_identifiers`,
  `test_apple_silicon_profiles_defined_in_profiles_yaml`,
  `test_apple_silicon_chip_brand_match_is_unique`,
  `test_gemma4_family_not_compatible_with_any_apple_silicon`,
  `test_qwen25_3b_compatible_with_apple_silicon_m4_pro`.

### Preserved (P2 / P6)

The `gemma4` family stays **excluded** from every `apple-silicon-*`
profile. Same VRAM-pressure failure mode that motivated the
`gpu-entry` exclusion (D18, F8) applies to unified memory on smaller
chip variants. Re-enabling any `(gemma4, apple-silicon-*)` pair
requires new empirical evidence on Mac hardware and an explicit
debt entry referencing the prior exclusion. The regression-guard
test `test_gemma4_family_not_compatible_with_any_apple_silicon`
enforces this from v2.6.0 onward.

### Notes

- Compatibility is **inferred from unified-memory specifications,
  not empirically validated on Apple Silicon hardware** in v2.6.0.
- Q4_K_M quantisation is expected to make `f1`/`mae` bit-exact
  across architectures; logprobs (and therefore ECE) may differ.
  See [`CROSS_ARCH_REPRODUCIBILITY.md`](CROSS_ARCH_REPRODUCIBILITY.md).
- `select_profile()` in `src/puma/preflight/profile.py` runs the
  apple-silicon branch BEFORE the existing GPU/CPU dispatch. On
  Linux+NVIDIA the new branch is a no-op (caps.chip_brand is None).

## catalog_version 2.5.0 — 2026-05-13 (PUMA v2.5.0)

### Added

- `catalog_version` field at the YAML root, starting at `"2.5.0"`.
- `catalog_changelog_path` field pointing to this document.
- Unit test `tests/unit/test_catalog_metadata.py::test_catalog_has_version_field`
  asserting both fields exist and match the expected values.

### Documented (no entry change, status clarification only)

The **gemma4** family (`gemma4:e2b`, `gemma4:e4b`, `gemma4:26b-a4b`)
was catalogued in earlier releases with the `gpu-entry` profile
*excluded* from `profiles_compatible[]`. This exclusion is empirically
grounded; v2.5.0 preserves it unchanged. The supporting evidence:

- **F8** (closed): `gemma4:e2b` GGUF size was measured at 7.2 GB on
  disk, not the ~2 GB suggested by the model's effective active
  parameter count. Root cause: MoE architecture stores every expert
  in the GGUF artifact regardless of which are routed at inference
  time, so "effective active params" do not predict the on-disk size.
  Catalog field `gguf_size_gb` was corrected from `2.0` to `7.2`.
- **D18** (closed): all 5 smoke runs with `gemma4:e2b` on `gpu-entry`
  hardware (RTX 2060 Mobile 6 GB VRAM) returned empty `raw_response`
  strings across `triage_jira`, `estimation_tawos`, and
  `prioritization_jira`. The inferred root cause is VRAM pressure
  (7.2 GB GGUF vs 6 GB VRAM) causing partial CPU offload that the
  current parsers cannot recover from. Resolution: remove `gpu-entry`
  from `profiles_compatible[]` for the three `gemma4` tags.
- **Regression guard**: `tests/unit/test_catalog_metadata.py::test_gemma4_family_excluded_from_gpu_entry`
  asserts `"gpu-entry" not in entry.profiles_compatible` for all
  three `gemma4` tags. This test is never weakened — re-enabling
  `gpu-entry` for any `gemma4` entry requires new empirical evidence
  on the validation hardware and reopening D18 with that evidence.

Users on `gpu-mid` (12–24 GB VRAM) or `gpu-pro` (24+ GB VRAM) hardware
can use the `gemma4` family normally. Users on `gpu-entry` should
select `qwen2.5:*` or `gemma3:*` models instead.

### Reference: Gemma 4 release timeline

The Gemma 4 family was released by Google on 2 April 2026 under the
Apache 2.0 license. PUMA's catalog reflects *empirical compatibility
on the validation hardware* (RTX 2060 Mobile 6 GB), which is more
restrictive than nominal specifications would suggest for MoE
variants. The catalog is not a marketing document — it is the
single source of truth for hardware-compatible model dispatch, and
its `profiles_compatible[]` field is binding.

## catalog_version 2.4.0 and earlier (no version field)

No `catalog_version` field was present in `v2.0.0` through `v2.4.0`.
The catalog content evolved organically across Sprints 1–7. The
de-facto baseline at `v2.4.0` includes:

- `qwen2.5:1.5b`, `qwen2.5:3b` (canonical), `qwen2.5:7b`, `qwen2.5:14b`
- `gemma3:1b`, `gemma3:4b`, `gemma3:12b`, `gemma3:27b`
- `gemma4:e2b`, `gemma4:e4b`, `gemma4:26b-a4b` (all gpu-entry-excluded
  per D18/F8)
- `mistral:7b`, `llama3.1:8b`
- `deepseek-r1:7b`, `deepseek-r1:14b`
- `phi3:mini` (where present in the prevailing config)

For the exact catalog state at any earlier tag, use git:

```bash
git show v2.4.0:config/models_catalog.yaml
git show v2.3.0:config/models_catalog.yaml
```

## Conventions for future entries

When adding or modifying a catalog entry, the following invariants
hold:

1. **Bump `catalog_version`** in `config/models_catalog.yaml` and add
   a section in this document describing what changed.
2. **Empirically validate or mark `pending`.** Any new entry without
   empirical validation on PUMA's validation hardware must include
   `empirical_validation: pending` and must NOT include `gpu-entry`
   in `profiles_compatible[]`. This invariant generalises the
   F8/D18 lesson — nominal specifications do not predict runtime
   compatibility on constrained hardware.
3. **Never re-enable a previously-excluded `(model, profile)` pair**
   without new empirical evidence and an explicit debt-tracker entry
   referencing the prior exclusion.
4. **Test the change.** Catalog tests live in
   `tests/unit/test_catalog_metadata.py`; add an assertion when an
   entry encodes a non-obvious invariant.
