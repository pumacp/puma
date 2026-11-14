# Sprint 12 retrospective

Sprint 12 closed with the **v4.0.0** release of PUMA. This retrospective records
what the sprint set out to do, what it delivered, what it validated end to end,
what went well, what was deferred, the methodological lessons, and the
post-Sprint-12 maintenance backlog.

## 1. Sprint goal

The goal was to ship **v4.0.0** as a coherent, publicly usable milestone: a
community submission infrastructure, a security audit MVP, a comprehensive
documentation surface, and — the decisive proof point — the **first inaugural
production submission** landed end to end on the public leaderboard. The release
had to be reproducible, English-only across all public surfaces, and free of any
brand or internal-context regressions.

## 2. Delivered

| Area | Outcome |
|------|---------|
| Publishing | PyPI + Docker (ghcr.io) workflows; `puma-cp==4.0.0` live on PyPI (PR #45) |
| Dashboard | Multi-model comparison view + corporate monochrome palette (PR #46) |
| Branding | README channel-directory restructure; acrostic visual flexibility (PR #47) |
| Docs sync | mkdocs nav 6 → 28 public pages; D30 resolved (PR #48) |
| Contribution | Manual IDE contribution workflow reference (PR #49) |
| Security | Audit MVP: pip-audit + bandit + gitleaks + Trivy + `SECURITY.md` (PR #50) |
| Reference | Consolidated technical reference, ~5100 words, 17-decision timeline (PR #51) |
| Milestone | Inaugural submission documented end to end (PR #52) |
| Release | v4.0.0 ceremony: release-prep (PR #53) + develop→main (PR #54) |

Across the sprint: **9 pull requests**, **8 new documentation pages**, a
**30+-term glossary**, a **9-check programmatic validation** pipeline for
submissions, SARIF integration with the GitHub Security tab, and the first
official community submission archived and reproducible.

## 3. Validated end to end

The inaugural submission proved the full pipeline: inference → submission JSON →
schema validation + integrity hash → push to the community repository → Hugging
Face dataset mirror → leaderboard rendering. The submission was
`qwen2.5:3b` on `triage_jira` / `zero_shot`, F1-macro **0.3898**, archived under
`predictions_summary_hash`
`f60423ca6a6e9b033f0f89ac5a5a127d889a6e2627fc07c480c44bfdf53857ec`. Even though
D-39 (a verifier API drift) currently hides the row visually behind a
verified-only filter, the data is publicly verifiable: anyone can recompute the
hash from the published predictions and confirm it deterministically. The
milestone stands independent of the cosmetic workflow gap.

## 4. What went well

- **Discovery-before-write held at every layer.** Each phase began by reading
  the current repository state before editing. This caught several stale
  assumptions early — most consequentially during the release ceremony, when the
  develop→main merge surfaced that `main` had diverged into an older parallel
  line carrying brand regressions; resolving to develop's audited tree avoided
  reintroducing them.
- **Atomic commits plus per-phase quality gates** kept the release
  reproducible. Every phase ran ruff, the test suite, and a strict docs build
  before pushing, so regressions surfaced at the phase boundary rather than at
  release time.
- **The security gate proved its value in production.** During the v4.0.0
  publish, Trivy correctly blocked a vulnerable container image — 3 HIGH (and 3
  MEDIUM, 1 LOW; 0 CRITICAL) base-image findings tripped the configured gate, so
  the image was not published. This is exactly the behaviour a release pipeline
  should exhibit.
- **Honesty in the release notes.** The container gap was documented plainly in
  the public release notes rather than hidden, with the PyPI package offered as
  the working install path.
- **Post-publish verification caught packaging gaps early.** Installing the
  published wheel in a clean environment surfaced D-42 (missing bundled config)
  and D-43 (no `--version` flag) before a larger number of users hit them.

## 5. What surfaced as deferred

Sprint 12 deferred six items (D-38 through D-43). None blocks the release; the
architecture isolated each so the milestone could still ship:

- **D-38** — `validate-submission` references a non-existent action version.
- **D-39** — `verify-integrity` broken by a verifier-client API drift; the
  inaugural submission is therefore `self-attested`.
- **D-40** — `puma share-results` hangs after the Review panel.
- **D-41** — container image v4.0.0 blocked by 3 HIGH base-image CVEs.
- **D-42** — PyPI wheel does not bundle `config/profiles.yaml`.
- **D-43** — the CLI does not expose a top-level `--version` flag.

## 6. Methodological lessons

- **A two-layer prompt structure — a coordinator level over an executor
  level — scaled cleanly across fifteen phases.** Keeping orchestration separate
  from execution kept each phase small and auditable.
- **Discovery-before-write at both layers** caught multiple cases where the
  coordinator's mental model of the repository had drifted from its actual
  state; the executor's audit step corrected them in place each time.
- **Pause-and-surface gates at irreversible operations** (tag push, the
  develop→main merge) earned their keep: the merge gate is what caught the
  divergence in `main` before it could reintroduce forbidden-token regressions.
- **Programmatic validation provides defense in depth.** The 9-check submission
  gate complements schema validation and the integrity hash rather than
  duplicating them.
- **Post-publish verification belongs in every release ceremony.** Installing
  the artefact in a clean environment is a cheap, high-value gate; here it
  surfaced two packaging defects the in-tree test suite could not, because
  source-clone installs mask them.

## 7. Post-Sprint-12 maintenance backlog

Cross-reference `known_debt.md` (D-38 through D-43):

- **v4.0.1 patch release** — container CVE fix (D-41), PyPI wheel packaging fix
  (D-42, bundle `config/profiles.yaml`), CLI `--version` flag (D-43),
  `validate-submission` action pin (D-38), verifier-client kwarg fix (D-39), and
  an investigation of the `share-results` hang (D-40).
- **PyPI Trusted Publishers (OIDC) migration** plus restricting the publish
  token to project scope.
- **Workflow action version updates** ahead of the Node 20 → 24 deprecation
  (2026-06-16) and the CodeQL action v3 deprecation.
- **Community-repository `wiki-sync.yml` `master` → `main` fix**, parallel to the
  same fix landed in this repository during this closure phase.

## 8. Closing

PUMA v4.0.0 is the canonical Sprint 12 milestone: the community submission
infrastructure is live, the security architecture has been validated in
production, the documentation surface is publicly accessible, and the first
inaugural submission is archived and reproducible by any third party who can
recompute the `predictions_summary_hash` from the published predictions. The
platform's core value proposition — local-first, privacy-preserving,
reproducible LLM benchmarks for ICT project-management tasks — is now operational
and demonstrably so.
