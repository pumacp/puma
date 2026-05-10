# Hardware Specification

This document records the hardware specification of the machine used
to develop, validate, and produce baseline measurements for PUMA.
Reproducing measurements on different hardware is expected to yield
different absolute values; this document exists so that those
differences are interpretable.

## Reference machine

| Component | Specification |
|-----------|--------------|
| Form factor | Laptop (MSI GS66 Stealth 10SE, model 16V1.1) |
| CPU | Intel Core i7-10750H @ 2.60 GHz (6 cores / 12 threads, base 2.6 GHz, turbo up to 5.0 GHz) |
| CPU cache | L1d 192 KiB, L1i 192 KiB, L2 1.5 MiB, L3 12 MiB |
| Memory | 32 GB DDR4 SODIMM @ 2667 MHz (2× 16 GB Samsung M471A2K43CB1-CTD, dual channel) |
| GPU (discrete) | NVIDIA GeForce RTX 2060 Mobile (TU106M), 6 GB GDDR6, CUDA capability 7.5 (Turing) |
| GPU (integrated) | Intel UHD Graphics (CometLake-H GT2) |
| Storage | NVMe WD PC SN730 SDBPNTY-1T00-1032, 1 TB total |
| Linux root partition | EXT4, 766 GB |
| Network | Intel WiFi 6 AX201 + Ethernet i225 (1 Gbps) |
| OS | Linux 6.8.0-111-generic |
| Battery | 32.7 Wh (32768 mWh) — measurements should be done on AC power only |

## Profile detection

`puma.preflight.select_profile()` automatically classifies this machine
as profile **`gpu-entry`** based on:

- VRAM ≥ 6 GB (threshold for `gpu-entry`)
- VRAM < 12 GB (threshold for `gpu-mid`)
- RAM ≥ 16 GB (host requirement satisfied)
- NVIDIA backend detected via `nvidia-smi`

Models compatible with `gpu-entry` are derived dynamically from
`config/models_catalog.yaml` via `models_for_profile('gpu-entry')`
(see `src/puma/preflight/catalog.py`).

## Implications for measurements

The following hardware characteristics directly affect how PUMA
measurements should be interpreted on this reference machine.

### Sustained-load thermal behavior

This is a laptop, not a desktop or server. Sustained inference loads
(such as the Phase B sweep across multiple models and scenarios) may
trigger thermal throttling on either CPU or GPU. This affects:

- `duration_s` per run can vary across runs of the same configuration
  due to thermal state at start of run
- `co2_kg` and `kwh` reported by CodeCarbon will reflect the actual
  energy consumed (including throttling-induced variations) but the
  *efficiency* metric (e.g., gCO₂ per F1 point) may be biased upward
  for runs that ran while the chassis was already warm

Empirical observation from Phase B sweep: `mistral:7b` showed
duration variability of 10–18× across the 3 scenarios on this hardware
(129 s vs 1377 s vs 2299 s), suggesting either thermal throttling,
memory pressure transients, or a mix. Cross-model comparisons should
be interpreted with this variance in mind.

Recommended mitigations when running sweeps:

- Run sweeps on AC power, not battery
- Allow brief cooldown intervals between large model runs
- Document ambient temperature if reproducing measurements
- Take measurements as relative comparisons (model A vs model B on
  the same machine in the same session) rather than absolute claims

### Memory bandwidth

DDR4-2667 is moderate-bandwidth memory by 2025 standards. For models
that do not fit entirely in VRAM and require partial CPU/RAM offload
(specifically `gemma3:12b` at 8.1 GB GGUF on a 6 GB VRAM card, and
the unexpectedly large `gemma4:e2b` at 7.2 GB GGUF), the memory
bandwidth becomes a bottleneck. Expect significantly higher
`duration_s` for these runs than VRAM-resident equivalents.

### VRAM constraints

The 6 GB VRAM ceiling determines which models in the catalog are
practical on this machine:

- Models up to ~5 GB GGUF (Q4 quantization, params ≤ 7B) fit fully
  in VRAM with comfortable margin: `qwen2.5:1.5b/3b/7b`, `gemma3:1b/4b`,
  `mistral:7b`, `deepseek-r1:7b`
- Models at ~5 GB GGUF (Q4 quantization, ~8B params) fit but with
  little margin: `llama3.1:8b`
- Models exceeding 6 GB GGUF require partial CPU offload, which may
  succeed (slowly) or produce unusable outputs depending on parser
  compatibility: `gemma3:12b`, `gemma4:e2b`
- Models exceeding ~10 GB GGUF cannot run effectively on this machine
  and are excluded from `gpu-entry` runs: `qwen2.5:14b`, `gemma3:27b`,
  `deepseek-r1:14b`, plus the Gemma4 MoE variants `e4b` and `26b-a4b`

### CodeCarbon accuracy on this hardware

CodeCarbon currently reports `gpu_energy = 0` when invoked from inside
the `puma_runner` container, because the container does not have
direct access to `nvidia-smi`. As a result, GPU energy contribution
on this reference machine is not captured in the `emissions` table
unless the container is reconfigured with `nvidia-runtime` and
appropriate device passthrough. This is tracked as open debt
(see `docs/known_debt.md`, item D15).

Until that is resolved, `kwh` and `co2_kg` figures from CodeCarbon
on this machine reflect CPU and RAM energy only. For CPU-bound runs
(small models that don't engage the GPU significantly) this is close
to total system energy. For GPU-bound runs it is an underestimate.

## Reproducibility scope

The reference baseline of v2.0.0 (`F1-macro = 0.5867 ± 0.01` for
`qwen2.5:3b` + `contextual-anchoring` + `seed=42` + `temperature=0.0`
on `triage_jira` with 200 instances) was characterized on this
specific machine. The numerical value is bit-exact reproducible in
warm state and exhibits ≤0.006 cold-vs-warm drift, both within the
documented ±0.01 tolerance.

Reproducing this exact baseline value on different hardware is not
guaranteed. The reproducibility claim of PUMA is the *procedure*
(seed, temperature, dataset, prompts), not the absolute number.
Different hardware may yield slightly different F1 due to differences
in floating-point execution order across CPU/GPU implementations and
across CUDA versions.

## Updating this document

When PUMA is run on additional reference machines, append sections
documenting those machines and their detected profiles, rather than
replacing this content. Hardware diversity in the measurement set
strengthens the reproducibility evidence.
