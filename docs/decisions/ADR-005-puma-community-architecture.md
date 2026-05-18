# ADR-005: PUMA Community architecture using a separate repository (`pumacp/puma-community`) and downstream mirrors to Hugging Face Datasets, Zenodo, and Kaggle, with a dual-mode CLI command supporting both `--dry-run` preview and default real GitHub PR opening via a personal access token

## Status

Accepted by Daniel (project maintainer), 2026-05-18.

## Context

PUMA, as released at `v2.7.0`, is a local-first, fully reproducible benchmark platform
that evaluates open Large Language Model (LLM) agents on three project management tasks
(issue triage, effort estimation, backlog prioritization). The empirical contribution
shipped with the release is *deliberately controlled*: every reference number quoted in
`README.md` (`F1=0.5867` on `baseline_triage.yaml`, `MAE=5.7150` on
`baseline_estimation_canonical.yaml`) is generated on a single, well-defined machine,
with `temperature=0.0`, `seed=42`, a known GGUF digest per Ollama tag, and a defensive
test suite that locks the seventeen catalogued models to the profiles where they have
been validated. That body of evidence is intentionally narrow because narrow is what
makes it reproducible.

The same narrowness, however, is a ceiling. PUMA's seventeen catalogued models and five
hardware profiles do not exhaust the universe of locally-runnable LLMs or of consumer
hardware. Users have already begun to run PUMA on chips PUMA has not validated (the nine
Apple-Silicon profiles added in `v2.6.0` exist precisely to document this gap), and the
two Qwen3 entries added in `v2.7.0` are flagged as *pending validation* for exactly the
same reason: PUMA's locked reference hardware cannot run them. There is a real,
legitimate demand for a structured way to collect those externally-generated results,
without contaminating the v2.7.0 empirical record and without forcing the maintainer to
operate a server.

The natural shape of that demand is a *community corpus*: an opt-in, descriptive,
attributed dataset of `(model × scenario × hardware × metrics × emissions)` tuples,
contributed voluntarily by users who run PUMA on machines outside the locked reference
configuration. The corpus is explicitly *descriptive*, not normative — it characterizes
what happens in the wild rather than what PUMA guarantees. The locked v2.7.0 numbers
remain the only inferential claims PUMA itself makes.

This corpus must satisfy four design constraints simultaneously. First, the
`v2.7.0-academic` rollback tag must remain bit-for-bit recoverable; nothing the
community contributes may bleed into the locked release state. Second, the entire stack
must run at *zero perpetual infrastructure cost* — PUMA is published under MIT and has
no funding line, so any architecture that requires paid hosting, a credit card on file,
or a maintainer-funded VPS is disqualified. Third, the data must be FAIR (findable via
search engines and aggregators, accessible without an account, interoperable via JSON
Schema and CSV, reusable under a permissive license). Fourth, the architecture must
preserve the four principles enumerated in the project constitution (local-first,
reproducibility under `seed=42` / `temperature=0.0`, human-in-the-loop, CodeCarbon
sustainability accounting). PUMA Community is an *extension* of PUMA: it must inherit
those principles, not weaken them.

Two strategic decisions follow directly from these constraints and are non-negotiable
under this ADR.

(A) **Separate repository.** The community corpus lives in `pumacp/puma-community`, a
GitHub repository distinct from `pumacp/puma`. Storing community submissions inside the
main repository would force every submission Pull Request into the same git history that
the academic baseline tag refers to, would conflate MIT-licensed code with CC-BY-4.0
licensed data, and would scale poorly as submissions accumulate.

(B) **Dual-mode `puma share-results`.** The CLI command that publishes a submission
supports *both* a `--dry-run` mode (local preview, zero network) and a default mode
(opens a real Pull Request against `pumacp/puma-community` using the user's GitHub
personal access token). Both modes are fully implemented, equally validated, equally
tested. Neither is a stub. A single-mode design (either dry-run only or publish only)
would be hostile to one of the two legitimate user populations: contributors on
restricted networks, contributors without a configured token, and CI pipelines all need
the offline path; contributors who want frictionless publication need the network path.

## Decision

PUMA Community is structured as a seven-layer stack on top of free public services. Each
layer is replaceable, all of them are mirrors of the same canonical source, and only one
of them (the GitHub repository) is authoritative.

- **Data layer — Hugging Face Datasets.** The canonical published artifact is the
  Dataset `pumacp/puma-results`, hosted on Hugging Face. The Dataset is regenerated from
  the GitHub source of truth after each merged submission via a scheduled Action.
  Hugging Face's Datasets UI offers preview, parquet conversion, and a permanent
  hub-level URL that survives renames.

