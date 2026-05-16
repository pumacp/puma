# PUMA on macOS — Operational Notes

This document clarifies the operational characteristics of PUMA on macOS,
specifically on Apple Silicon (M1, M2, M3, M4, M5 families). It supersedes
the brief statements about Apple Silicon scattered across earlier docs
(notably the line in `docs/troubleshooting.md` corrected in v2.5.0, the
"Optional — NVIDIA/AMD/Apple Silicon" GPU row in `README.md`, and the
"AMD ROCm and Apple Metal" backlog items in earlier release notes).

The short version: in v2.5.0, PUMA on macOS runs in Docker Desktop and
therefore in **CPU-only mode** inside a Linux VM that does not expose
Metal to the container. Native Ollama on macOS uses Metal, but that
mode is not yet integrated into `start_puma.sh` (planned for v2.6.0).

## Two operational modes

### Mode A: Docker Desktop (current default in v2.5.0)

When PUMA runs inside Docker Desktop on macOS:

- Docker Desktop runs a Linux VM via Apple's Virtualization framework.
- The VM does NOT have access to the Metal GPU API. Apple's
  Virtualization framework intentionally does not expose Metal to
  guest Linux kernels.
- The VM does NOT have CUDA (Apple Silicon has no NVIDIA hardware).
- Ollama inside the `puma_ollama` container therefore operates in
  CPU-only mode regardless of the host's M-series chip.
- Inference performance is significantly lower than Linux+NVIDIA or
  native macOS+Metal.
- Recommended profile: `cpu-standard` or `cpu-lite` depending on
  available RAM allocated to Docker.
- Reproducibility (bit-exact under `T=0.0` + `seed=42`) is preserved
  on the same architecture; cross-architecture reproducibility against
  the Linux+NVIDIA baseline is *empirically unverified* — see
  `docs/CROSS_ARCH_REPRODUCIBILITY.md` (planned for v2.6.0).

This is the mode documented in `start_puma.sh` and is the supported
path in v2.5.0.

### Mode B: Native Ollama (advanced users, not yet officially supported in v2.5.0)

When Ollama runs natively on macOS (outside Docker):

- Ollama uses Metal Performance Shaders for inference acceleration.
- Apple Silicon's unified memory architecture provides high memory
  bandwidth between CPU cores, GPU cores, and Neural Engine.
- M3/M4/M5 chips include a Neural Engine, but Ollama does not currently
  leverage it (Metal only).
- Inference performance is comparable to mid-range NVIDIA GPUs
  depending on the chip variant.

This mode is technically possible today (`brew install ollama && ollama
serve`) but not yet integrated into PUMA's `start_puma.sh` in v2.5.0.
First-class native-mode support — including the `--native` flag in
`start_puma.sh`, `apple-silicon-*` profile detection in `puma profile`,
and `apple-silicon-*` entries in `config/models_catalog.yaml` — is
planned for v2.6.0.

A manual workaround to run Mode B today:

```bash
# Terminal 1: native Ollama
brew install ollama
ollama serve

# Terminal 2: PUMA Python venv (no Docker)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export PUMA_OLLAMA_HOST=http://localhost:11434
puma run specs/runs/baseline_triage.yaml
```

Caveats for the manual workaround in v2.5.0:

- `puma profile` will report a generic `cpu-*` profile because Apple
  Silicon detection is not yet implemented.
- CodeCarbon tracking on macOS uses `powermetrics`, which requires
  `sudo`; without elevation, energy figures will be incomplete. Use
  `--no-emissions` in `puma run` if you cannot grant sudo.
- Cross-architecture reproducibility (x86_64 vs arm64) is empirically
  unverified.

## Performance expectations

Estimated baseline (`qwen2.5:3b` × N=200 × `triage_jira`):

