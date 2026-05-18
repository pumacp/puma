# PUMA Community — Engineering Risk Register

**Status:** Living document. First version 2026-05-18.
**Companion to:** `docs/decisions/ADR-005-puma-community-architecture.md`.
**Scope:** all engineering risks that the PUMA Community subsystem introduces to PUMA
between the `v2.7.0-academic` baseline and the first community-feature release.

## Reading guide

PUMA Community is the opt-in extension that lets users contribute evaluation results
obtained on heterogeneous hardware to a public corpus hosted in the separate repository
`pumacp/puma-community`. The corpus is descriptive, not normative; it does not replace
the controlled v2.7.0 reference numbers documented in `README.md`. This register
enumerates the engineering risks that follow from that design choice.

Each risk carries an identifier, a short statement, qualitative probability and impact
ratings (Low / Medium / High), and a mitigation column with concrete implementation
details — file paths, regex patterns, test names, configuration keys — rather than
vague principles. The six risk categories are scientific and methodological (RC),
security and privacy (RS), manipulation and abuse (RM), legal and compliance (RL),
operational and sustainability (RO), and implementation-schedule (RT).

## RC — Scientific and methodological

These risks address the gap between the controlled v2.7.0 empirical contribution
(single-machine, bit-exact reproducibility) and the uncontrolled community corpus
(heterogeneous hardware, voluntary sampling, descriptive statistics only).

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RC1 | Loss of sampling control: contributors run their own choice of model, scenario, and dataset slice, so the corpus cannot be treated as a uniform random sample. | High | Medium | The submission schema marks every payload with `corpus_type = "community"` and the dashboard surfaces this label in red on every chart it renders from the corpus. The `README` of `pumacp/puma-community` declares the corpus *descriptive*, separate from the v2.7.0 inferential numbers. The Streamlit `🤝 Community` view never mixes community rows with locked baseline rows on a single axis without an overt toggle. Hugging Face Dataset cards repeat the caveat verbatim. |
| RC2 | Reduced statistical validity: per-model sample sizes will be small for rare hardware combinations, undermining naive aggregate statistics. | High | Medium | The validation Action rejects payloads claiming `n < 30` for any reported metric (threshold configurable in `community-repo/config/validation.yaml`). The Hugging Face Dataset exposes a precomputed `per_cell_n` column; the Streamlit view greys out cells with `n < 30` and prints a warning. Zenodo snapshots carry a `corpus_health.md` summary listing under-threshold cells. No statistical significance is claimed without a paired-sample Wilcoxon test (the v2.4.0 `wilcoxon` command). |
| RC3 | Hardware heterogeneity: contributors span the nine Apple-Silicon profiles introduced in v2.6.0, multiple NVIDIA generations, AMD ROCm rigs not yet validated, and pure-CPU configurations. | High | Medium | The `hardware_profile` field is enumerated against the canonical identifiers in `config/profiles.yaml`; free-form strings are rejected at submission time. Unknown profile identifiers route to a "needs new profile" Issue template instead of polluting the corpus. The validation Action computes a per-profile contribution index in `corpus_health.md`. Cross-profile aggregations require an overt `--allow-cross-profile` flag in the Streamlit view. |
| RC4 | Imperfect cross-machine reproducibility: even with `seed=42` and `temperature=0.0`, GGUF quantization layouts and hardware-bespoke kernels produce small but real numeric drift, as already formalized in hypotheses H0–H3 of `docs/CROSS_ARCH_REPRODUCIBILITY.md`. | High | Low | The submission schema records the GGUF SHA-256, the Ollama tag, the CodeCarbon `tracking_mode`, and the chip identifier. The dashboard renders cross-machine results as a forest plot with confidence intervals instead of point estimates. A footnote on every community chart links to the H0–H3 documentation so readers can interpret drift as anticipated behaviour rather than a defect. |
| RC5 | Submitter self-selection bias: users who run PUMA on consumer hardware and submit results are not a representative sample of the LLM-evaluation population. | Medium | Medium | The corpus card states the bias overtly. The dashboard never headlines a community statistic without the `corpus_type = "community"` chip next to it. The community view offers a per-country, per-hardware, per-model contribution map so the bias is visible rather than hidden. The January Zenodo snapshot each year carries a one-paragraph reflection on the prior year's contributor distribution. |

## RS — Security and privacy