- **Governance layer — GitHub repository `pumacp/puma-community`.** This is the single
  source of truth. Contributors open a Pull Request whose payload is a JSON file under
  `submissions/`. A GitHub Actions workflow validates the payload against the schema
  shipped in Prompt 2, executes a battery of safety checks (PII scan, integrity hash
  verification, model-exclusion-list enforcement, rate limit), and either auto-merges or
  leaves a structured review comment. This layer is *separate* from `pumacp/puma`
  (decision A above): the main repository's git history is not touched by submission
  traffic.

- **Archive layer — Zenodo.** A scheduled GitHub Action publishes a snapshot of the
  GitHub repository to Zenodo on the first day of January, April, July, and October at
  00:00 UTC. Each snapshot receives an independent DOI, making the corpus citable, and
  the four-per-year cadence is a deliberate trade-off between recency and DOI
  proliferation.

- **Discoverability layer — Kaggle Datasets + GitHub Wiki + shields.io.** A weekly Action
  mirrors the dataset to Kaggle, refreshes the project's GitHub Wiki, and republishes
  the dynamic shields.io endpoint JSON consumed by the badges in `README.md` (counts of
  submissions, contributors, models covered).

- **Notification layer — Discord webhook and Telegram bot.** Both are post-merge
  notification channels only. Neither stores data. They exist to make the community
  aware of merges and milestones without paying for a paging service.

- **Demo and auxiliary layer — Google Colab + Oracle Cloud Always Free.** A
  read-the-docs-style Colab notebook demonstrates how to load the dataset and produce
  the headline plots in fifteen lines of Python. Oracle Cloud Always Free hosts a static
  landing page and a maintainer staging area; neither is on the contributor path and
  neither is required for the corpus to function.

- **Client layer — `puma share-results` and the Streamlit Community view.** The CLI
  command is dual-mode, both modes equally valid:
  - `puma share-results --dry-run` validates the local SQLite run, generates the JSON
    payload, runs the PII sweep, computes the SHA-256 integrity hash, prints a diff of
    what would be sent, and writes the payload to `data/community/staged/<id>.json`. No
    network call occurs. No token is required. This mode is the safe default for
    offline use, CI pipelines, preview, and debugging.
  - `puma share-results` (default) performs the same steps and then opens a real Pull
    Request against `pumacp/puma-community` via the GitHub API, using the personal
    access token registered earlier via `puma auth login github`. The token lives in
    `~/.config/puma/credentials.toml` with file mode `0600`. Both modes share the
    payload generation, schema validation, consent UX, PII sweep, integrity hashing,
    and rate-limit enforcement; they diverge only on the final action.
  The Streamlit dashboard gains a `🤝 Community` view that lets the user review the
  staged submissions and re-run `share-results` from a button.

## Consequences

### Positive

The architecture costs nothing perpetually: every layer is a free public service. The
v2.7.0-academic baseline tag remains bit-for-bit recoverable because community traffic
never reaches `pumacp/puma`; the locked release state is structurally inaccessible to
contributors. The corpus is FAIR: findable via Hugging Face and Kaggle, accessible via
the GitHub source, interoperable via a versioned JSON Schema, reusable under CC-BY-4.0
with required attribution. The corpus is citable via Zenodo DOIs that pin particular
snapshots in time. The `pumacp` organization already owns the GitHub, Hugging Face, and
Zenodo handles needed for the architecture, so no naming negotiations are required. The
dual-mode `share-results` command gives every legitimate user population a path forward
without forcing a single workflow on all of them. PUMA core continues to work unchanged
without the `puma.community` package installed, satisfying the opt-in extension contract.

### Negative

PUMA Community depends on three external platforms (GitHub, Hugging Face, Zenodo). A
unilateral policy change at any one of them is a real risk; the triple-mirror topology
mitigates it. Contributors without a GitHub account face a higher friction barrier; the
Issue-template fallback and the Colab demo notebook mitigate it. Governance burden grows
with submission volume; the auto-merge path for the approximately ninety-five percent of
submissions that pass all checks contains the burden. Managing a separate repository is
an additional operational surface for the maintainer; the validation, merge, mirror, and
notification automation absorb the routine load and leave only true anomalies for human
review.

## Alternatives considered

- **Single-repository approach (`community/` folder inside `pumacp/puma`).** Rejected.
  Hundreds of future submission Pull Requests would contaminate the main repository's
  git history, would force a single license to cover both code (MIT) and data
  (CC-BY-4.0), and would break the clean rollback semantics of `v2.7.0-academic`.

