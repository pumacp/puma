# Security

This page is PUMA's comprehensive security posture reference: the
threat model, the determinism and integrity guarantees, the no-outbound
defaults, the CI security tooling, the GitHub Actions permissions
baseline, and the known security debt that is queued for follow-up
work.

For the GitHub-canonical security policy (private disclosure path,
supported versions, disclosure timeline) see
[`SECURITY.md`](https://github.com/pumacp/puma/blob/develop/SECURITY.md)
at the repository root.

---

## 1. Overview

PUMA is a local-first benchmarking framework. Its security posture
follows from three structural choices:

1. **Inference is local.** Every model call goes through a local
   Ollama daemon on the same host. There is no SaaS inference path
   and no API token to leak.
2. **Predictions are reproducible.** Fixed `seed=42`, `temperature=0.0`,
   and a pinned model digest produce byte-identical predictions across
   runs — the `predictions_summary_hash` is the audit signature.
3. **Submissions are integrity-checked.** Every PUMA Community
   submission carries a `SHA-256` over a canonical predictions tuple,
   the schema is immutable, and verification is available client-side
   and server-side.

The attack surface that remains — dependency vulnerabilities, leaked
secrets, container image CVEs, GitHub Actions misconfiguration — is
addressed by the CI security tooling and the audit cadence described
below.

---

## 2. Threat Model

### 2.1 In scope

| Threat | Mitigation |
|---|---|
| Tampered or back-doored Python dependency | `pip-audit` on every push and weekly; `pip` install over PyPI HTTPS; pinned versions in `requirements.txt`. |
| SAST-detectable issue in PUMA source code | `bandit -r src/puma/` on every push; `MEDIUM`+ reported, `HIGH` fails the build. |
| Secrets leaked in git history | `gitleaks` full-history scan on every push; `.githooks/commit-msg` strips AI-assistant trailers and other unwanted footers on the local side; the Phase Z-2 history rewrite (May 2026) removed prior co-author trailers. |
| CVE in the published container image | `Trivy` scan on every published tag (`v*`); upload as SARIF to the GitHub Security tab; build fails on `HIGH`/`CRITICAL` OS or library CVE. |
| Tampered PUMA Community submission | `SHA-256` over the canonical predictions tuple; immutable `schema/submission.v1.json` (P3 constraint); JSON Schema validation; server-side recompute via the public verifier service. |
| GitHub Actions over-privilege | Least-privilege `permissions:` block declared per workflow / per job; no workflow uses a long-lived registry credential — GHCR publishes via the auto-provided `GITHUB_TOKEN` with `packages: write`; PyPI publishes via OIDC `id-token: write` (trusted publishing). |
| Drift of the determinism guarantees | The `predictions_summary_hash` is part of every persisted run and is verified across re-runs; any drift surfaces as a `validate-baseline` failure. |

### 2.2 Out of scope

- **Host OS hardening** — the contributor's local OS and Docker daemon
  configuration are the contributor's responsibility.
- **Network-level attacks** — PUMA does not run network services that
  expose attack surface beyond `localhost` (the dashboard binds
  `0.0.0.0:8501` by default but is intended for the local host).
- **Physical access** — full-disk encryption and similar host-level
  defenses are out of scope.
- **Model-output adversarial attacks** — prompt-injection,
  jailbreaking, and similar attacks against the model itself are
  research-grade concerns and are tracked separately (post-v4.x
  research agenda).
- **Vulnerabilities in third-party services** — Ollama, the SQLAlchemy
  driver, Streamlit, etc. are reported upstream and tracked here via
  `pip-audit` advisories.

---

## 3. Determinism guarantees

PUMA's reproducibility is a security property: it is what makes a
benchmark result auditable.

| Guarantee | Where it is enforced |
|---|---|
| Fixed RNG seed `42` | `src/puma/runtime/` — every spec uses `inference.seed: 42` unless explicitly overridden. |
| Fixed sampling temperature `0.0` | Spec default; overrides surface in the run summary. |
| Pinned model digest | The Ollama manifest digest (e.g. `qwen2.5:3b` → `357c53fb659c`) is captured in the `runs` table when the run starts. Re-running the same spec against a different digest is detectable as a hash mismatch. |
| Bi-temporal SQLite audit trail | `runs`, `instances`, `predictions`, `metrics`, `emissions`, `profile_snapshots` tables. Every row carries `created_at`; no row is mutated post-write. |
| `predictions_summary_hash` | Computed deterministically over the (instance_id, prediction) pairs in canonical order; recorded on the run and shipped in every PUMA Community submission. Byte-identical across re-runs of the same spec on the same hardware-and-runtime profile. |

The `puma validate-baseline` command compares the current canonical
spec's metrics against a reference value and exits `1` on drift —
the gate that turns determinism into a release-blocking check.

---

## 4. No outbound telemetry by default

The default configuration of PUMA makes no outbound network calls
during a benchmark run.

| Surface | Default | How to opt in |
|---|---|---|
| Inference | Local Ollama daemon (`http://localhost:11434`) — no outbound calls. | The endpoint can be reconfigured via `OLLAMA_HOST` for advanced setups; PUMA itself never reaches a remote inference provider. |
| Carbon tracking (CodeCarbon) | Off-line measurement — energy and CO₂ are computed from local CPU/GPU counters; no network call required. | `sustainability.codecarbon: true` in the run-spec enables the measurement; even when enabled, CodeCarbon's default emission factors are used locally. |
| Publishing (PUMA Community) | Off — `puma share-results --dry-run` packages the artifact locally without any network call. | `puma share-results` (no `--dry-run`) opens a PR against `pumacp/puma-community` over `api.github.com` after `puma auth login` has stored a PAT locally at `~/.puma/credentials.toml` (`0600`). |
| Server-side verification | Off — local `puma community verify-hash` recomputes the hash on-disk. | `puma community verify-hash --remote` calls the public verifier service. |
| Web fetches inside the CLI | Off — there are no `web_search` / `web_fetch` paths in the production CLI. | N/A. |

If you need a fully air-gapped operation, set `sustainability.codecarbon: false`,
do not invoke `puma share-results`, and run only on a host where the
Ollama daemon is local.

---

## 5. Submission integrity (PUMA Community)

Every artifact shared with the public benchmark hub is integrity-checked
end-to-end.

- **Hash format**: `SHA-256` hex digest over the canonical tuple
  `(instance_id, prediction)` for every row, sorted by `instance_id`,
  serialized as compact JSON with stable key order.
- **Where it is stored**: in the submission JSON itself
  (`predictions_summary_hash` field) and as a row in the `metrics`
  table of the originating run.
- **Schema**: `schema/submission.v1.json` is **immutable** (P3 constraint).
  Any drift is detected by JSON Schema validation in the `puma
  community validate` path and rejected before submission.
- **Local verification**: `puma community verify-hash <submission.json> --predictions <jsonl>`
  recomputes the hash on-disk and compares it to the declared value.
  Exit `0` means verified, exit `1` means mismatch, exit `2` means
  the input could not be read.
- **Server-side verification**: `puma community verify-hash --remote`
  calls the public verifier service; the service hashes a different
  input shape (D23 — tracked in `docs/known_debt.md`) so the
  `--remote` flag returns `mismatch` by construction for schema v1.0.0
  submissions even when the local hash is correct. Reconciliation is
  deferred to v4.x with a schema decision; the canonical verification
  path is **local**.
- **Auto-merge**: the `pumacp/puma-community` repository's auto-merge
  workflow only accepts PRs that touch path-restricted submission
  files, refuses any diff outside that path filter, and requires the
  client-side hash to match the schema-declared one.

---

## 6. Git history sanitization

The repository's history was sanitized in **Phase Z-2 (May 2026)** to
remove AI-assistant co-author trailers that had accumulated on
machine-drafted commits. The rewrite:

- Used `git filter-repo` to remove `Co-Authored-By:` trailer lines on
  every commit and every annotated tag, repo-wide.
- Was verified to have no external dependents on the rewritten SHAs
  before force-pushing (no open PRs, no published packages that
  pinned a pre-rewrite SHA).
- Was followed by a `git push --force-with-lease` on `develop` and
  `main` and a re-tag pass to keep `vX.Y.Z` pointing at the
  rewritten commits.

The repo-root `.githooks/commit-msg` hook now strips three classes of
trailer from every future commit locally:

```
Co-authored-by:        # any AI-assistant Co-authored-by line
Signed-off-by: …<AI tool>   # any Signed-off-by line that names an AI tool
Generated-by:          # any Generated-by footer
```

Activation is one-time per fresh clone: `git config core.hooksPath
.githooks`. The new-contributor procedure for setting this is
documented in [`development-workflow.md`](development-workflow.md)
§§6 and 10.6.

The GitHub UI for the repository surfaces commits with the
maintainer's identity as the only author; no AI-tool branding
appears in `git log` output.

---

## 7. Dependency management

| Tool | Workflow | Cadence | Severity gate |
|---|---|---|---|
| `pip-audit` | `.github/workflows/pip-audit.yml` | Every push to `develop`/`main` + every PR + weekly `0 6 * * 1` UTC + manual dispatch | Fails on `HIGH` or `CRITICAL` advisory in any production dependency listed in `requirements.txt`. |
| `bandit` | `.github/workflows/bandit.yml` | Every push to `develop`/`main` + every PR + manual dispatch | Reports `MEDIUM`+ via `-ll`; fails the build on `HIGH` (`-l`). |
| `Trivy` (container) | Appended to `.github/workflows/publish-docker.yml` | Every tag push (`v*`) | Fails on `HIGH` or `CRITICAL` OS or library CVE in the published image; results uploaded as SARIF to the GitHub Security tab. |

The production dependency surface is small and reads from
`requirements.txt` (27 entries: typer, httpx, pydantic, pyyaml,
jinja2, jsonschema, pandas, numpy, scikit-learn, scipy, sqlalchemy,
alembic, psutil, codecarbon, PyGithub, streamlit, langdetect,
structlog, rich, pyfiglet, tomli-w, requests, gradio-client,
matplotlib, seaborn — see the file for the canonical list). The
development-only surface (`requirements-dev.txt`: pytest, pytest-cov,
pytest-asyncio, respx, ruff, mypy, pre-commit) is excluded from
`pip-audit` to avoid blocking on advisories that cannot reach an
end user.

License-compatibility automation is **deferred** from this MVP — see
**§13 Known security debt** entry D32.

---

## 8. Container image security

The published image at `ghcr.io/pumacp/puma:vX.Y.Z` is built from
`Dockerfile.publish` (added in S12.15). Properties:

- **Multi-stage build**: a `builder` stage produces the wheel; the
  `final` stage installs it into a clean image. Build tooling does
  not ship in the final layer.
- **Slim base**: `python:3.11-slim` — minimal Debian-derived layer.
- **Non-root user**: a `puma` user (`uid=1000`) is created in the
  final stage and the `USER puma` directive switches to it before
  `ENTRYPOINT`. The image never runs as `root`.
- **OCI labels**: `org.opencontainers.image.title`,
  `description`, `source`, `documentation`, `licenses` — set at the
  Dockerfile level and reinforced by the
  `docker/metadata-action@v5` step in the publish workflow.
- **Entrypoint**: `puma` — the published image is the CLI; the
  default command is `--help`.
- **No bundled Ollama**: the image expects an Ollama service to be
  reachable on the network (see the project's `docker-compose.yml`
  for the canonical multi-service layout).
- **Trivy scan**: every tag push triggers a `Trivy` scan with
  `severity: CRITICAL,HIGH` and `exit-code: 1`; results upload to the
  GitHub Security tab as SARIF.

SBOM generation (CycloneDX) is **deferred** from this MVP — see
**§13 Known security debt** entry D33.

---

## 9. GitHub Actions security posture

PUMA's CI uses GitHub-hosted `ubuntu-latest` runners with explicit
least-privilege `permissions:` blocks per workflow / per job.

Audit at the time of S12-N2 (current state, develop branch):

| Workflow | Permissions | Notes |
|---|---|---|
| `docs.yml` (build job) | `contents: read` | Minimal — checkout + mkdocs build. |
| `docs.yml` (deploy job) | `contents: write` | Required to push to `gh-pages`. |
| `release.yml` | `contents: write` | Required by `softprops/action-gh-release@v2`. |
| `publish-docker.yml` | `contents: read` + `packages: write` | `packages: write` is required by `docker/login-action` + GHCR push. No long-lived registry credential — `GITHUB_TOKEN` only. |
| `publish-pypi.yml` | `id-token: write` | OIDC-based trusted publishing — no PyPI token in repo secrets. |
| `wiki-sync.yml` | `contents: write` | Required to push to the `puma.wiki.git` companion repo. |
| `lint-and-test.yml` | (none declared) | Inherits the repo-default permissions. Worth tightening to explicit `contents: read` in a follow-up — tracked as an audit finding, not blocking this PR. |
| `smoke.yml` | (none declared) | Same as above — audit finding. |
| `pip-audit.yml` (S12-N2) | `contents: read` | Minimal. |
| `bandit.yml` (S12-N2) | `contents: read` | Minimal. |
| `gitleaks.yml` (S12-N2) | `contents: read` | Minimal. |

GitHub branch protection on `develop` and `main` requires the
`Lint and Test`, `Smoke Test`, and `Docs/build` checks to be green
before merge; the security-tooling checks added in S12-N2 (`pip-audit`,
`bandit`, `gitleaks`) become required after one clean cycle on
`develop` to give time to remediate any first-pass findings.

---

## 10. Brand-scanner enforcement

`tests/integration/test_agent_agnostic_remote.py::test_no_brand_references_in_tracked_tree`
scans the entire tracked tree (via `git grep -i -E`) for the assistant
brand token and its case variants. The test enforces the project's
tool-agnostic posture documented in
[`development-workflow.md`](development-workflow.md) §13.

If you add a test, a config, or a doc that needs to **reason about**
the brand token (e.g., an audit that asserts the brand does not
appear elsewhere), the token must be **assembled from fragments at
runtime**, exactly as `test_agent_agnostic_remote.py` does:

```python
_BRAND = "cl" + "aude"   # not the literal token
```

This idiom is mandatory for any code that handles the brand token as
data; otherwise the repo-wide scanner trips on the literal in your
own file. The pattern is also applied in
`tests/integration/test_security_doc.py` (added in S12-N2) and in
`tests/integration/test_development_workflow_doc.py` (added in
S12-N4).

---

## 11. Vulnerability reporting

The canonical private-disclosure path is documented in
[`SECURITY.md`](https://github.com/pumacp/puma/blob/develop/SECURITY.md)
at the repository root.

In short: email `pumacapstoneproject@gmail.com` with a description,
reproduction steps, the affected version(s), and any suggested
mitigation. Acknowledgement within 72 hours; remediation plan within
30 days; public advisory within 90 days under the standard
coordinated-disclosure timeline.

---

## 12. Audit cadence

| Audit | Frequency |
|---|---|
| `pip-audit` weekly cron | Every Monday at 06:00 UTC. |
| `pip-audit` / `bandit` / `gitleaks` on push | Every push to `develop`/`main` + every PR. |
| `Trivy` on published image | Every tag push (`v*`). |
| Full re-audit (this page, the threat model, the workflow permissions table) | Every minor release (e.g. v4.1.0, v4.2.0) at minimum; on demand otherwise. |
| Hard re-audit (penetration test, dependency tree review) | Annually — first slot post-v4.0.0 release. |

---

## 13. Known security debt

Tracked in [`docs/known_debt.md`](known_debt.md). The S12-N2 MVP
deliberately right-sizes scope; the items below are queued for a
post-Sprint-12 backlog or a future audit cycle:

- **D32** — License compatibility automation. Add `pip-licenses` in
  CI to fail the build on non-permissive licenses entering the
  dependency tree.
- **D33** — SBOM CycloneDX generation. Produce a Software Bill of
  Materials in CycloneDX format and attach it to every published
  release artifact.
- **D34** — Mutation testing on `src/puma/community/integrity.py`.
  Use `mutmut` or equivalent to verify the integrity-hash test
  coverage actually catches subtle mutations of the canonical hash
  procedure.
- **D35** — Cross-platform install test. Verify the published wheel
  installs and the CLI starts on Linux, macOS (x86_64 + arm64), and
  Windows; today only Linux is exercised in CI.

---

Last reviewed: 2026-05-31 (S12-N2 MVP).