These risks cover the surface introduced by external submissions and by storing a
GitHub personal access token on contributor machines.

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RS1 | Token leakage in logs or commits: a contributor's GitHub PAT is accidentally printed, committed, or attached to a submission. | Medium | High | The credential store is `~/.config/puma/credentials.toml` with file mode `0600`; a pre-commit hook scans for GitHub PAT regex patterns (`ghp_[A-Za-z0-9]{36}` and `github_pat_[A-Za-z0-9_]{82}`) and refuses commits containing them. A test `test_no_token_in_logs` patches the logger and verifies credential operations never write tokens to stdout, stderr, or log files. The publisher masks tokens to last-4-chars in every error and traceback. `puma auth login` stores the token via a single `tomli-w` write and never echoes it. |
| RS2 | PII appears in the `notes` field or in the `raw_predictions_url`: a contributor pastes their email, employer, or a private URL into a free-form text field. | Medium | High | The submission builder runs a PII sweep using deny-list regexes for email addresses, postal codes, phone numbers, IBANs, and dotted hostnames not on an allow-list. Any match aborts the build with a structured error. The schema caps `notes` at 280 characters and rejects markdown URLs. The validation Action repeats the sweep server-side as defense in depth. |
| RS3 | PII leakage in predictions: issue texts used in the triage or estimation scenarios may carry personal data that lands in the published `raw_predictions` payload. | Medium | High | By default the submission excludes raw issue text; only the instance hash, model output, gold label, and metrics are published. A `--include-raw` flag exists for transparency cases but is gated behind a triple-confirmation HITL dialog that requires typing the literal phrase `I accept publishing raw text`. The validation Action refuses payloads with `include_raw=true` when the source dataset is `jira_balanced_200`, as a belt-and-braces measure. |
| RS4 | Submission from a compromised fork: an attacker pushes a malicious Action workflow inside a Pull Request, trying to escalate via the validation pipeline. | Low | High | The validation Action runs with the `pull_request` trigger (not `pull_request_target`), so the workflow that executes is the one in the base branch, not the fork. Permissions are scoped to `contents: read, pull-requests: write` only — no `GITHUB_TOKEN` write access. Auto-merge fires only when validation succeeds and the contributor has signed the CLA via a separate workflow. Branch protection enforces required status checks on `main`. |
| RS5 | Webhook URLs revealed in code or logs: the Discord and Telegram webhook URLs grant write access to the notification channels and must remain secret. | Medium | Medium | Webhook URLs live only as GitHub Action secrets (`DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`) — never in code, env files, or PR diffs. A test `test_no_webhook_in_repo` greps every tracked file for `discord.com/api/webhooks/` and fails on any hit. The notification Action uses `::add-mask::` to redact the URL from logs. Rotation procedure: `community-repo/SECURITY.md`. |

## RM — Manipulation and abuse

These risks cover adversarial contributions: false metrics, flooding, and impersonation.

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RM1 | Fabricated submissions with false metrics: a contributor edits the JSON payload by hand to inflate `f1_macro` or deflate `mae`. | Medium | High | Each payload carries a SHA-256 integrity hash computed from the canonical serialization of the SQLite source rows; the validation Action recomputes the hash from the `raw_predictions_url` artifact and rejects mismatches. The schema requires per-instance prediction rows as an attached artifact (not just aggregate metrics), so headline numbers are re-derivable. Anomaly detection flags any `f1_macro` more than three standard deviations above the per-model corpus mean. |
| RM2 | Spam submissions in volume: a single contributor opens dozens of near-identical PRs. | Medium | Medium | The validation Action enforces a per-author rate limit of one merged submission every 24 hours (configurable). Duplicate detection keys on `(submitter_id, model, scenario, hardware_profile, sample_size, seed)`; later identical submissions are rejected with a comment pointing at the prior PR. A daily housekeeping Action closes stale, validation-failing PRs after seven days of contributor silence. |
| RM3 | Submitter impersonates another entity: the `submitter_name` field claims to be a known organization or contributor. | Low | Medium | The schema separates `submitter_github_login` (mandatory, derived server-side from the PR author, unspoofable) from `submitter_display_name` (free-form, advisory). Public dashboards prefer the GitHub login. A `CONTRIBUTORS_VERIFIED.md` lists manually verified handles; the corpus card surfaces the distinction without making non-verification a barrier. |
| RM4 | Bot submits repetitive submissions to inflate corpus visibility or game the contributor leaderboard. | Medium | Medium | The validation Action requires every PR to come from an account that has had a verified email for at least seven days; accounts younger than 24 hours are auto-rejected pending manual review. Auto-merge requires a passing CAPTCHA-equivalent (a randomly generated `submission_nonce` the contributor must echo back via a separate API call) — enough friction to deter scripted floods without burdening genuine contributors. |
| RM5 | Denial-of-service on the validation Action: a contributor (or a botnet) opens many simultaneous PRs to exhaust GitHub Actions minutes for the `pumacp` organization. | Low | Medium | Per-author concurrency is capped at one active validation job at a time via a `concurrency` group keyed on `submitter_github_login`; later PRs queue or cancel previous in-flight runs. Repository-wide total concurrency is capped at five. The maintainer is notified when monthly free-tier consumption crosses 70 percent so manual throttling can land early. |

