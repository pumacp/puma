# data/ — Datasets

Datasets are **not** versioned in this repository. Regenerate them locally:

```bash
python scripts/download_datasets.py
```

## Sources

| Dataset | Source | DOI / URL |
|---------|--------|-----------|
| Jira Social Repository (balanced) | Zenodo | 10.5281/zenodo.5901893 |
| TAWOS issue tracker | SOLAR-group/TAWOS | github.com/SOLAR-group/TAWOS |

## Expected files after running the script

| File | Approx. size |
|------|-------------:|
| `data/jira_balanced_200.csv` | ~200 KB |
| `data/tawos_clean.csv` | ~5.5 MB |
| `data/tawos_raw.csv` | ~5.9 MB |

SHA-256 checksums are validated automatically by `scripts/download_datasets.py`.

## What IS tracked here

- `.gitkeep` — keeps the directory in the repository.
- `README.md` — this file.

Everything else is ignored by `.gitignore` (`data/*.csv`, `data/*.json`,
`data/*.parquet`).