- **Single-mode `share-results` (only `--dry-run`, or only real publish).** Rejected.
  Dry-run-only excludes users who want frictionless publication; publish-only excludes
  users without a configured token, users on restricted networks, and CI pipelines.
  Treating both modes as first-class citizens is the only design that serves all
  legitimate use cases without sacrificing the safety value of preview.

- **Oracle Cloud as the corpus backbone.** Rejected. It violates the local-first
  principle stated in the project constitution, carries account-suspension risk for
  automation workloads, and transfers 24/7 operational debt to the maintainer.

- **Self-hosted PostgreSQL plus a REST API.** Rejected. Over-engineered for the
  anticipated data volume and contrary to the minimum-complexity principle.

- **Telegram or Discord as the primary repository.** Rejected. Not FAIR-compliant, no
  DOI, fragile persistence (channels can be banned or deleted), no schema enforcement.

- **Direct Pull Requests to a Hugging Face Dataset.** Rejected. Hugging Face's PR review
  tooling is less mature than GitHub Actions for the validation needs of this corpus
  (rate limiting, anomaly detection, auto-merge gating, structured review comments).

- **Supabase, Cloudflare D1, or Firebase.** Rejected. Over-engineered and introduces
  unnecessary backend-as-a-service dependencies whose free tiers are subject to silent
  policy changes.

- **Storing this ADR under the SDD source-of-truth directory.** Rejected. The SDD
  source-of-truth directory is normative per the project constitution and binds the
  benchmark pipeline. PUMA Community is opt-in, non-normative project tooling; an ADR
  about it must not live in the directory that governs the benchmark.

## Constitution alignment

The four principles in the project constitution are preserved as follows.

- **Local-first.** PUMA Community is an opt-in extension shipped as a separately-importable
  package (`puma.community`). The core `puma` workflow works unchanged whether or not
  the package is installed, and no network call occurs unless the user explicitly invokes
  `puma share-results`. Even then, `--dry-run` mode performs zero network access.
- **Reproducibility.** PUMA Community reads `data/puma.db` read-only via the
  `session_scope()` helper in `src/puma/storage/db.py`. It does not touch the inference
  path, the KV-cache, the runtime profile, or any of the invariants guarded by the
  `validate-baseline` mechanism added in `v2.4.0` and extended in `v2.5.0`. The
  `seed=42` and `temperature=0.0` contracts are unaffected.
- **Human-in-the-loop.** Both modes of `share-results` require explicit user invocation,
  display a diff before any irreversible action, and surface a final confirmation
  prompt. No background scheduler, no silent uploads, no telemetry.
- **Sustainability.** CodeCarbon fields already captured by PUMA's `emissions` table are
  carried into the community payload. Aggregating those fields across heterogeneous
  hardware enables future community-wide carbon characterizations, which are explicitly
  scoped *out* of v2.7.0 and *into* the community corpus.

## Coexistence with v2.4.0 – v2.7.0 features

PUMA Community must coexist with four feature families introduced in the v2.4.0 → v2.7.0
sequence without breaking any of them.

- **v2.4.0 CLI completeness.** Six top-level commands (`list-runs`,
  `list-ollama-models`, `prepare-datasets`, `wilcoxon`, `bias-analysis`,
  `generate-plots`) live in `src/puma/cli.py`. PUMA Community adds two more (`auth` and
  `share-results`) via the same `app.add_typer()` precedent established for `db_app`.
  No command names collide.
- **v2.5.0 hardening.** The dual-mode `validate-baseline` F1 and MAE invariant and the
  KV-cache contamination invariant must remain inviolate. PUMA Community reads SQLite
  read-only and never invokes inference, never touches the cache, never alters runtime
  configuration.
- **v2.6.0 Apple-Silicon support.** The nine Apple-Silicon profiles defined in
  `config/profiles.yaml` are part of the canonical profile catalogue. The
  `hardware_profile` field of the community payload reuses those identifiers verbatim
  rather than free-form text, ensuring that aggregations remain meaningful.
- **v2.7.0 catalog expansion.** The two `qwen3:30b*` entries are flagged
  *pending validation* and protected by three defensive tests; the Kimi K2.6 family is
  formally excluded with thirteen documented registry probe failures. The community
  payload builder consults the exclusion list before publication and refuses to publish
  a submission whose model is on it, with a clear error message.

No invariant is violated, no existing test is broken, and no profile is bypassed.

## References

- Risk register: `docs/community/risk-register.md`.
- Repository inventory: `docs/community/00-inventory.md`.
- Project constitution: the canonical SDD constitution file in the project's SDD
  source-of-truth directory.
- Project architecture: the canonical SDD architecture file in the same directory.
- Project technical closure note: `docs/PROJECT_TECHNICAL_CLOSURE.md`.
