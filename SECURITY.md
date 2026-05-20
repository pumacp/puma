# Security Policy

## Supported Versions

PUMA follows semantic versioning. Security fixes are applied to the
latest minor release.

| Version | Supported |
| ------- | --------- |
| 3.x     | Yes       |
| < 3.0   | No        |

## Reporting a Vulnerability

If you believe you have found a security vulnerability in PUMA, please
**do not** open a public GitHub Issue. Instead, report it privately by
email to:

**pumacapstoneproject@gmail.com**

Include in your report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, or a minimal proof-of-concept.
- The affected version(s) of PUMA.
- Any suggested mitigation, if applicable.

We will acknowledge receipt within 7 days and aim to provide a remediation
plan within 30 days for confirmed vulnerabilities. We will credit you in
the release notes unless you prefer to remain anonymous.

## Scope

In scope:

- The PUMA Python package (`src/puma/`).
- The Docker setup and orchestration (`docker-compose.yml`,
  `Dockerfile`).
- GitHub Actions workflows (`.github/workflows/`).
- The `puma share-results` client and credential handling.

Out of scope (report upstream to the respective projects):

- Vulnerabilities in third-party dependencies (Ollama, SQLAlchemy,
  Streamlit, etc.). Please report directly to those projects.
- Vulnerabilities in the user's local environment (operating system,
  Docker daemon, network configuration).
- Submission disputes: open a regular GitHub Issue on the
  `pumacp/puma-community` repository.

## Local credential storage

PUMA stores GitHub Personal Access Tokens locally at
`~/.puma/credentials.toml` with file permissions `0600` (readable only
by the file owner). The token is never transmitted to any server other
than `api.github.com`. If you suspect your token has been exposed,
revoke it immediately at https://github.com/settings/tokens and
re-authenticate with `puma auth login`.

## Disclosure timeline

We follow a coordinated disclosure approach: once a fix is published,
we wait at least 14 days before publishing the full vulnerability
details, to give downstream users time to upgrade.
