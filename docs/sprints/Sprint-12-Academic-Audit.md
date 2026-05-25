# Sprint 12 — Academic Audit (FASE A+B detection report)

**Status:** Awaiting maintainer review (PAUSE 1)
**Phase:** Sprint 12 S12.4 (detection only — no content changes)
**Branch:** `audit/sprint12-academic-audit`
**Generated:** 2026-05-25
**Detector:** `scripts/audit_academic_terms.sh` (ripgrep, re-runnable)
**Total matches:** 367 across 4 of 7 categories; 142 files scanned.

**Default classification distribution (from the detector):**

| Category | Matches | Script default |
|---|---:|---|
| academic-identity | 52 | REEMPLAZAR |
| legacy-naming (AgentPM) | 0 | — |
| non-existent-method ("MIT Student Method") | 0 | — |
| forbidden-term-HELM | **0** | CRITICAL (must be 0) ✅ |
| forbidden-term-federation | 43 | DUDOSO |
| citation-non-registered | 7 | DUDOSO |
| sprint-internal-language | 265 | DUDOSO |

## Critical alerts

**None.** The `forbidden-term-HELM` category returned **0 matches** across all
in-scope files. Legacy naming (`AgentPM`) and the non-existent "MIT Student
Method" also returned 0 matches.

## How to review this report (PAUSE 1)

For each finding below, in the PR review comments write:

- `✓` — approve: S12.5 applies the proposed change verbatim.
- `✗` — reject: S12.5 leaves the original text unchanged.
- `✎ <text>` — modify: S12.5 applies your edited version.

**Defaults are conservative.** No item is changed without an explicit `✓`.
Both `REEMPLAZAR` and `DUDOSO` items default to "no change" if unreviewed.
This phase applies nothing; S12.5 applies only approved items.

A reproducible, complete, line-level enumeration of every match (all 367) is in
the **Appendix** at the end of this document (verbatim detector output); the
tables below add refined classification and proposed replacements.

## Findings by category

### 1. academic-identity (52 matches)

**1a. Actionable — REEMPLAZAR (user-facing or newly-introduced content).**
These appear in CLI help text (rendered by `puma <cmd> --help`) or in current
public docs, and leak academic-annex / degree-project identity.

| # | File:Line | Match (excerpt) | Proposed replacement | Class |
|---|---|---|---|---|
| 1 | src/puma/cli.py:434 | `List runs … headline metrics (Anexo F § A.2.5).` | drop the `(Anexo F § A.2.5)` parenthetical | REEMPLAZAR |
| 2 | src/puma/cli.py:546 | `List models … Ollama volume (Anexo F § A.2.6).` | drop the `(Anexo F § A.2.6)` parenthetical | REEMPLAZAR |
| 3 | src/puma/cli.py:620 | `Prepare canonical datasets … — Anexo F § A.2.1.` | drop the `— Anexo F § A.2.1` suffix | REEMPLAZAR |
| 4 | src/puma/cli.py:688 | `Wilcoxon … two runs (Anexo F § A.2.2).` | drop the `(Anexo F § A.2.2)` parenthetical | REEMPLAZAR |
| 5 | src/puma/cli.py:816 | `Bias analysis … (Anexo F § A.2.3).` | drop the `(Anexo F § A.2.3)` parenthetical | REEMPLAZAR |
| 6 | src/puma/cli.py:976 | `Generate consolidated plots … (Anexo F § A.2.4).` | drop the `(Anexo F § A.2.4)` parenthetical | REEMPLAZAR |
| 7 | docs/sustainability.md:137 | `…deferred to the final memoria write-up…` | `…deferred to future project documentation…` | REEMPLAZAR |
| 8 | docs/PROJECT_TECHNICAL_CLOSURE.md:4 | `technical implementation scope for the TFG defence cycle.` | `technical implementation scope for the project.` | REEMPLAZAR |
| 9 | docs/PROJECT_TECHNICAL_CLOSURE.md:129–130 | `…marginal value of memoria redaction … for the TFG defence cycle.` | `…marginal value of further documentation.` | REEMPLAZAR |
| 10 | docs/PROJECT_TECHNICAL_CLOSURE.md:135 | `post-defence work outside the TFG scope.` | `future work outside the current project scope.` | REEMPLAZAR |
| 11 | docs/anexo_F_cli_reference.md:14 | `…disponible en la memoria del TFG.` | `…disponible en la documentación del proyecto.` | REEMPLAZAR |
| 12 | docs/anexo_F_cli_reference.md:183 | `…completa del Anexo F entregada con la memoria del TFG.` | `…referencia completa de comandos del proyecto.` | REEMPLAZAR |

> Note on `docs/anexo_F_cli_reference.md`: the file is itself named and titled as
> an academic annex ("Anexo F — Catálogo de comandos…"). Renaming/retitling the
> whole document is larger than a line edit and is flagged **DUDOSO** (item in
> 1b); only the two `memoria del TFG` sentences above are proposed for edit here.

**1b. DUDOSO — maintainer adjudicates (code comments, doc identity, sprints).**

| File:Line | Match (excerpt) | Why DUDOSO | Class |
|---|---|---|---|
| src/puma/cli.py:418 | `# ── Sprint 7 — CLI completeness (Anexo F § A.2)` | code comment, not rendered to users | DUDOSO |
| src/puma/community/{browse,validate,pull,verify}_cli.py:1 | module docstrings `(Anexo F.16.5–.8)` | module docstrings are not shown in `--help` | DUDOSO |
| docs/anexo_F_cli_reference.md:1 | `# Anexo F — Catálogo de comandos…` | document title/identity; rename is broader scope | DUDOSO |
| docs/sprints/Sprint-11p-Closure.md:176 | `academic memoria's Anexos (UOC .docx) maintained separately` | sprints/ permissive for Sprint IDs, but this names **UOC** + academic memoria | DUDOSO |
| docs/community/00-inventory.md:330–331, 451 | quotes "memoria redaction … TFG defence cycle"; "reviewer of the memoria" | internal planning archive quoting academic context | DUDOSO |
| docs/known_debt.md:62 | D11 row (internal operational documents) | matched on broad term; likely benign | DUDOSO |

**1c. MANTENER — technical history (CHANGELOG / RELEASES).**
`Anexo F`/`Anexo G`/`academic memoria` references describing past work in
`CHANGELOG.md` (lines 28, 75–76, 581, 584, 587, 626), `docs/RELEASES/v2.4.0.md`
(9, 11–12, 18, 35, 37, 46, 79, 83, 93), `docs/RELEASES/v3.1.0.md` (18, 73), and
the `docs/community/00-inventory.md` command-inventory rows (189–194, 273, 284)
are historical records of feature provenance. Default **MANTENER**; the
maintainer may still `✎` any they want neutralized. (All enumerated in Appendix.)

### 2. legacy-naming — AgentPM (0 matches)

No occurrences. Nothing to do.

### 3. non-existent-method — "MIT Student Method" (0 matches)

No occurrences. ("Keshav's Three-Pass Method" is the verified equivalent had any
been found.)

### 4. forbidden-term-HELM (0 matches)

No occurrences in any in-scope file. **This is the required state.**

### 5. forbidden-term-federation (43 matches, default DUDOSO)

Per the S11'.7 classification, historical archives are exempt; new public content
is not.

