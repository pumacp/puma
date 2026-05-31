# Security Policy

## Supported Versions

PUMA follows [Semantic Versioning](https://semver.org/). Security fixes
are backported to the latest minor release on the active major line.

| Version | Supported |
| ------- | --------- |
| 4.x (when released) | yes |
| 3.x | yes |
| < 3.0 | no |

The active major line is updated on each release. When `v4.0.0` ships,
the 3.x line stays supported for a 90-day grace period before moving
to "no" — see `docs/security.md` for the full backport policy.

## Reporting a Vulnerability

If you believe you have found a security vulnerability in PUMA, please
**do not** open a public GitHub Issue. Report it privately by email:

**pumacapstoneproject@gmail.com**

Include in your report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, or a minimal proof-of-concept.
- The affected version(s) of PUMA.
- Any suggested mitigation, if applicable.

We will acknowledge receipt within **72 hours** and aim to provide a
remediation plan within **30 days** for confirmed vulnerabilities. We
will credit you in the release notes unless you prefer to remain
anonymous (see *Recognition* below).

A GPG public key for end-to-end encryption of the report is on the
roadmap and will be published here when generated; until then, email
in plaintext is the supported channel.

## Disclosure Timeline

PUMA follows a coordinated-disclosure approach:

- **Day 0** — receipt acknowledged (within 72 hours of the report).
- **Day 30** — remediation plan shared with the reporter for confirmed
  vulnerabilities.
- **Day 60** — patched release available on the active major line.
- **Day 90** — public advisory + full vulnerability details published.

The 30/60/90-day windows are upper bounds; we ship faster when the
severity warrants it. Critical-severity issues with a known exploit
path may compress the entire timeline to under 14 days.

## Scope

In scope:

- The PUMA Python package (`src/puma/`).
- The Docker setup and orchestration (`docker-compose.yml`,
  `Dockerfile`, `Dockerfile.publish`).
- GitHub Actions workflows (`.github/workflows/`).
- The `puma share-results` client and credential handling.
- The published image at `ghcr.io/pumacp/puma`.
- The published package at `puma-cp` on PyPI.

Out of scope (report upstream to the respective projects or owners):

- Vulnerabilities in third-party dependencies (Ollama, SQLAlchemy,
  Streamlit, etc.). Report directly to those projects; we will track
  them via `pip-audit` and `Trivy` in CI and ship coordinated upgrades.
- Vulnerabilities in the user's local environment (operating system,
  Docker daemon, network configuration).
- Submission disputes — open a regular GitHub Issue on the
  `pumacp/puma-community` repository.
- Social engineering of the maintainer or contributors.
- Denial-of-service attacks against the project's social or
  communication channels.

## Security Commitments

PUMA's threat model and security posture are documented in detail at
[`docs/security.md`](docs/security.md) (also published at
<https://pumacp.github.io/puma/security/>). In summary:

- **Local-first inference** — all model calls go through a local
  Ollama daemon by default; no outbound API calls during a benchmark
  run.
- **Deterministic execution** — fixed `seed=42` and `temperature=0.0`
  at the inference layer; the predictions hash is byte-identical
  across runs given the same inputs.
- **Submission integrity** — every PUMA Community submission carries
  a `SHA-256` over the canonical predictions tuple; the schema
  (`schema/submission.v1.json`) is immutable; verification is
  available both client-side and via the public verifier service.
- **Sanitized git history** — the project's history was sanitized in
  Phase Z-2 (May 2026) to remove AI-assistant co-author trailers; the
  `.githooks/commit-msg` hook automatically strips equivalent trailers
  from future commits.
- **CI security tooling** — `pip-audit`, `bandit`, `gitleaks`, and
  `Trivy` run on every push to `develop` and `main`; `Trivy` also
  runs on every published image tag.

## Local Credential Storage

PUMA stores GitHub Personal Access Tokens locally at
`~/.puma/credentials.toml` with file permissions `0600` (readable only
by the file owner). The token is never transmitted to any server other
than `api.github.com`. If you suspect your token has been exposed,
revoke it immediately at
<https://github.com/settings/tokens> and re-authenticate with
`puma auth login`.

## Recognition

Confirmed reporters are credited by name (or by handle, or anonymously
— at the reporter's choice) in:

- The release notes of the patched version on GitHub.
- A future `SECURITY-HALL-OF-FAME.md` in this repository once the
  first credited disclosure is published.

We do not currently offer monetary bounties.

## Public Disclosure

After the 90-day window (or sooner if coordinated with the reporter),
the full vulnerability details, the root-cause analysis, and the
patch are published in the affected release's notes and cross-linked
from [`docs/security.md`](docs/security.md).
