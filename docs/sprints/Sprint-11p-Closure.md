# PUMA Sprint 11' — Closure Report

## Sprint identification

| Field | Value |
|-------|-------|
| Sprint name | Sprint 11' (prime) — Post-v3.0.0 Reconciliation |
| Supersedes | Original "Sprint 11 — Post-v2.7.0 Consistency Hardening" (retired; see episode 1) |
| Duration | 2026-05-24 → 2026-05-25 |
| Goal | Reconcile v3.0.0 release artifacts, complete the `puma community` CLI, repair the wiki-sync workflows and the Verifier Space, activate the Kaggle mirror, and clean residual documentation drift — then consolidate and release as **v3.1.0**. |
| Release artifact | **v3.1.0** — tag → `1792be7` (immutable); main at `d66266c` (tree byte-identical to develop). <https://github.com/pumacp/puma/releases/tag/v3.1.0> |
| Safety tag | `sprint11p-pre-hardening` → `0542ce8` (pre-Sprint baseline) |

## Sprint scope and outcomes

| Goal | Outcome |
|------|---------|
| v3.0.0 artifact reconciliation (version, CHANGELOG, RELEASES, INDEX) | **Met** — S11'.1 + S11'.1.1 |
| Community CLI (`browse`/`pull`/`verify-hash`/`validate`) | **Met** — S11'.2, 34 tests, coverage 80-89% |
| HF dataset namespace canonicalization | **Met** — S11'.3 (companion PR #2; 7 HF refs, 6 Kaggle preserved per P10) |
| Wiki-sync workflow repair | **Met** — S11'.4 (puma commit + companion PR #3); both `/wiki` render HTTP 200 |
| Verifier Space schema alignment | **Met** — S11'.5 (HF Space @ `d8a4ffd`, RUNNING) |
| Kaggle mirror activation | **Deferred** — S11'.6; workflow fully hardened (companion PR #4), blocked on a Kaggle-internal soft-delete grace period (operational, not technical) |
| Docs drift cleanup | **Met** — S11'.7, scoped to active product surface |
| Regression + release | **Met** — S11'.8 (PR #15) + E.nov (v3.1.0 tag, release, production deploy) |

Out-of-scope discoveries surfaced and recorded rather than actioned: D23 (Verifier/client hash-algorithm mismatch, deferred to v4.x) and the `actions/checkout@v4` Node-20 deprecation (hygiene PR scheduled post-Sprint).

## Phase-by-phase summary

| Phase | Commits | Key outputs | Status |
|-------|---------|-------------|--------|
| S11'.0 | tag + branch | safety tag `sprint11p-pre-hardening`, branch `feature/sprint-11p-reconciliation` | ✅ |
| S11'.1 | 5 (`25b5676`,`abf89fd`,`bd7ad7f`,`11b76e4`,`3a33d45`) | pyproject 3.0.0; CHANGELOG fold under [3.0.0]; `docs/RELEASES/v3.0.0.md`; INDEX status; overview.md | ✅ |
| S11'.1.1 | 1 (`d6c018f`) | dashboard view count 9 → 8 (off-by-one; `_base.py` is a helper) | ✅ |
| S11'.2 | 4 (`6c4fee2`,`7d5eb04`,`57cc749`,`44c9783`) | `puma community` subgroup (4 verbs) + `_community_app.py`; D23 in `known_debt.md`; gradio-client dep; 34 tests | ✅ |
| S11'.3 | companion PR #2 | 7 HF refs `pumacp/` → `pumaproject/` (5 files); 6 Kaggle refs preserved (P10) | ✅ (PR open) |
| S11'.4 | 1 (`e026487`) + companion PR #3 | `wiki-sync.yml` `contents: read` → `write`; both wikis publish (HTTP 200) | ✅ |
| S11'.5 | HF Space @ `d8a4ffd` | strip `sha256:` prefix → schema `^[a-f0-9]{64}$`; Space RUNNING | ✅ |
| S11'.6 | companion PR #4 | Kaggle workflow hardened (`-r zip`, robust create/version, CC-BY-4.0, 46-char title, post-publish HEAD verify) | ⏸ Deferred (platform grace period) |
| S11'.7 | 1 (`b340299`) | test docstring 7 → 8 views; historical-note header on `00-inventory.md` | ✅ |
| S11'.8 | — | full regression (597+7 tests, baselines, coverage); consolidator PR #15 | ✅ |
| E.nov | 4 (`cca6cea`,`f7593a7`,`dbe8988`,`6fd7555`) + deploy PR #17 | version 3.1.0; CHANGELOG [3.1.0]; INDEX; `docs/RELEASES/v3.1.0.md`; merge PR #15 → develop; tag v3.1.0; GitHub release; production deploy to main | ✅ |

