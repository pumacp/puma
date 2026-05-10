# Datasets

These dataset CSVs are tracked in this repository (small enough for git):

| File | Size | Origin |
|------|------|--------|
| jira_balanced_200.csv | ~24 KB | Generated from Jira Social Repository (Zenodo DOI 10.5281/zenodo.5901893) |
| tawos_clean.csv       | ~5.5 MB | Processed from TAWOS SQL dump |
| tawos_raw.csv         | ~5.9 MB | Processed from TAWOS SQL dump |

Total tracked: ~12 MB.

## Regeneration

### Jira (works without external setup)

```bash
python scripts/create_jira_data.py
```

### TAWOS (requires manual setup)

TAWOS regeneration requires the upstream SQL dump (~1.5 GB compressed,
4.3 GB uncompressed) which is too large for git distribution.

1. Manually obtain `TAWOS.sql.zip` from the SOLAR-group project at
   <https://github.com/SOLAR-group/TAWOS>
2. Place at `db/TAWOS.sql.zip` (gitignored)
3. Run:

```bash
python scripts/prepare_datasets.py
```

## Future work

- Implement automated fetch of TAWOS dump from a stable mirror

## Sources

- Jira Social Repository: Zenodo DOI 10.5281/zenodo.5901893
- TAWOS: github.com/SOLAR-group/TAWOS