| Configuration | Mode | Latency p95 | Notes |
|---|---|---|---|
| Linux + RTX 2060 6 GB | Docker | ~45–60 s | gpu-entry reference (empirically measured) |
| macOS M4 Pro (24 GB) | Docker | ~8–12 min | CPU-only inside VM — *estimated, unvalidated* |
| macOS M4 Max (36 GB) | Docker | ~6–10 min | CPU-only inside VM — *estimated, unvalidated* |
| macOS M4 Pro | Native | ~90–150 s | Metal accelerated — *estimated, unvalidated* |
| macOS M5 Max | Native | ~50–90 s | Metal accelerated — *estimated, unvalidated* |
| macOS M5 Ultra | Native | ~30–60 s | Metal accelerated — *estimated, unvalidated* |

Native-mode estimates are extrapolated from Ollama community benchmarks
and have NOT been empirically validated by PUMA on M-series hardware.
A future Sprint will add first-class Apple Silicon support including a
native runtime mode and dedicated profiles (`apple-silicon-m3`, `m4`,
`m4-pro`, `m4-max`, `m5`, `m5-pro`, `m5-max`, `m5-ultra`).

## Reproducibility caveat

The reference baseline (`F1-macro = 0.5867 ± 0.01` for `qwen2.5:3b` +
`contextual-anchoring` + `seed=42` + `T=0.0` on `triage_jira` × 200
instances) was characterized on Linux + RTX 2060 Mobile 6 GB
(`gpu-entry`). It is bit-exact reproducible in warm state on that
hardware.

Reproducing this exact F1 value on macOS — in either Mode A or Mode B —
is empirically unverified in v2.5.0. Floating-point execution order
may differ between x86_64 (AVX2) and arm64 (NEON) SIMD paths, and
between CUDA and Metal kernels. Q4_K_M integer-quantised inference is
*expected* to be deterministic across architectures, but this claim
has not yet been tested.

If you reproduce PUMA on macOS, please record your results and open an
issue — empirical data from M-series hardware would directly close the
cross-architecture reproducibility gap.

## Energy tracking on macOS (Mode B / native)

CodeCarbon supports macOS energy tracking via the `powermetrics`
utility, which requires `sudo`. PUMA v2.6.0 adopts a graceful
fallback driven by
`puma.sustainability.codecarbon_wrapper.get_tracking_mode_and_warnings`:

1. **Passwordless powermetrics configured** — PUMA uses
   `tracking_mode="machine"` (most accurate; identical to the Linux
   path).
2. **Default macOS state (sudo required)** — PUMA falls back to
   `tracking_mode="process"` and emits a single warning. Energy
   values are still recorded but are less precise. The warning text
   points back to this section.
3. **No tracking wanted** — run `puma run --no-emissions` to disable
   CodeCarbon entirely.

The Linux path is unchanged from v2.5.0: `tracking_mode="machine"`
with no warnings.

### Configuring passwordless powermetrics (advanced)

Edit `/etc/sudoers` (always via `sudo visudo`, never directly) and
add a single line:

```
%admin ALL=(root) NOPASSWD: /usr/bin/powermetrics
```

**Caution**: this grants every admin user passwordless root access
to `powermetrics`. Evaluate the security implication for your
environment before applying. For shared machines, prefer the
process-mode fallback or disable emissions entirely.

### Why CodeCarbon needs `tracking_mode="machine"` in particular

PUMA's split-container architecture on Linux runs orchestration in
`puma_runner` and inference in `puma_ollama`. With
`tracking_mode="process"`, CodeCarbon measures only the
orchestrator's own energy and misses the GPU work performed in the
other container — exactly the D15 bug that was fixed in v2.1.0.
`tracking_mode="machine"` captures whole-host energy and attributes
it correctly under PUMA's documented sweep convention (AC power,
idle host, no other GPU consumers).

On macOS Mode B with a native Ollama process, the same reasoning
applies in reverse: process-mode would measure only puma's own
energy and miss Ollama's. The machine path requires `powermetrics`
under the hood, hence the sudo dependency.

## Recommendation

- For reproducibility-critical research, use Linux with an NVIDIA GPU
  (the validation environment for all empirical results in v2.0.0–v2.5.0).
- For exploratory work on macOS, use Mode A (Docker) accepting CPU-only
  performance. Profile classification will be `cpu-standard` or
  `cpu-lite`.
- Native mode (B) is experimental in v2.5.0 and requires user-provided
  setup. First-class support arrives in v2.6.0.
