# Scenarios Reference

## triage_jira

**Task**: Assign a priority label to a Jira issue.

| Field | Value |
|-------|-------|
| Dataset | Jira balanced (200 issues, 50 per class) |
| Labels | `Critical`, `Major`, `Minor`, `Trivial` |
| Input | `title`, `description` |
| Gold column | `priority` |
| Primary metric | `f1_macro` |
| Class | `puma.scenarios.triage_jira.TriageJiraScenario` |

**Parse logic**: regex `r"\\b(Critical|Major|Minor|Trivial)\\b"` (case-insensitive, first match).

---

## estimation_tawos

**Task**: Estimate story points for a user story.

| Field | Value |
|-------|-------|
| Dataset | TAWOS (agile backlog items) |
| Output | Fibonacci number from {1, 2, 3, 5, 8, 13, 21, 34, 55, 89} |
| Input | `title`, `description` |
| Gold column | `story_points` |
| Primary metric | `mae` |
| Class | `puma.scenarios.estimation_tawos.EstimationTawosScenario` |

**Parse logic**: extract first number from response; snap to nearest Fibonacci if within ±1.

---

## prioritization_jira

**Task**: Given two Jira issues A and B, determine which has higher priority.

| Field | Value |
|-------|-------|
| Dataset | Jira (pairs sampled from SR issues) |
| Labels | `A`, `B` |
| Input | Two issue descriptions |
| Gold column | `higher_priority` |
| Primary metric | `accuracy` |
| Class | `puma.scenarios.prioritization_jira.PrioritizationJiraScenario` |

**Parse logic**: regex `r"\\b([AB])\\b"` (first match).

**Priority order** (highest → lowest): Critical > Major > Minor > Trivial.