## RL — Legal and compliance

These risks address the regulatory framework around publishing a dataset that may
carry user-identifiable metadata.

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RL1 | GDPR non-compliance: personal data is published without a lawful basis. | Medium | High | The default payload carries no personal data: `submitter_display_name` is opt-in and may be left empty (the GitHub login is then the only identifier); no email is ever in the payload; no IP is logged. A triple-consent UX in `puma share-results` (read, modify, send) records each consent in `data/community/consent.log` with timestamp and payload hash, but the log stays local. The community repository ships a `PRIVACY.md` documenting the lawful basis (consent) and the data-minimization stance. |
| RL2 | Zenodo immutability versus the right to erasure: GDPR Article 17 requires deletion on request, but Zenodo DOIs are immutable by design. | Medium | High | The submission consent form states overtly that, while the GitHub source-of-truth row can be erased on request, Zenodo snapshots are immutable archival records released under CC-BY-4.0 and will retain the contribution. Erasure requests are honoured by replacing the contributor identifier in the GitHub source row with a tombstone string and re-mirroring to Hugging Face within the week; later Zenodo snapshots no longer carry the identifier. `community-repo/PRIVACY.md` documents this procedure. |
| RL3 | License conflict: code in `pumacp/puma` is MIT but data in `pumacp/puma-community` is CC-BY-4.0, and contributors may mix them. | Medium | Medium | The two licenses live in two different repositories, eliminating directory-level confusion. The submission consent form requires overt acknowledgement of CC-BY-4.0. The Hugging Face Dataset card, Zenodo metadata, Kaggle card, and `community-repo/LICENSE` all repeat the wording. The PUMA Community CLI prints the license line and asks the user to confirm before any publication. |
| RL4 | Incorrect citation of submitters: downstream researchers cite the corpus without attribution to individual contributors. | Medium | Low | CC-BY-4.0 requires attribution. The dataset card ships a recommended citation template naming the corpus and the relevant Zenodo DOI. Per-submission DOIs are not issued (Zenodo is snapshot-level), but contributors are listed by GitHub handle in each snapshot's `contributors.csv`. The `pumacp/puma-community` README documents the recommended citation form. |
| RL5 | Cross-border data transfer: contributors and downstream consumers span jurisdictions with conflicting data-protection regimes. | Low | Medium | The corpus stores no personal data beyond a freely-chosen identifier, eliminating most jurisdictional triggers. The validation Action retains no IP-bearing logs; GitHub's own retention policy governs the PR audit trail. `PRIVACY.md` documents the data flow, recipients (GitHub, Hugging Face, Zenodo, Kaggle), and the safeguard relied upon (consent + minimization). |

## RO — Operational and sustainability

These risks address the longevity of the architecture under decisions made by
third-party platforms and by the maintainer.

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RO1 | Hugging Face changes its free Datasets policy: storage limits drop or paid tiers become mandatory. | Medium | Medium | The GitHub repository is the source of truth; Hugging Face is a mirror. If the free tier shrinks, the mirror is paused or moved to Kaggle as the primary discoverability layer without data loss. The mirror Action checks for HTTP 402 responses and posts a maintainer alert. `community-repo/RUNBOOK.md` documents the migration procedure. |
| RO2 | GitHub Actions stops being free for public repositories or imposes a stricter quota. | Low | Medium | The validation Action is lean (< 90 s typical, < 3 min worst-case). At ten merged submissions per day the monthly consumption stays well below the current public-repo allowance. If quotas tighten, the maintainer can downgrade to a self-hosted runner on a low-end VPS, or cut auto-merge cadence to a nightly batch. Mitigation choice and threshold are documented in `community-repo/RUNBOOK.md`. |
| RO3 | Zenodo withdraws the service or freezes uploads for projects without institutional backing. | Low | High | Zenodo is one of three archival paths; the GitHub source-of-truth and the Hugging Face mirror together already satisfy the F and A of FAIR. If Zenodo withdraws, the maintainer registers a Software Heritage archive ID or a DataCite DOI within the same quarter, updates the citation template, and opens an Issue in `community-repo`. |
| RO4 | Maintainer abandonment: PUMA Community accumulates years of submissions and the original maintainer becomes unavailable. | Medium | Medium | The corpus is structurally self-sustaining: GitHub keeps the source-of-truth indefinitely, Zenodo snapshots persist regardless of maintainer activity, Hugging Face serves the last mirrored version, and Kaggle preserves the latest weekly snapshot. Auto-merge handles routine validation without human intervention. `MAINTAINERS.md` documents the operational state and the ownership-transfer procedure. |
| RO5 | Unforeseen operational cost emerges: a third-party service silently introduces egress fees or rate-limit overages. | Low | Medium | The architecture has no credit card on file at any provider; if any provider requires payment, the corresponding integration is suspended rather than billed. The `RUNBOOK.md` lists every account, the maintainer email associated with it, and the recovery procedure should a free-tier exhaustion notification arrive. A monthly cron-driven Action posts a one-line status to the Discord channel summarizing usage versus quota for each integration. |

