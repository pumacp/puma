# db/ — Database dumps and large data files

This folder is intentionally kept in version control as a placeholder, but its
contents are ignored by `.gitignore` because they typically exceed the 100 MB
file size limit imposed by GitHub.

## How to populate this folder

Run the dataset download script from the repository root:

```bash
python scripts/download_datasets.py
```

This will fetch the TAWOS database dump and any other required data files
from their original sources.

## Why files here are not committed

- `db/TAWOS.sql` and similar SQL dumps are several GB in size.
- GitHub rejects pushes that contain files larger than 100 MB.
- Repositories larger than 1 GB in total are discouraged by GitHub.
- For large binary assets, prefer Git LFS or external storage (S3, HuggingFace, etc.).

## What IS tracked here

- `.gitkeep` — keeps the directory in the repository
- `README.md` — this file