- **MANTENER (historical / meta).** 36 of 43 are in `docs/community/00-inventory.md`
  — an internal planning/inventory archive that documents the pre-v3.0.0
  "Federation" → "PUMA Community" rename and the design constraints of a future
  opt-in feature. Plus meta-references that *count* federation occurrences
  (`docs/sprints/Sprint-11p-Closure.md:64` "Federation refs in code | 0 (P4)";
  `docs/RELEASES/v3.1.0.md:40` "zero federation references in code") and
  `CHANGELOG.md:39` ("pre-v3.0.0 'federation' terminology; body preserved
  verbatim"). These describe or count the term; they don't brand the project
  with it. Default **MANTENER**.
- **DUDOSO — review.** `wiki/Publishing-Results.md:4` — *"a public federation hub
  where users of the PUMA benchmarking tool share their…"* This is current,
  user-facing wiki prose using "federation hub" as a live concept. Recommend the
  maintainer decide whether to neutralize to "community hub" (consistent with the
  v3.0.0 "PUMA Community" rename). **DUDOSO.**

(Full 43 in Appendix.)

### 6. citation-non-registered (7 matches, default DUDOSO)

Citations outside the approved registry (`docs/internal/.../PROMPT-00-MASTER.md`:
Strubell 2019, Guo 2017, Kitchenham 2004, Cohen 1988). All seven are **real,
legitimate** references — none is fabricated:

| File:Line | Citation | Domain |
|---|---|---|
| CHANGELOG.md:833, 887 | Caliskan et al. (2017), Bolukbasi et al. (2016) | bias/fairness |
| docs/RELEASES/v2.2.0.md:70 | Caliskan et al. (2017), Bolukbasi et al. (2016) | bias/fairness |
| docs/PROJECT_TECHNICAL_CLOSURE.md:83–84 | Caliskan 2017, Bolukbasi 2016, Tatman 2017 | bias/fairness |
| docs/metrics_reference.md:201 | Lacoste et al. (2019) — CodeCarbon paper | sustainability |
| docs/results/bias_evaluation.md:16 | Caliskan 2017; Bolukbasi 2016 | bias/fairness |

**Recommendation (DUDOSO):** these are not errors to remove but references to
**ratify** — likely add Caliskan 2017, Bolukbasi 2016, Tatman 2017, and Lacoste
2019 to the approved registry rather than delete them. Maintainer decides; no
deletion proposed.

### 7. sprint-internal-language (265 matches, default DUDOSO → mostly MANTENER)

Sprint numbers, `S12.x` phase IDs, `D2x` debt items, `PAUSE`/`FASE` markers.
Concentrated in technical-history documents, where they are legitimate per the
permissive threshold:

| File | Matches | Refined default |
|---|---:|---|
| docs/known_debt.md | 63 | MANTENER (debt log) |
| docs/sprints/Sprint-11p-Closure.md | 49 | MANTENER (sprint report) |
| CHANGELOG.md | 35 | MANTENER (changelog) |
| docs/community/00-inventory.md | 16 | MANTENER (inventory) |
| docs/RELEASES/*.md | ~50 | MANTENER (release notes) |
| src/**/*.py (comments) | ~18 | MANTENER (code history) |
| **docs/sustainability.md** | **4** | **DUDOSO (user-facing — "D25"/"Sprint 12"/"D15"/"D27")** |
| docs/results/*.md | ~12 | MANTENER (results write-ups) |

**Only DUDOSO subset for review:** `docs/sustainability.md` (a public document
authored in S12.3) references debt-item IDs `D25`, `D15`, `D27` and "Sprint 12".
The maintainer may want these phrased without internal IDs in a public doc. All
other sprint-internal matches default **MANTENER**. (Full 265 in Appendix.)

## Files with zero matches (coverage spot-check)

The detector scanned 142 files. In-scope top-level files `README.md`,
`CONTRIBUTING.md`, and `LICENSE` (if present) returned **no** matches in any
category — the user's first-contact documents are already clean. `.github/`
templates and workflow free-text returned no matches.

## Methodology

The detector is `scripts/audit_academic_terms.sh` (ripgrep, PCRE2,
case-insensitive — a superset of case-sensitive). Its pattern set is fixed and
documented in the script header. It honours `.gitignore`, so the gitignored
`docs/internal/` (which is **not** part of the published repo and intentionally
contains the academic prompt registry) is excluded; an explicit exclude
reinforces this. False-positive bias is intentional: ambiguous matches are
surfaced as DUDOSO rather than silently dropped. Re-run with
`bash scripts/audit_academic_terms.sh`.

## Out of scope for this report

- `tests/` (test fixtures may contain anything for test reasons)
- commit history (immutable; not audited)
- companion repos (puma-community, puma-vault, puma-leaderboard, puma-verifier)
- `docs/internal/` (gitignored; not published)
- the Anexos `.docx` (maintained outside this repo by maintainer convention)

## Appendix — complete detector output (verbatim, all 367 matches)

The block below is the unedited output of `scripts/audit_academic_terms.sh`.
Match excerpts are quoted verbatim for accurate reporting; their presence here is
the detector's record, not new project content.

```text
===== academic-identity =====
docs/sustainability.md	137	references are informational here and are deferred to the final memoria	academic-identity	REEMPLAZAR
docs/PROJECT_TECHNICAL_CLOSURE.md	4	technical implementation scope for the TFG defence cycle.	academic-identity	REEMPLAZAR
docs/PROJECT_TECHNICAL_CLOSURE.md	129	infrastructure work is now exceeded by the marginal value of memoria	academic-identity	REEMPLAZAR
docs/PROJECT_TECHNICAL_CLOSURE.md	130	redaction for the TFG defence cycle.	academic-identity	REEMPLAZAR
docs/PROJECT_TECHNICAL_CLOSURE.md	135	post-defence work outside the TFG scope.	academic-identity	REEMPLAZAR
src/puma/cli.py	418	# ── Sprint 7 — CLI completeness (Anexo F § A.2) ──────────────	academic-identity	REEMPLAZAR
src/puma/cli.py	434	    """List runs registered in the database with their headline metrics (Anexo F § A.2.5)."""	academic-identity	REEMPLAZAR
src/puma/cli.py	546	    """List models effectively present in the Ollama volume (Anexo F § A.2.6)."""	academic-identity	REEMPLAZAR
src/puma/cli.py	620	    """Prepare canonical datasets (jira_balanced_200, tawos, prioritization) — Anexo F § A.2.1.	academic-identity	REEMPLAZAR
src/puma/cli.py	688	    """Wilcoxon signed-rank pairwise comparison of two runs (Anexo F § A.2.2)."""	academic-identity	REEMPLAZAR
src/puma/cli.py	816	    """Bias analysis from perturbed runs already in DB (Anexo F § A.2.3)."""	academic-identity	REEMPLAZAR
src/puma/cli.py	976	    """Generate consolidated plots from runs in the DB (Anexo F § A.2.4)."""	academic-identity	REEMPLAZAR
CHANGELOG.md	28	  `verify-hash`, `validate` (Anexo F F.16.5-F.16.8; implemented in S11'.2).	academic-identity	REEMPLAZAR
CHANGELOG.md	75	Discovery-before-write captures recorded during execution (see Anexo G of the	academic-identity	REEMPLAZAR
CHANGELOG.md	76	academic memoria for full enumeration). The post-publish HEAD verification	academic-identity	REEMPLAZAR
CHANGELOG.md	581	Sprint 7 (CLI completeness for Anexo F):	academic-identity	REEMPLAZAR
CHANGELOG.md	584	  Resolves the gap between the academic Anexo F and the actual	academic-identity	REEMPLAZAR
CHANGELOG.md	587	- Six new CLI commands implementing Section A.2 of the Anexo F:	academic-identity	REEMPLAZAR
CHANGELOG.md	626	- **Anexo F implementation gap resolved.** Section A (implemented) and	academic-identity	REEMPLAZAR
docs/anexo_F_cli_reference.md	1	# Anexo F — Catálogo de comandos de la plataforma PUMA (referencia técnica)	academic-identity	REEMPLAZAR
docs/anexo_F_cli_reference.md	13	versión completa del Anexo F (con extensiones propuestas detalladas)	academic-identity	REEMPLAZAR
docs/anexo_F_cli_reference.md	14	está disponible en la memoria del TFG.	academic-identity	REEMPLAZAR
docs/anexo_F_cli_reference.md	183	completa del Anexo F entregada con la memoria del TFG.	academic-identity	REEMPLAZAR
docs/sprints/Sprint-11p-Closure.md	176	- **The academic memoria's Anexos (UOC `.docx`) are maintained separately** from in-repo developer d	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	9	This release consolidates Sprint 7 (CLI completeness for Anexo F) onto	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	11	Anexo F catalog and the actual repository state by adding the six	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	12	high-value commands from section A.2 of Anexo F, together with a new	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	18	### Anexo F gap resolved	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	35	### Six new CLI commands (Anexo F § A.2)	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	37	| Anexo F | Command | Style |	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	46	**Why two commands are NEW analyses and not wrappers:** Anexo F § A.2.2	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	79	  do not yet exist. This matches the Anexo F spec without inventing	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	83	  comparison is documented in Anexo F but not yet in the repo; the	academic-identity	REEMPLAZAR
docs/RELEASES/v2.4.0.md	93	- **Section B of Anexo F** is *documented design space*, not technical	academic-identity	REEMPLAZAR
docs/RELEASES/v3.1.0.md	18	  `pull`, `verify-hash`, `validate` (Anexo F F.16.5–F.16.8). The GitHub	academic-identity	REEMPLAZAR
docs/RELEASES/v3.1.0.md	73	- Anexo G of the academic memoria — discovery-before-write episodes recorded	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	189	| 10 | 415 | `@app.command(name="list-runs")` | `list_runs`         | List runs registered in the da	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	190	| 11 | 536 | `@app.command(name="list-ollama-models")` | `list_ollama_models` | List models effectiv	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	191	| 12 | 600 | `@app.command(name="prepare-datasets")` | `prepare_datasets` | Prepare canonical datase	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	192	| 13 | 669 | `@app.command(name="wilcoxon")` | `wilcoxon_cmd`      | Wilcoxon signed-rank pairwise c	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	193	| 14 | 795 | `@app.command(name="bias-analysis")` | `bias_analysis_cmd` | Bias analysis from perturb	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	194	| 15 | 958 | `@app.command(name="generate-plots")` | `generate_plots_cmd` | Generate consolidated pl	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	273	| 2.4.0   | 2026-05-13 | Sprint 7 — CLI completeness for Anexo F |	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	284	| v2.4.0.md | "Sprint 7 (CLI completeness for Anexo F) onto the v2.3.0 base. Resolves the long-stand	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	330	> further infrastructure work is now exceeded by the marginal value of memoria redaction	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	331	> for the TFG defence cycle."	academic-identity	REEMPLAZAR
docs/community/00-inventory.md	451	  reviewer of the memoria. (Alternative `tests/unit/community/` would be the first nested	academic-identity	REEMPLAZAR
docs/known_debt.md	62	| D11 | Git history prior to commit `1abd831` contains references to internal operational documents 	academic-identity	REEMPLAZAR
src/puma/community/pull_cli.py	1	"""``puma community pull`` — download PUMA Community submissions (Anexo F.16.6).	academic-identity	REEMPLAZAR
src/puma/community/verify_cli.py	1	"""``puma community verify-hash`` — integrity check for a submission (Anexo F.16.8).	academic-identity	REEMPLAZAR
src/puma/community/validate_cli.py	1	"""``puma community validate`` — validate submission JSON files (Anexo F.16.7).	academic-identity	REEMPLAZAR
src/puma/community/browse_cli.py	1	"""``puma community browse`` — list PUMA Community submissions (Anexo F.16.5).	academic-identity	REEMPLAZAR

===== legacy-naming =====
(no matches)

===== non-existent-method =====
(no matches)

===== forbidden-term-HELM =====
(no matches)

===== forbidden-term-federation =====
CHANGELOG.md	39	  pre-v3.0.0 "federation" terminology; body preserved verbatim as a planning	forbidden-term-federation	DUDOSO
wiki/Publishing-Results.md	4	a public federation hub where users of the PUMA benchmarking tool share their	forbidden-term-federation	DUDOSO
docs/sprints/Sprint-11p-Closure.md	64	| Federation refs in code | 0 (P4) |	forbidden-term-federation	DUDOSO
docs/RELEASES/v3.1.0.md	40	- Schema v1.0.0 unchanged (P3); zero federation references in code (P4).	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	3	> working name "Federation". The feature was renamed to "PUMA	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	4	> Community" (and "federated" → "community-published") in v3.0.0;	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	248	natural field a federation client would need to read (already populated by the runner).	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	296	  untracked simply because nothing was ever staged from it. **Federation tooling that writes	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	298	- `data/puma.db` ✗ — **not explicitly ignored either.** Same situation. **Federation tooling	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	334	federation v1 fits this profile if introduced under a strict opt-in mechanism that does not	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	359	**Proposed home for ADR-005 (federation):**	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	365	seed=42, temperature=0.0"). The federation v1 is by design **non-normative for the	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	377	Role: **Project constitution.** Verbatim principles the federation MUST NOT contradict:	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	389	→ The federation must be **opt-in** (HITL), produce its own JSON-schema-validated payloads	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	400	→ The federation must respect: (a) **identical-results contract** — no side-effect of	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	414	→ Federation CI work should land **as an additional job** in `lint-and-test.yml`, not as a	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	450	  preserves the "purpose-shaped" convention and keeps federation tests collocated for the	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	452	  subfolder ever in `tests/unit/` and would split federation tests across multiple	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	504	# Community federation v1 (opt-in publication of results)	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	513	and the federation prompt MUST NOT introduce a third divergence).	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	522	| `.gitignore`                | explicit ignores for `data/cache/`, `data/puma.db`, and any new fede	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	523	| `docs/community/` (this folder) | future federation docs — guide, ADR-005 link, payload schema, 	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	524	| `CHANGELOG.md`              | `Unreleased` section will accrue federation entries. |	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	525	| `docs/RELEASES/v2.8.0.md` (future) | release notes for the federation feature. |	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	533	   and the federation MUST respect (each is enforced by tests or by the closure document):	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	536	     `generate-plots`). The federation's new commands must not name-collide with these.	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	540	     default of F1=0.5867 must stay backward-compatible. The federation must not call	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	544	     `unified_memory_gb`; `CodeCarbon` has a platform-aware tracking mode. A federation	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	551	     `test_qwen3_entries_target_gpu_high_only`). The federation MUST NOT label	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	553	     the catalog (13 registry probes, all 404) — federation tooling must refuse to publish	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	557	   `puma/` at the repo root. Imports inside the federation code must use	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	573	   subfolders** other than `__pycache__`. The federation introduces concerns spanning CLI,	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	578	   federation tests run only on the GitHub CI workflow (which itself currently runs only	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	581	5. **Constitution + architecture set hard constraints the federation must NOT contradict:**	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	585	     the federation must NOT introduce any non-determinism on the inference path, must	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	590	   - **CodeCarbon mandatory**: federation tooling must not gate the codecarbon hook on	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	592	   - **JSON Schema for all outputs**: federation payloads must be JSON-schema-validated	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	597	   benchmark per the constitution; the federation is opt-in non-normative project	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	604	   to reconcile them. The federation payload's `puma_version` field MUST derive from the	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	607	   pre-existing inconsistency the federation should not try to fix in v1 — flag for a	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	612	   `pyproject.toml.dependencies`. The federation must add `jsonschema`, `PyGithub`,	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	617	   simply untracked. Any federation cache layer that writes new files under `data/` risks	forbidden-term-federation	DUDOSO
docs/community/00-inventory.md	618	   accidental staging. The first prompt that introduces a federation cache must add	forbidden-term-federation	DUDOSO

===== citation-non-registered =====
CHANGELOG.md	833	    Caliskan et al. (2017) and Bolukbasi et al. (2016). 10 TDD tests.	citation-non-registered	DUDOSO
CHANGELOG.md	887	  following Caliskan et al. and Bolukbasi et al.). Key empirical	citation-non-registered	DUDOSO
docs/RELEASES/v2.2.0.md	70	  Methodology per Caliskan et al. (2017) and Bolukbasi et al. (2016).	citation-non-registered	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	83	  - Fairness evaluation under perturbations (Caliskan et al. 2017,	citation-non-registered	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	84	    Bolukbasi et al. 2016, Tatman 2017)	citation-non-registered	DUDOSO
docs/metrics_reference.md	201	- CodeCarbon: Lacoste et al. (2019), *Quantifying the Carbon Emissions of Machine Learning*	citation-non-registered	DUDOSO
docs/results/bias_evaluation.md	16	  content does not require them (Caliskan et al. 2017; Bolukbasi	citation-non-registered	DUDOSO

===== sprint-internal-language =====
CHANGELOG.md	21	Sprint 11' — Post-v3.0.0 reconciliation, community CLI completion, wiki +	sprint-internal-language	DUDOSO
CHANGELOG.md	28	  `verify-hash`, `validate` (Anexo F F.16.5-F.16.8; implemented in S11'.2).	sprint-internal-language	DUDOSO
CHANGELOG.md	50	- `docs/known_debt.md`: documented deuda técnica D23 — Verifier Space hash	sprint-internal-language	DUDOSO
CHANGELOG.md	54	  reconstructed in S11'.1). [#15]	sprint-internal-language	DUDOSO
CHANGELOG.md	72	  mismatch (D23) deferred.	sprint-internal-language	DUDOSO
CHANGELOG.md	77	added during S11'.6 caught an upstream-CLI false-success at runtime,	sprint-internal-language	DUDOSO
CHANGELOG.md	137	Sprint 10 (catalog expansion — empirical-first, real Ollama tags	sprint-internal-language	DUDOSO
CHANGELOG.md	221	  **PASSING** unchanged (P6 enforcement from Sprint 9 honored).	sprint-internal-language	DUDOSO
CHANGELOG.md	264	  exclusion from `gpu-entry` (established in Sprint 9 for Apple	sprint-internal-language	DUDOSO
CHANGELOG.md	277	Sprint 9 (Apple Silicon M3/M4/M5 detection + native runtime mode;	sprint-internal-language	DUDOSO
CHANGELOG.md	457	Sprint 8 (hardening — six post-v2.4.0 inconsistencies I5–I10 resolved;	sprint-internal-language	DUDOSO
CHANGELOG.md	581	Sprint 7 (CLI completeness for Anexo F):	sprint-internal-language	DUDOSO
CHANGELOG.md	595	    Sprint 3; the existing `scripts/wilcoxon_topmodels.py` keeps its	sprint-internal-language	DUDOSO
CHANGELOG.md	648	Sprint 6 (dashboard polish, Phase C close):	sprint-internal-language	DUDOSO
CHANGELOG.md	681	Sprint 6:	sprint-internal-language	DUDOSO
CHANGELOG.md	711	Sprint 6:	sprint-internal-language	DUDOSO
CHANGELOG.md	747	- ECE (Expected Calibration Error) end-to-end pipeline (Sprint 3,	sprint-internal-language	DUDOSO
CHANGELOG.md	773	- Multi-seed baseline validation (Sprint 3):	sprint-internal-language	DUDOSO
CHANGELOG.md	783	- Wilcoxon signed-rank pairwise model comparison (Sprint 3):	sprint-internal-language	DUDOSO
CHANGELOG.md	802	- Dashboard core (Sprint 4, Phase C):	sprint-internal-language	DUDOSO
CHANGELOG.md	816	    vs CO₂ Pareto consuming the emissions table from Sprint 2 D15),	sprint-internal-language	DUDOSO
CHANGELOG.md	820	    by Sprint 5).	sprint-internal-language	DUDOSO
CHANGELOG.md	827	- Empirical bias evaluation suite (Sprint 5, Gate D criterion 4):	sprint-internal-language	DUDOSO
CHANGELOG.md	876	- D22 (synthetic `triage_jira` dataset persists only `instance_id`	sprint-internal-language	DUDOSO
CHANGELOG.md	879	  not evaluation metrics. Surfaced during Sprint 4 S4.3.0 when	sprint-internal-language	DUDOSO
CHANGELOG.md	906	  Sprint 2 surfaced in the Sustainability Frontier view. Polish	sprint-internal-language	DUDOSO
CHANGELOG.md	908	  to a future Sprint 6.	sprint-internal-language	DUDOSO
CHANGELOG.md	911	- **Methodological note:** four independent findings (D15, D18, D21,	sprint-internal-language	DUDOSO
CHANGELOG.md	912	  D22) share a meta-pattern documented in `docs/known_debt.md`:	sprint-internal-language	DUDOSO
CHANGELOG.md	957	  Closes debt D21 (folded into this sprint as task S1.5.bis).	sprint-internal-language	DUDOSO
CHANGELOG.md	958	  End-to-end smoke (post D17 + D21): a 20-instance `deepseek-r1:7b` run	sprint-internal-language	DUDOSO
CHANGELOG.md	982	  section was added in Sprint 2 with full diagnostic write-ups for	sprint-internal-language	DUDOSO
CHANGELOG.md	1098	  D17, D18, D18-cleanup, D21). See `docs/known_debt.md` for individual	sprint-internal-language	DUDOSO
CHANGELOG.md	1099	  entries; Sprint 1 closures remain inline with strikethrough	sprint-internal-language	DUDOSO
CHANGELOG.md	1100	  notation in the open-debt tables, and the involved Sprint 2	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	17	### Statistical analysis pipeline (Sprint 3)	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	36	### Dashboard core (Sprint 4)	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	43	  the emissions table from Sprint 2 D15), Instance Drill-down	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	46	  (made functional by Sprint 5).	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	58	### Bias evaluation (Sprint 5) — empirical findings	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	65	nothing. Sprint 5 therefore evaluates bias via **signal injection**	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	103	- **Sprint 3** confirmed empirically the deterministic-reproducibility	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	106	- **Sprint 4** dashboard integration exposed **D22**: the synthetic	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	110	  D21).	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	111	- **Sprint 5** confirmed **D3** empirically: `puma validate-baseline`	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	121	- **New entry**: D22 (Low) — `instances.input_text` empty on	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	132	- `input_text` not persisted in `triage_jira` instances (D22, Low —	sprint-internal-language	DUDOSO
docs/RELEASES/v2.2.0.md	140	  future Sprint 6.	sprint-internal-language	DUDOSO
src/puma/cli.py	418	# ── Sprint 7 — CLI completeness (Anexo F § A.2) ──────────────	sprint-internal-language	DUDOSO
docs/RELEASES/v2.5.0.md	9	This release consolidates Sprint 8 (hardening) onto the v2.4.0 base.	sprint-internal-language	DUDOSO
docs/RELEASES/v2.5.0.md	106	- **gemma4 stays excluded.** The original Sprint 8 plan asked for	sprint-internal-language	DUDOSO
docs/RELEASES/v2.5.0.md	143	- `input_text` not persisted in `triage_jira` instances (D22,	sprint-internal-language	DUDOSO
docs/RELEASES/v2.4.0.md	9	This release consolidates Sprint 7 (CLI completeness for Anexo F) onto	sprint-internal-language	DUDOSO
docs/RELEASES/v2.4.0.md	104	- `input_text` not persisted in `triage_jira` instances (D22, Low).	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	1	# PUMA v3.1.0 — Sprint 11' Post-v3.0.0 Reconciliation	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	9	Sprint 11' is a post-v3.0.0 hardening Sprint: it reconciles the v3.0.0	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	21	  D23-aware on `--remote`.	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	28	- **D23 deuda técnica documented** — the Verifier (2-field JSONL) and client	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	44	- **D23**: `puma community verify-hash --remote` returns `mismatch` by	sprint-internal-language	DUDOSO
docs/RELEASES/v3.1.0.md	50	- **Kaggle mirror activation (S11'.6)**: the `mirror-kaggle.yml` workflow is	sprint-internal-language	DUDOSO
docs/RELEASES/v2.1.0.md	15	the release validation cycle (D15, D17, D18, D21) are resolved with	sprint-internal-language	DUDOSO
docs/RELEASES/v2.1.0.md	59	- Resolved: D1, D6, D10, D13, D15, D17, D18, D18-cleanup, D21	sprint-internal-language	DUDOSO
docs/RELEASES/v2.1.0.md	64	  technical debt" section for the involved Sprint 2 write-ups	sprint-internal-language	DUDOSO
docs/RELEASES/v2.1.0.md	69	- 3 new findings from Phase B / Sprint 1 / Sprint 2 surfaced and	sprint-internal-language	DUDOSO
docs/RELEASES/v2.1.0.md	73	  - **D21** — unit-test vs end-to-end discrepancy (catalog	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	12	  v2.4.0 — Sprint 7 CLI completeness	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	13	  v2.5.0 — Sprint 8 hardening (I5-I10)	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	14	  v2.6.0 — Sprint 9 Apple Silicon M3/M4/M5 detection + native mode	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	15	  v2.7.0 — Sprint 10 catalog expansion (Qwen3 dense + MoE) +	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	32	     Source: D18/F8 (Sprint 5 empirical evidence)	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	33	     Test added: Sprint 5	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	37	     Test added: Sprint 9	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	45	     Tests added: Sprint 10	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	119	The originally-planned multi-Sprint scope (Sprint 8 hardening +	sprint-internal-language	DUDOSO
docs/PROJECT_TECHNICAL_CLOSURE.md	120	Sprint 9 Apple Silicon + Sprint 10 catalog expansion) is complete.	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	1	# Sprint 11' — Community CLI Smoke Proof	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	4	`verify-hash`, `validate`) implemented in Sprint 11'.2. Performed during	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	5	S11'.10.b as part of the Sprint closure.	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	7	**Context.** The Sprint 11'.10.a E2E demo attempt surfaced three integration	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	8	gaps (D24/D25/D26 in `docs/known_debt.md`) that prevent producing a real	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-CLI-Smoke.md	120	The CLI is fit for purpose once the upstream gaps D24/D25/D26 are resolved and	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	9	This release consolidates Sprint 10 (catalog expansion) onto the	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	78	The original Sprint 10 plan proposed ~12 new YAML fields (`family`,	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	94	Sprint 9 for Apple Silicon entries) is reaffirmed for the new	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	100	| `test_gemma4_family_excluded_from_gpu_entry` | PASSED (preserved) | D18/F8 (Sprint 2) |	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	101	| `test_gemma4_family_not_compatible_with_any_apple_silicon` | PASSED (preserved) | P6 extension to 	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	102	| `test_qwen3_entries_excluded_from_gpu_entry` | PASSED (new) | P10/P11 (Sprint 10) |	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	172	- **No closure of pre-existing debt** — Sprint 10 is	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	188	  `empirical_validation: pending` (Sprint 9 forward-work).	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	239	Sprint 10 closes the originally-planned multi-Sprint sequence	sprint-internal-language	DUDOSO
docs/RELEASES/v2.7.0.md	240	(Sprint 8 hardening → Sprint 9 Apple Silicon → Sprint 10 catalog	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	1	# PUMA Sprint 11' — Closure Report	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	7	| Sprint name | Sprint 11' (prime) — Post-v3.0.0 Reconciliation |	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	8	| Supersedes | Original "Sprint 11 — Post-v2.7.0 Consistency Hardening" (retired; see episode 1) |	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	18	| v3.0.0 artifact reconciliation (version, CHANGELOG, RELEASES, INDEX) | **Met** — S11'.1 + S11'.1	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	19	| Community CLI (`browse`/`pull`/`verify-hash`/`validate`) | **Met** — S11'.2, 34 tests, coverage 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	20	| HF dataset namespace canonicalization | **Met** — S11'.3 (companion PR #2; 7 HF refs, 6 Kaggle p	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	21	| Wiki-sync workflow repair | **Met** — S11'.4 (puma commit + companion PR #3); both `/wiki` rende	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	22	| Verifier Space schema alignment | **Met** — S11'.5 (HF Space @ `d8a4ffd`, RUNNING) |	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	23	| Kaggle mirror activation | **Deferred** — S11'.6; workflow fully hardened (companion PR #4), blo	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	24	| Docs drift cleanup | **Met** — S11'.7, scoped to active product surface |	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	25	| Regression + release | **Met** — S11'.8 (PR #15) + E.nov (v3.1.0 tag, release, production deploy	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	27	Out-of-scope discoveries surfaced and recorded rather than actioned: D23 (Verifier/client hash-algor	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	33	| S11'.0 | tag + branch | safety tag `sprint11p-pre-hardening`, branch `feature/sprint-11p-reconcili	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	34	| S11'.1 | 5 (`25b5676`,`abf89fd`,`bd7ad7f`,`11b76e4`,`3a33d45`) | pyproject 3.0.0; CHANGELOG fold u	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	35	| S11'.1.1 | 1 (`d6c018f`) | dashboard view count 9 → 8 (off-by-one; `_base.py` is a helper) | ✅	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	36	| S11'.2 | 4 (`6c4fee2`,`7d5eb04`,`57cc749`,`44c9783`) | `puma community` subgroup (4 verbs) + `_com	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	37	| S11'.3 | companion PR #2 | 7 HF refs `pumacp/` → `pumaproject/` (5 files); 6 Kaggle refs preserv	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	38	| S11'.4 | 1 (`e026487`) + companion PR #3 | `wiki-sync.yml` `contents: read` → `write`; both wiki	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	39	| S11'.5 | HF Space @ `d8a4ffd` | strip `sha256:` prefix → schema `^[a-f0-9]{64}$`; Space RUNNING 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	40	| S11'.6 | companion PR #4 | Kaggle workflow hardened (`-r zip`, robust create/version, CC-BY-4.0, 4	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	41	| S11'.7 | 1 (`b340299`) | test docstring 7 → 8 views; historical-note header on `00-inventory.md`	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	42	| S11'.8 | — | full regression (597+7 tests, baselines, coverage); consolidator PR #15 | ✅ |	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	72	1. **v3.0.0 baseline discovery** (S11'.0 audit). The repo was already at v3.0.0 (released 2026-05-20	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	73	2. **D19 → D23 renumber** (S11'.2). "D19" was already used by a closed fairness-scaffolding debt i	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	74	3. **`raw_predictions_url` schema reality / P13** (S11'.2). The field **is** optional in schema v1.0	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	75	4. **Two `sha256:` occurrences in Verifier `app.py`** (S11'.5). The plan assumed one (line 26, funct	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	79	5. **Historical-vs-active distinction in grep-empty criteria** (S11'.7). A literal "grep `7 views` e	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	83	6. **Kaggle CLI exit-0-on-error** (S11'.6 attempts 1-2). `kaggle datasets create` returns exit 0 eve	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	84	7. **`--dir-mode` required for folders** (S11'.6 attempt 1). Without `-r zip`/`tar`, the CLI silentl	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	85	8. **"MIT" is not a Kaggle license slug** (S11'.6 attempt 2). The repo is MIT-licensed but Kaggle's 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	86	9. **Title length cap is 50, not 80** (S11'.6 attempt 4). The audit assumed 80 chars; the CLI error 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	87	10. **Title collision is slug-keyed** (S11'.6 attempt 5). The "title already in use" error fired for	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	98	15. **`-X theirs` cannot reproduce a restructured file** (E.nov Step 11, iteration 3). A 3-way merge	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	100	**Total: 15 substantive P1 captures + 1 benign expectation correction (#14).** Episodes 1-15 are enu	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	102	## S11'.10.a discovery: end-to-end integration gaps (episode 16)	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	104	The Sprint 11'.10 attempt to perform a live publication demo (canonical runner → `share-results` 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	106	- **D24** (`docs/known_debt.md`): canonical specs do not declare `profile_required`, so `Run.profile	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	107	- **D25** (`docs/known_debt.md`): canonical specs disable codecarbon, so no emissions record is prod	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	108	- **D26** (`docs/known_debt.md`): `src/puma/orchestrator/runner.py:526` never populates `ProfileSnap	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	110	D24 and D25 are spec-level (configuration); both were bridged locally during S11'.10.a via an untrac	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	120	Sprint 11'.10 was re-scoped from "live publication demo" to "documented integration-gap analysis + C	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	124	### D23 — Verifier algorithm/schema mismatch	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	127	- **Workaround:** `puma community verify-hash --remote` detects the systematic mismatch and emits a 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	130	### S11'.6 — Kaggle mirror activation	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	139	Node 20 deprecates June 2026; affects `wiki-sync.yml`, `mirror-*.yml`, `lint-and-test.yml`. Hygiene 	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	153	- #15 — Sprint 11' main consolidation → develop (MERGED)	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	155	- #17 — Sprint 11' production deploy → main, rebase-and-merge (MERGED)	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	162	- `v3.1.0` → `1792be7` (Sprint 11' release, immutable)	sprint-internal-language	DUDOSO
docs/sprints/Sprint-11p-Closure.md	175	- **A retry cap (3 by default) plus explicit authorization to exceed it when new information justifi	sprint-internal-language	DUDOSO
docs/RELEASES/v3.0.0.md	35	This file is added as part of the Sprint 11' reconciliation work	sprint-internal-language	DUDOSO
docs/RELEASES/v2.6.0.md	9	This release consolidates Sprint 9 (Apple Silicon M3/M4/M5 support)	sprint-internal-language	DUDOSO
docs/RELEASES/v2.6.0.md	173	- **No closure of pre-existing debt** — Sprint 9 is forward-looking	sprint-internal-language	DUDOSO
docs/RELEASES/v2.6.0.md	189	- `input_text` not persisted in `triage_jira` instances (D22, Low).	sprint-internal-language	DUDOSO
docs/RELEASES/v2.6.0.md	223	Sprint 10 (planned, awaiting explicit user confirmation per P8):	sprint-internal-language	DUDOSO
docs/RELEASES/v2.6.0.md	230	is not tied to Sprint 10.	sprint-internal-language	DUDOSO
src/puma/orchestrator/runner.py	527	    """Resolve the profile id to persist on ``Run.profile`` (D24).	sprint-internal-language	DUDOSO
src/puma/orchestrator/runner.py	557	    """Collect flat host-system facts for ``ProfileSnapshot.extra`` (D26).	sprint-internal-language	DUDOSO
src/puma/orchestrator/runner.py	606	    """Resolve the installed PUMA distribution version dynamically (D26).	sprint-internal-language	DUDOSO
docs/results/wilcoxon_demo.md	1	# Wilcoxon Signed-Rank Pairwise Model Comparison (Sprint 3)	sprint-internal-language	DUDOSO
docs/results/wilcoxon_demo.md	29	`docs/results/phase_b_analysis.md`. Sprint 3 therefore demonstrates	sprint-internal-language	DUDOSO
docs/results/wilcoxon_demo.md	68	  resolve this either way. The N=50 cohort chosen for Sprint 3 is a	sprint-internal-language	DUDOSO
docs/RELEASES/v2.3.0.md	9	This release consolidates Sprint 6 (dashboard polish + structural	sprint-internal-language	DUDOSO
docs/RELEASES/v2.3.0.md	16	### Dashboard production-quality (Sprint 6)	sprint-internal-language	DUDOSO
docs/RELEASES/v2.3.0.md	70	Sprint 6 surfaced one additional finding consistent with the	sprint-internal-language	DUDOSO
docs/RELEASES/v2.3.0.md	85	D21, D22, and this CSS scope issue); the fifth is retired in the	sprint-internal-language	DUDOSO
docs/RELEASES/v2.3.0.md	115	- `input_text` not persisted in `triage_jira` instances (D22, Low —	sprint-internal-language	DUDOSO
docs/known_debt.md	39	| ~~D17~~ | ~~`deepseek-r1` parse_failure_rate ≈ 0.8 with `triage_jira` scenario.~~ — **CLOSED i	sprint-internal-language	DUDOSO
docs/known_debt.md	40	| ~~D21~~ | ~~Runtime client `timeout_s = 120.0` is hard-coded in `puma.runtime.client` and not cons	sprint-internal-language	DUDOSO
docs/known_debt.md	50	| ~~D6~~ | ~~Timestamp columns in ORM models use Python-side defaults, not database-side `server_def	sprint-internal-language	DUDOSO
docs/known_debt.md	51	| ~~D1~~ | ~~`--validate-baseline` CLI flag declared in earlier specifications but not implemented~~	sprint-internal-language	DUDOSO
docs/known_debt.md	53	| D20 | Laptop thermal characteristics may bias `duration_s` and energy measurements during sustaine	sprint-internal-language	DUDOSO
docs/known_debt.md	61	| ~~D10~~ | ~~`pre-commit` not installed as a local git hook (incompatibility with cross-container d	sprint-internal-language	DUDOSO
docs/known_debt.md	63	| ~~D13~~ | ~~`scripts/download_datasets.py` is mis-named: it processes a local SQL zip dump, not do	sprint-internal-language	DUDOSO
docs/known_debt.md	65	| D22 | Synthetic `triage_jira` dataset persists only `instance_id` and `gold_label`; original ticke	sprint-internal-language	DUDOSO
docs/known_debt.md	66	| ~~D18-cleanup~~ | ~~`pyproject.toml` has `version = "2.0.0-dev"` which causes the published wheel 	sprint-internal-language	DUDOSO
docs/known_debt.md	68	### D23 — Verifier Space algorithmic mismatch with the client (since v3.0.0)	sprint-internal-language	DUDOSO
docs/known_debt.md	83	**Schema note (correction to an earlier Sprint 11' assumption).**	sprint-internal-language	DUDOSO
docs/known_debt.md	93	  `verified-local-only (D23 warned)` (exit 0).	sprint-internal-language	DUDOSO
docs/known_debt.md	103	(b) Strip the `sha256:` prefix on the Verifier side (the S11'.5 minimal repair)	sprint-internal-language	DUDOSO
docs/known_debt.md	107	consumes; neither is attempted in Sprint 11'.	sprint-internal-language	DUDOSO
docs/known_debt.md	109	**Deferral rationale (S12.2 empirical confirmation, 2026-05-25).** A controlled	sprint-internal-language	DUDOSO
docs/known_debt.md	110	discovery session in Sprint 12 S12.2 attempted the client-side alignment and	sprint-internal-language	DUDOSO
docs/known_debt.md	111	HALTED before any edit, confirming D23 is schema-decision work, not a	sprint-internal-language	DUDOSO
docs/known_debt.md	113	1. The Sprint 12 plan assumed a `src/puma/community/hashing.py` with a	sprint-internal-language	DUDOSO
docs/known_debt.md	135	**Three open decisions D23 closure requires.** (a) Which side adapts — client	sprint-internal-language	DUDOSO
docs/known_debt.md	140	after v4.0.0.** Cross-references: S12.2 HALT report; D27 (the exporter, RESOLVED	sprint-internal-language	DUDOSO
docs/known_debt.md	141	in S12.2, which productizes the *existing* 4-field canonical and is decoupled	sprint-internal-language	DUDOSO
docs/known_debt.md	145	### D24 — Canonical baseline specs missing `profile_required` (since v1.0.0)	sprint-internal-language	DUDOSO
docs/known_debt.md	147	**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25	sprint-internal-language	DUDOSO
docs/known_debt.md	148	(Sprint 11' E2E demo attempt, S11'.10.a).	sprint-internal-language	DUDOSO
docs/known_debt.md	160	**Impact.** All canonical runs in the Sprint 11' DB at v3.1.0 release time	sprint-internal-language	DUDOSO
docs/known_debt.md	163	**Detection.** S11'.10.a attempted to produce a real demo submission and was	sprint-internal-language	DUDOSO
docs/known_debt.md	177	**Resolution (Sprint 12 S12.1).** Implemented approach (b): `runner.py` now	sprint-internal-language	DUDOSO
docs/known_debt.md	184	### D25 — Canonical baseline specs disable codecarbon (since v1.0.0)	sprint-internal-language	DUDOSO
docs/known_debt.md	186	**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25	sprint-internal-language	DUDOSO
docs/known_debt.md	187	(Sprint 11' E2E demo attempt, S11'.10.a).	sprint-internal-language	DUDOSO
docs/known_debt.md	189	flow as D24).	sprint-internal-language	DUDOSO
docs/known_debt.md	195	Therefore, even with D24 bridged (`Run.profile` set), the absence of an	sprint-internal-language	DUDOSO
docs/known_debt.md	197	second precondition hit during S11'.10.a, after D24 was bridged.	sprint-internal-language	DUDOSO
docs/known_debt.md	199	**Impact.** Same scope as D24: canonical runs are not publishable directly.	sprint-internal-language	DUDOSO
docs/known_debt.md	206	**Resolution (Sprint 12 S12.1).** Flipped `sustainability.codecarbon` from	sprint-internal-language	DUDOSO
docs/known_debt.md	213	### D26 — `runner.py` never populates `ProfileSnapshot.extra` (since v1.0.0)	sprint-internal-language	DUDOSO
docs/known_debt.md	215	**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.1). Discovered: 2026-05-25	sprint-internal-language	DUDOSO
docs/known_debt.md	216	(Sprint 11' E2E demo attempt, S11'.10.a).	sprint-internal-language	DUDOSO
docs/known_debt.md	218	feeding `share-results`. Unlike D24 and D25, this is **not** spec-fixable; it	sprint-internal-language	DUDOSO
docs/known_debt.md	226	D24 + D25 bridged via spec, the runner output still fails the builder's snapshot	sprint-internal-language	DUDOSO
docs/known_debt.md	230	**Why this gap remained latent until S11'.10.a.** The `share-results` and	sprint-internal-language	DUDOSO
docs/known_debt.md	238	**Impact.** Combined with D24 + D25, no canonical run can be turned into a	sprint-internal-language	DUDOSO
docs/known_debt.md	240	Sprint 11'.2 (`validate`, `verify-hash`, `browse`, `pull`) are architecturally	sprint-internal-language	DUDOSO
docs/known_debt.md	257	**Resolution (Sprint 12 S12.1).** `_add_profile_snapshot` now populates	sprint-internal-language	DUDOSO
docs/known_debt.md	266	the regression test that would have caught D24/D25/D26 immediately.	sprint-internal-language	DUDOSO
docs/known_debt.md	272	for academic traceability. Sprint 1 closures remain inline in the	sprint-internal-language	DUDOSO
docs/known_debt.md	274	following entries document the more involved resolutions from Sprint 2	sprint-internal-language	DUDOSO
docs/known_debt.md	278	### D27 — Predictions JSONL exporter missing in `share-results` (since v3.0.0)	sprint-internal-language	DUDOSO
docs/known_debt.md	280	**Status:** RESOLVED in v4.0.0 (Sprint 12 S12.2).	sprint-internal-language	DUDOSO
docs/known_debt.md	281	**Discovered:** Sprint 12 S12.1 (2026-05-25), while implementing the E2E	sprint-internal-language	DUDOSO
docs/known_debt.md	284	`validate --strict` consume had no producer. The S12.1 E2E test worked around	sprint-internal-language	DUDOSO
docs/known_debt.md	300	semantics, the schema, or the Verifier. It is deliberately decoupled from D23	sprint-internal-language	DUDOSO
docs/known_debt.md	303	D23's eventual schema decision selects a different canonical format, the	sprint-internal-language	DUDOSO
docs/known_debt.md	306	publication demo (S12.12) alongside the D23 resolution.	sprint-internal-language	DUDOSO
docs/known_debt.md	310	**Status:** CLOSED in Sprint 2 (2026-05-10).	sprint-internal-language	DUDOSO
docs/known_debt.md	385	**References.** PR `feature/sprint-2-critical-debt`, Sprint 2 task	sprint-internal-language	DUDOSO
docs/known_debt.md	390	**Status:** CLOSED in Sprint 2 (2026-05-10) via documented exclusion.	sprint-internal-language	DUDOSO
docs/known_debt.md	448	**References.** PR `feature/sprint-2-critical-debt`, Sprint 2 task	sprint-internal-language	DUDOSO
docs/known_debt.md	455	- Closed in Sprint 1: **7** (D1, D6, D10, D13, D17, D18-cleanup, D21)	sprint-internal-language	DUDOSO
docs/known_debt.md	456	  - D21 was detected mid-sprint during D17 smoke verification and folded	sprint-internal-language	DUDOSO
docs/known_debt.md	457	    into Sprint 1 as task S1.5.bis; see CHANGELOG for the full sequence.	sprint-internal-language	DUDOSO
docs/known_debt.md	458	- Closed in Sprint 2: **2** (D15 measurement-and-infrastructure fix;	sprint-internal-language	DUDOSO
docs/known_debt.md	463	No critical debt remains after Sprint 2. The repository is in	sprint-internal-language	DUDOSO
docs/anexo_F_cli_reference.md	26	### A.2. Comandos añadidos en v2.4.0 (Sprint 7 — CLI completeness)	sprint-internal-language	DUDOSO
docs/results/phase_b_analysis.md	103	thermal throttling on the laptop reference machine (debt #D20).	sprint-internal-language	DUDOSO
docs/results/phase_b_analysis.md	234	> Sprint 2 (post-fix smoke confirms `gpu_energy > 0` in the	sprint-internal-language	DUDOSO
docs/results/phase_b_analysis.md	342	under ideal conditions. This is tracked as debt #D20.	sprint-internal-language	DUDOSO
docs/results/phase_b_analysis.md	430	  measurement (debt #D20). The `mistral:7b` figures should be read	sprint-internal-language	DUDOSO
docs/results/phase_b_analysis.md	455	- **Run sweeps in chunks with cooldown intervals** (debt #D20) to	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	14	``--remote`` (deuda técnica D23): the Verifier Space	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	20	present; it is simply uninformative until D23 is resolved (see	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	116	    remote: bool = typer.Option(False, "--remote", help="Also query the Verifier Space (D23)."),	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	148	    # ── --remote (D23-aware) ──────────────────────	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	155	            "deuda técnica D23 (see docs/known_debt.md). Local verification is canonical."	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	182	    # local verified but remote disagrees -> the expected D23 outcome.	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	186	        "técnica D23 (the Verifier hashes a different input shape and prefixes 'sha256:'); "	sprint-internal-language	DUDOSO
src/puma/community/verify_cli.py	189	    console.print("[green]verdict: verified-local-only (D23 warned)[/green]")	sprint-internal-language	DUDOSO
src/puma/dashboard/views/sustainability.py	35	            "CodeCarbon emissions are persisted from Sprint 2 onwards (D15)."	sprint-internal-language	DUDOSO
src/puma/dashboard/views/sustainability.py	75	            "Older runs (pre-Sprint 2 D15) did not persist CodeCarbon output."	sprint-internal-language	DUDOSO
src/puma/community/share_cli.py	337	        # D27: emit the canonical predictions JSONL alongside the submission	sprint-internal-language	DUDOSO
docs/results/multi_seed_baseline.md	1	# Multi-seed Baseline Validation (Sprint 3)	sprint-internal-language	DUDOSO
docs/results/multi_seed_baseline.md	98	   Sprint 3 (current warm-state value: 0.5831; canonical reference:	sprint-internal-language	DUDOSO
src/puma/dashboard/views/instance_drilldown.py	117	            "tracked as future work (see `docs/known_debt.md` D22)."	sprint-internal-language	DUDOSO
docs/results/bias_evaluation.md	1	# Bias evaluation — Sprint 5	sprint-internal-language	DUDOSO
docs/results/bias_evaluation.md	9	the model. Sprint 5 therefore evaluates bias via *signal injection*	sprint-internal-language	DUDOSO
src/puma/community/integrity.py	105	    """Write a run's predictions to a canonical JSONL file at ``target`` (D27).	sprint-internal-language	DUDOSO
docs/sustainability.md	36	**Coverage.** Since Sprint 12 (debt item D25), the canonical baseline specs ship	sprint-internal-language	DUDOSO
docs/sustainability.md	50	verified **structurally** in Sprint 12 — each loads, declares no per-profile	sprint-internal-language	DUDOSO
docs/sustainability.md	114	default since Sprint 12. Re-run and validate them with:	sprint-internal-language	DUDOSO
docs/sustainability.md	130	- `docs/sprints/Sprint-12-Closure.md` (when published) for the Sprint 12	sprint-internal-language	DUDOSO
docs/TESTING.md	42	`d5996f1` (Sprint 8 head). 354 tests passing, 7 deselected.	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	270	| 2.7.0   | 2026-05-16 | Sprint 10 — catalog expansion (Qwen3 dense + MoE) + formal Kimi K2.6 excl	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	271	| 2.6.0   | 2026-05-16 | Sprint 9 — Apple Silicon M3/M4/M5 detection + native runtime mode |	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	272	| 2.5.0   | 2026-05-16 | Sprint 8 — hardening (I5-I10) |	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	273	| 2.4.0   | 2026-05-13 | Sprint 7 — CLI completeness for Anexo F |	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	274	| 2.3.0   | 2026-05-13 | Sprint 6 — dashboard polish + structural refactor |	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	283	| v2.3.0.md | "Sprint 6 (dashboard polish + structural refactor) and retrospective documentation wor	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	284	| v2.4.0.md | "Sprint 7 (CLI completeness for Anexo F) onto the v2.3.0 base. Resolves the long-stand	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	285	| v2.5.0.md | "Sprint 8 (hardening) onto the v2.4.0 base. Resolves the six inconsistencies (I5–I10	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	286	| v2.6.0.md | "Sprint 9 (Apple Silicon M3/M4/M5 support) onto the v2.5.0 base. Adds first-class dete	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	287	| v2.7.0.md | "Sprint 10 (catalog expansion) onto the v2.6.0 base. Adds two Alibaba Qwen3 family ent	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	326	> "The originally-planned multi-Sprint scope (Sprint 8 hardening + Sprint 9 Apple Silicon	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	327	> + Sprint 10 catalog expansion) is complete. Every quality gate passes. … Further	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	534	   - **v2.4.0** — Sprint 7 CLI completeness: six Anexo-F-shaped commands already exist	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	537	   - **v2.5.0** — Sprint 8 hardening: the new `--expected-mae` path of	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	542	   - **v2.6.0** — Sprint 9 Apple Silicon detection: nine `apple-silicon-*` profiles in	sprint-internal-language	DUDOSO
docs/community/00-inventory.md	547	   - **v2.7.0** — Sprint 10 catalog expansion: two `qwen3:30b*` entries are catalogued as	sprint-internal-language	DUDOSO
docs/maintenance/baseline-2026-05.md	353	completed  success  Sprint 10 (v2.7.0): Qwen3 catalog expansion (gpu-high, pending...  Lint and Test	sprint-internal-language	DUDOSO

===== SUMMARY =====
367 matches across 4 categories, files scanned: 142
```