12 in-repo commits on `feature/sprint-11p-reconciliation` (merged via PR #15) + 4 release-consolidation commits (E.nov) + 3 companion-repo PRs + 1 HF Space commit.

## Quality state at release (v3.1.0)

Canonical statement: `docs/RELEASES/v3.1.0.md`.

| Metric | Value |
|--------|-------|
| `ruff check` / `ruff format --check` | green |
| `mypy --strict src/puma/` | 0 errors / 81 files |
| `pytest -m "not ollama"` | 597 passed, 1 skipped, 7 deselected |
| `pytest -m ollama` | 7 passed |
| F1 triage baseline | 0.5831 (Δ −0.0036 vs 0.5867 spec; within ±0.01) |
| MAE estimation baseline | 5.7150 bit-exact (Δ +0.0000) |
| Coverage — `browse_cli` | 80% |
| Coverage — `pull_cli` | 87% |
| Coverage — `verify_cli` | 85% |
| Coverage — `validate_cli` | 89% |
| Schema v1.0.0 | unchanged (P3) |
| Federation refs in code | 0 (P4) |

## Discovery-before-write episodes (15 substantive P1 captures + 1 benign expectation correction)

Each episode is a case where empirical reality contradicted a plan assumption and was resolved **before** any write reached the remote. No P1 capture escaped to remote — zero wrong commits pushed.

### Category A — Codebase state assumptions

1. **v3.0.0 baseline discovery** (S11'.0 audit). The repo was already at v3.0.0 (released 2026-05-20); the original plan assumed a v2.7.0 baseline. Resolution: the original Sprint 11 was retired and replaced by Sprint 11' (prime).
2. **D19 → D23 renumber** (S11'.2). "D19" was already used by a closed fairness-scaffolding debt item (v2.0.0 → v2.2.0); the next free id was D23. Resolution: renamed across code + docs before committing.
3. **`raw_predictions_url` schema reality / P13** (S11'.2). The field **is** optional in schema v1.0.0 (`schema_data/submission.v1.json:472`), contrary to the assertion that it was absent. Resolution: reformulated the D23 description and the `verify_cli.py` `--remote` behavior.
4. **Two `sha256:` occurrences in Verifier `app.py`** (S11'.5). The plan assumed one (line 26, functional); a second existed (line 137, UI placeholder). Resolution: fixed both for consistency, so the grep-empty check holds.

### Category B — Documentation policy

5. **Historical-vs-active distinction in grep-empty criteria** (S11'.7). A literal "grep `7 views` empty" criterion would have falsified the CHANGELOG (v2.0.0 / v2.3.0 genuinely shipped 7 views) and overwritten archived planning docs. Resolution: the criterion applies to the **active** product surface only; historical archives are preserved verbatim, with a header note for context where helpful (`docs/community/00-inventory.md`).

### Category C — Platform-API quirks (Kaggle)

6. **Kaggle CLI exit-0-on-error** (S11'.6 attempts 1-2). `kaggle datasets create` returns exit 0 even on real errors ("title already in use"), masking failure. Resolution: a post-publish `curl` HEAD verification step on the public dataset URL was added to the workflow.
7. **`--dir-mode` required for folders** (S11'.6 attempt 1). Without `-r zip`/`tar`, the CLI silently skips subdirectories (it uploaded only LICENSE + README, not `submissions/` or `schema/`). Resolution: `-r zip` added.
8. **"MIT" is not a Kaggle license slug** (S11'.6 attempt 2). The repo is MIT-licensed but Kaggle's dataset-license list excludes "MIT". Resolution: `dataset-metadata.json` switched to `CC-BY-4.0` (matching the HF mirror).
9. **Title length cap is 50, not 80** (S11'.6 attempt 4). The audit assumed 80 chars; the CLI error reported a 6-50 limit. Resolution: title shortened to 46 chars.
10. **Title collision is slug-keyed** (S11'.6 attempt 5). The "title already in use" error fired for a brand-new title; diagnosis showed the collision is on the slug held in a soft-delete grace period. Resolution: deferred to grace-period expiry; the workflow is fully hardened in PR #4.

### Category D — SaaS server-side policies (GitHub)

11. **`main` has divergent squash-merge history** (E.nov Step 11, iteration 1). Fast-forward from develop is impossible. Resolution: deploy via PR.
12. **GitHub UI squash-merge blocked by ancestry artifacts** (iteration 2). Squash history causes add/add conflicts on files predating the merge-base. Resolution: build the deploy commit locally.
13. **`main` is PR-only with `enforce_admins: true`** (iteration 4). Direct push (even a verified FF) is rejected by branch protection; required check `lint-and-test`, 0 reviews. Resolution: deploy branch + PR #17 + rebase-and-merge, gated by `lint-and-test`.
14. **GitHub rebase-and-merge rewrites the commit SHA** (iteration 4 close). The committer timestamp is recomputed (`af855e2` → `d66266c`); tree, message, and parent are preserved. **Benign expectation correction, not a P1 halt** — the substantive guarantee (tree byte-identical to develop) holds.

### Category E — Git semantics

15. **`-X theirs` cannot reproduce a restructured file** (E.nov Step 11, iteration 3). A 3-way merge preserves non-conflicting hunks from both sides, producing a hybrid CHANGELOG (S11'.1 had restructured it). Resolution: use direct **tree replacement** (`git checkout origin/develop -- .`), not a merge. The tree-equality guard caught the hybrid before any commit.

**Total: 15 substantive P1 captures + 1 benign expectation correction (#14).** Episodes 1-15 are enumerated above (14 substantive + the benign #14); the 16th episode — the 15th substantive, S11'.10.a's integration-gap discovery — spawned three debt items (D24/D25/D26) and is detailed in its own section below. The post-publish HEAD verification (episode 6) and the tree-equality / parent-FF guards (episodes 11-15) each caught a defect at runtime, validating the defensive-engineering patterns empirically.

## S11'.10.a discovery: end-to-end integration gaps (episode 16)

The Sprint 11'.10 attempt to perform a live publication demo (canonical runner → `share-results` → community-CLI publication pipeline) surfaced three latent integration gaps that no unit test exercised:

- **D24** (`docs/known_debt.md`): canonical specs do not declare `profile_required`, so `Run.profile` is NULL (`builder.py:320-321`).
- **D25** (`docs/known_debt.md`): canonical specs disable codecarbon, so no emissions record is produced (`builder.py:330`).
- **D26** (`docs/known_debt.md`): `src/puma/orchestrator/runner.py:526` never populates `ProfileSnapshot.extra`; the publication builder requires `extra['cpu_cores']` (`builder.py:365`).

D24 and D25 are spec-level (configuration); both were bridged locally during S11'.10.a via an untracked one-off demo spec (`specs/runs/demo_triage_s11p.yaml`, `profile_required: gpu-entry`, F1 stayed 0.5831 bit-exact). D26 is src/-level (code change required) and was therefore the hard blocker under S11'.10.a's no-src-edit constraint: `share-results` cannot consume any run this runner produces.

These gaps remained latent through v3.1.0 release because all test fixtures (e.g. `tests/community/conftest.py:218`) hand-craft `Run.profile` and `ProfileSnapshot.extra`, never exercising the full pipeline with runner output. Unit tests at 80-89% coverage on the community CLI did not catch them.

### Methodological insight

Component-level testing at high coverage does not substitute for end-to-end integration exercise with real artifacts. The gap only surfaced when the actual end-to-end flow was attempted with the v3.1.0 product. Rather than fabricate the missing emissions/snapshot metadata to force a demo artifact — which would be academically dishonest — the live demo was halted and the gaps documented.

### Resolution

Sprint 11'.10 was re-scoped from "live publication demo" to "documented integration-gap analysis + CLI smoke proof" (`docs/sprints/Sprint-11p-CLI-Smoke.md`, confirming the community CLI is operational on the available placeholder fixture). The live publication demo is deferred to a future Sprint that fixes D26 in code and refines the canonical specs for D24/D25. Estimated effort to unblock the end-to-end demo: < 1 day plus a small integration test to prevent regression.

## Deferred work

### D23 — Verifier algorithm/schema mismatch
- **Status:** open; deferred to v4.x with a schema decision.
- **Scope:** the client hashes a 4-field CSV `(instance_id, predicted_label, predicted_value, prompt_hash)` from the DB; the Verifier Space hashes a 2-field JSONL `(instance_id, prediction)` fetched from `raw_predictions_url`. They differ by construction.
- **Workaround:** `puma community verify-hash --remote` detects the systematic mismatch and emits a D23-aware warning; local verification is canonical.
- **Reference:** `docs/known_debt.md`.

### S11'.6 — Kaggle mirror activation
- **Status:** workflow fully hardened (companion PR #4 on `pumacp/puma-community`); publication pending the Kaggle-internal soft-delete grace period reserving the slug `pumacp/puma-community-submissions`.
- **Action when unblocked:** re-trigger `mirror-kaggle.yml` on the PR-#4 branch — no further code change; the post-publish HEAD verification will self-confirm.
- **Owner note:** workflow ready since 2026-05-25; grace period typically hours to days.

### Companion-repo PRs
`pumacp/puma-community` #2, #3, #4 — all open; merge decision is separate from this Sprint.

### actions/checkout@v4 deprecation
Node 20 deprecates June 2026; affects `wiki-sync.yml`, `mirror-*.yml`, `lint-and-test.yml`. Hygiene PR scheduled post-E.nov (not in Sprint 11' scope).

## Companion repository state

| Repo / artifact | State |
|-----------------|-------|
| `pumacp/puma-community` PR #2 (HF namespace) | open, mergeable |
| `pumacp/puma-community` PR #3 (wiki-sync fix) | open, mergeable |
| `pumacp/puma-community` PR #4 (Kaggle hardening) | open; deploy blocked on Kaggle grace period |
| `pumaproject/puma-verifier` HF Space @ `d8a4ffd` | deployed, RUNNING; `/verify` endpoint live |

## References

**Pull requests (pumacp/puma):**
- #15 — Sprint 11' main consolidation → develop (MERGED)
- #16 — initial production-deploy attempt → main (CLOSED, superseded by #17)
- #17 — Sprint 11' production deploy → main, rebase-and-merge (MERGED)

**Pull requests (pumacp/puma-community):** #2, #3, #4 (companion).

**Tags:**
- `sprint11p-pre-hardening` → `0542ce8` (safety baseline)
- `v3.0.0` (prior release, immutable)
- `v3.1.0` → `1792be7` (Sprint 11' release, immutable)
- `v2.7.0-academic` (local-only academic snapshot, preserved)

**Releases:** v3.1.0 — <https://github.com/pumacp/puma/releases/tag/v3.1.0>

**HF Spaces:** `pumaproject/puma-verifier` @ `d8a4ffd` (RUNNING).

## Methodological notes for future Sprints

- **Pre-Sprint audit must include server-side policies** (branch protection, required status checks, allowed merge methods), not just codebase state. Episodes 11-13 cost four deploy iterations that an upfront protection check would have pre-empted.
- **"grep-empty" criteria must distinguish active vs historical surface up front**, or they force a choice between falsifying history and failing acceptance (episode 5).
- **Platform CLI behavior — especially exit codes — cannot be assumed from documentation.** A post-publish verification step (HEAD on the public artifact) is a generic defensive pattern that catches false success (episode 6).
- **Tree replacement (`git checkout <ref> -- .`) is the correct primitive for "make my branch's tree equal that ref's tree"; merge strategies are not** — a 3-way merge cannot reproduce a restructured file (episode 15). A `git write-tree` equality guard before commit makes this safe.
- **A retry cap (3 by default) plus explicit authorization to exceed it when new information justifies a grounded retry** prevents runaway loops while preserving forward progress (S11'.6 ran to a 5th attempt, each yielding a distinct new finding).
- **The academic memoria's Anexos (UOC `.docx`) are maintained separately** from in-repo developer documentation; this closure report is the in-repo artifact, and Anexo G is the academic counterpart enumerating the same discovery episodes.
