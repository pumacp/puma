---
id: spec-preflight-v1
title: Preflight — Hardware Detection and Profile Selection
phase: F1
status: approved
---

# Preflight Spec

## Purpose
Detect host hardware capabilities and select the appropriate execution profile before
any service is started. Write the result to `config/runtime_profile.yaml`.

## Modules

### puma.preflight.detect
Returns a `SystemCapabilities` dataclass:
- `os_system`, `os_arch`, `python_version`
- `cpu_model`, `cpu_cores_physical`, `cpu_threads`, `cpu_freq_mhz`
- `ram_total_gb`, `ram_available_gb`
- `disk_free_gb` (at cwd)
- `gpu_name`, `gpu_vram_gb`, `gpu_backend` (`nvidia`|`rocm`|`metal`|`none`)
- `ollama_version`, `ollama_reachable`

GPU detection order: nvidia-smi → rocm-smi → system_profiler (macOS Metal).

### puma.preflight.profile
- Reads `config/profiles.yaml` (5 profiles: cpu-lite, cpu-standard, gpu-entry, gpu-mid, gpu-high).
- `select_profile(caps) -> Profile` applies rules from INDEX.md §2.1.
- Raises `InsufficientHardwareError` if RAM < 8 GB.
- Manual override via `--profile <name>` validated against catalog.

### puma.preflight.provisioning
- Verifies disk space: sum of GGUF sizes for profile models + 5 GB margin.
- Verifies Docker and docker-compose are installed.
- Verifies GPU accessible from Docker (if GPU profile).
- Returns `list[ProvisioningIssue]` with `severity` (error|warning) and `message`.

## CLI
`puma preflight [--profile auto|cpu-lite|cpu-standard|gpu-entry|gpu-mid|gpu-high]`
- Prints human-readable diagnostic report to stdout.
- Writes `config/runtime_profile.yaml`.
- Exit code 0 if no errors, 1 if any error-severity issue.

## Config outputs
`config/runtime_profile.yaml`:
```yaml
profile: cpu-standard
detected_at: "2026-04-18T10:00:00"
hardware:
  os: Linux
  cpu: Intel Core i7
  cpu_cores: 8
  ram_gb: 16.0
  gpu: null
  gpu_vram_gb: null
models:
  - qwen2.5:3b
  - gemma3:4b
  - gemma4:e2b
```

## Gate checklist
- [ ] `puma preflight` prints diagnostic and writes `config/runtime_profile.yaml`
- [ ] Unit tests with mocked subprocess pass
- [ ] Integration test verifies runtime_profile.yaml written correctly
