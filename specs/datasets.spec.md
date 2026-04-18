---
id: spec-datasets-v1
title: Datasets — Jira SR and TAWOS loaders
phase: F2
status: approved
---

# Datasets Spec

## puma.datasets.jira_sr
- Downloads from Zenodo (DOI 10.5281/zenodo.5901893)
- Verifies SHA256
- Loads to DataFrame with columns: issue_key, project_key, summary,
  description, priority, issue_type, created, resolved
- `sample(n, seed, stratify_by='priority') -> DataFrame`

## puma.datasets.tawos
- Source: TAWOS.sql in db/ (from https://github.com/SOLAR-group/TAWOS)
- Parses SQL dump to DataFrame: story_id, project_key, title,
  description, story_points, created
- `sample(n, seed) -> DataFrame`

## puma.datasets.verify
- Checks db/jira_sr.csv or data/jira_balanced_200.csv
- Checks db/tawos.csv or data/tawos_clean.csv
- Reports row counts, class distribution, date ranges

## Gate checklist
- [ ] `puma datasets verify` reports files present and valid
- [ ] Both loaders return DataFrames with required columns
- [ ] TAWOS SQL parser handles the db/TAWOS.sql file