## RT — Implementation schedule

These risks cover the rollout of PUMA Community itself, prompt by prompt, against the
already-released PUMA core.

| ID  | Risk | Probability | Impact | Mitigation |
|-----|------|-------------|--------|------------|
| RT1 | Implementation of the planned prompts does not complete within five calendar weeks. | Medium | Low | Each prompt is scoped to ship in isolation: Prompts 1–2 add a self-contained schema module, Prompts 3–5 add a self-contained `puma.community` package, Prompt 9 adds a single dashboard view, Prompts 10–13 ship docs only. None touches the v2.7.0 invariants. A partial roll-out (schema + dry-run mode only) is shippable as a coherent subset; the `v2.7.0-academic` rollback tag stays intact at every checkpoint. |
| RT2 | A prompt produces an unforeseen diff that breaks an existing feature. | Medium | High | Every prompt runs the full test suite (`make test`) before commit; the suite covers `tests/unit/` and `tests/integration/`. The PUMA Community prompts also run `tests/community/` once it exists. Prompts that modify `src/puma/cli.py` or `src/puma/dashboard/app.py` show a diff of the exact lines being inserted before committing. The `v2.7.0-academic` tag is the safety anchor: `git reset --hard v2.7.0-academic` returns the repository to a known-good state. |
| RT3 | New dependencies conflict with existing ones — a known compound risk. | Medium | Medium | The PUMA Community additions (`jsonschema>=4.21`, `PyGithub>=2.3`, `tomli-w>=1.0`) must land in both `requirements.txt` and `pyproject.toml.dependencies` to avoid worsening the *pre-existing* divergence in which `matplotlib>=3.8` and `seaborn>=0.13` live only in `requirements.txt`. The PUMA Community prompts MUST NOT attempt to fix the matplotlib divergence: it pre-dates v2.7.0 and is out of scope. Separately, the three `puma_version` strings disagree (`pyproject.toml` is `2.1.0-dev`, `src/puma/__init__.py.__version__` is `2.0.0-dev`, the latest git tag is `v2.7.0`); the PUMA Community payload builder MUST source `puma_version` from the git tag (`git describe --tags --abbrev=0`) or from `ProfileSnapshot.puma_version`, NEVER from `pyproject.toml.version`. The discrepancy is logged as a known follow-up that PUMA Community works around but does not fix. |
| RT4 | External observers misinterpret PUMA Community's scope relative to the core v2.7.0 benchmark. | Medium | Medium | Every public artifact — corpus README, Hugging Face and Kaggle dataset cards, the Streamlit `🤝 Community` view, the badges in the main README — carries the label "community (descriptive, heterogeneous hardware)" next to any community-derived number, and v2.7.0 reference numbers retain the label "reference (controlled, single machine)". The contrast appears on the Hugging Face dataset card in the first paragraph, in bold. |
| RT5 | Subsequent prompts inadvertently refactor more than requested. | Medium | Medium | Each prompt has an overt *forbidden actions* list naming files that must not be touched. Each prompt runs `git diff --stat` before committing and the diff is reviewed against the planned file set. Refactors that are tempting but out of scope (such as merging `requirements.txt` into `pyproject.toml`, or unifying the three `puma_version` strings) are documented as follow-ups in this register rather than silently performed. The PUMA Community feature branch never carries unrelated changes. |

## Update procedure

Living document. New risks, revised ratings, and updated mitigations land in dedicated
commits citing the affected ID (`docs(community): update RS1 mitigation`). Older rows
are amended, not deleted, so threat-model history stays auditable from `git log`.
