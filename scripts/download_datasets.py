"""
Download and preprocess datasets for PUMA benchmark.

TAWOS (The Agile Work Of Stories):
  Official source : github.com/SOLAR-group/TAWOS
  License         : Apache-2.0
  DOI             : 10.5522/04/21308124
  Local dump      : db/TAWOS.sql.zip  (MySQL dump, 4.3 GB uncompressed)

Jira:
  Generated locally by scripts/create_jira_data.py (200 balanced issues).

Usage:
  python scripts/download_datasets.py
"""

import io
import os
import sys
import re
import csv
import zipfile
import subprocess
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.parent
DATA_DIR  = BASE_DIR / "data"
DB_DIR    = BASE_DIR / "db"
DATA_DIR.mkdir(exist_ok=True)

TAWOS_ZIP     = DB_DIR / "TAWOS.sql.zip"
TAWOS_SQL     = "TAWOS.sql"          # name inside the zip
TAWOS_RAW     = DATA_DIR / "tawos_raw.csv"
TAWOS_CLEAN   = DATA_DIR / "tawos_clean.csv"
JIRA_OUTPUT   = DATA_DIR / "jira_balanced_200.csv"
CREATE_JIRA   = Path(__file__).parent / "create_jira_data.py"

# ── TAWOS configuration ───────────────────────────────────────────────────────
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}

# TAWOS project key → PUMA experiment label
# TISTUD (Appcelerator Studio) is the ~2 000-item project documented as APSTUD.
TAWOS_PROJECT_MAP = {
    "MESOS":  "MESOS",
    "TISTUD": "APSTUD",
    "XD":     "XD",
}
TARGET_PROJECTS = set(TAWOS_PROJECT_MAP.keys())

# Fixed column indices in the Issue table (see CREATE TABLE in dump):
# 0=ID, 1=Jira_ID, 2=Issue_Key, 3=URL, 4=Title, 5=Description,
# 6=Description_Text, 7=Description_Code, 8=Type, 9=Priority, 10=Status,
# 11=Resolution, 12-15=dates, 16=Story_Point, ...
IDX_KEY   = 2
IDX_TITLE = 4
IDX_DESC  = 6   # Description_Text (natural-language portion)
IDX_TYPE  = 8   # Issue type — filter to 'Story' (user stories only)
IDX_SP    = 16

STORY_TYPES = {"Story", "story"}  # Jira user story type


# ── SQL value parser ──────────────────────────────────────────────────────────

def _parse_value(s: str, pos: int):
    """Parse one SQL value at position pos. Returns (value, next_pos)."""
    while pos < len(s) and s[pos] == ' ':
        pos += 1
    if pos >= len(s):
        return None, pos

    if s[pos] == "'":
        # Single-quoted string — handles \' and '' escapes
        buf = []
        pos += 1
        while pos < len(s):
            c = s[pos]
            if c == '\\' and pos + 1 < len(s):
                buf.append(s[pos + 1])
                pos += 2
            elif c == "'" :
                if pos + 1 < len(s) and s[pos + 1] == "'":
                    buf.append("'")
                    pos += 2
                else:
                    pos += 1
                    break
            else:
                buf.append(c)
                pos += 1
        return ''.join(buf), pos

    if s[pos:pos + 4] == 'NULL':
        return None, pos + 4

    # Number (int or float)
    end = pos
    while end < len(s) and s[end] not in (',', ')'):
        end += 1
    raw = s[pos:end].strip()
    try:
        val = float(raw) if '.' in raw else int(raw)
    except ValueError:
        val = raw
    return val, end


def _parse_row(s: str, start: int):
    """
    Parse one VALUES row starting at the opening '(' at position start.
    Returns a list of values (up to IDX_SP + 1 columns) and the position
    after the closing ')'.
    """
    pos = start + 1     # skip '('
    values = []
    need = IDX_SP + 1   # stop once we have enough columns
    while pos < len(s) and len(values) < need:
        val, pos = _parse_value(s, pos)
        values.append(val)
        # skip comma or ')' separator
        while pos < len(s) and s[pos] in (' ', ','):
            if s[pos] == ',':
                pos += 1
                break
            pos += 1
        # If next char is ')' this row is done
        if pos < len(s) and s[pos] == ')':
            pos += 1
            break
    return values, pos


# ── TAWOS extraction ──────────────────────────────────────────────────────────

# Regex: find the start of any Issue row whose Issue_Key matches a target project.
# Pattern: opening paren, two ints, then a quoted key like 'MESOS-123'
_ROW_RE = re.compile(
    r'\(\d+,\d+,\'(' + '|'.join(TARGET_PROJECTS) + r')-\d+\''
)


def extract_tawos(zip_path: Path, raw_out: Path, clean_out: Path) -> None:
    print(f"  Parsing {zip_path.name} ({zip_path.stat().st_size / 1_048_576:.0f} MB compressed)…")
    print("  This may take several minutes — reading 4 GB SQL dump.")

    raw_rows   = []
    clean_rows = []
    insert_n   = 0

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(TAWOS_SQL) as raw_f:
            fh = io.TextIOWrapper(raw_f, encoding="utf-8", errors="replace")
            for line in fh:
                if not line.startswith("INSERT INTO `Issue`"):
                    continue
                insert_n += 1

                # Find all target-project rows in this INSERT statement
                for m in _ROW_RE.finditer(line):
                    row_start = m.start()
                    try:
                        values, _ = _parse_row(line, row_start)
                    except Exception:
                        continue

                    if len(values) <= IDX_SP:
                        continue

                    issue_key = values[IDX_KEY] or ""
                    project   = issue_key.split("-")[0] if "-" in issue_key else ""
                    if project not in TARGET_PROJECTS:
                        continue

                    title = str(values[IDX_TITLE] or "").strip()
                    desc  = str(values[IDX_DESC]  or "").strip()
                    sp_raw = values[IDX_SP]

                    try:
                        sp = float(sp_raw) if sp_raw is not None else None
                    except (TypeError, ValueError):
                        sp = None

                    if sp is None:
                        continue

                    raw_rows.append({
                        "project":      project,
                        "title":        title,
                        "description":  desc,
                        "story_points": sp,
                    })

                if insert_n % 10 == 0:
                    print(f"    … {insert_n} INSERT blocks, {len(raw_rows)} target rows found",
                          end="\r")

    print(f"\n  Parsed {insert_n} INSERT blocks → {len(raw_rows):,} target-project rows")

    _write_csv(raw_rows, raw_out)
    print(f"  Saved {len(raw_rows):,} rows → {raw_out}")

    # ── Preprocessing ─────────────────────────────────────────────────────────
    for r in raw_rows:
        if not r["description"].strip():
            continue
        sp = r["story_points"]
        if sp != int(sp) or int(sp) not in FIBONACCI:
            continue
        clean_rows.append({
            "project":      TAWOS_PROJECT_MAP[r["project"]],
            "title":        r["title"],
            "description":  r["description"],
            "story_points": int(sp),
        })

    _write_csv(clean_rows, clean_out)
    print(f"  Saved {len(clean_rows):,} rows → {clean_out}")

    print("\n  Project counts (tawos_clean.csv):")
    counts = {}
    for r in clean_rows:
        counts[r["project"]] = counts.get(r["project"], 0) + 1
    for label in ["MESOS", "APSTUD", "XD"]:
        print(f"    {label}: {counts.get(label, 0):,}")


def _write_csv(rows: list, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["project", "title", "description", "story_points"])
        w.writeheader()
        w.writerows(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PUMA Dataset Preparation")
    print("=" * 60)

    # ── 1. TAWOS ──────────────────────────────────────────────────────────────
    print("\n=== 1. TAWOS Dataset ===")
    print("Source: SOLAR-group/TAWOS (DOI: 10.5522/04/21308124, Apache-2.0)")

    if TAWOS_CLEAN.exists() and TAWOS_CLEAN.stat().st_size > 0:
        print(f"  tawos_clean.csv already exists ({TAWOS_CLEAN.stat().st_size:,} bytes), skipping.")
        print("  Delete data/tawos_clean.csv to force re-generation.")
    elif not TAWOS_ZIP.exists():
        print(f"  ERROR: {TAWOS_ZIP} not found.")
        print("  Download the official TAWOS SQL dump and place it at db/TAWOS.sql.zip")
        print("  URL: https://rdr.ucl.ac.uk/ndownloader/files/37806375")
        sys.exit(1)
    else:
        extract_tawos(TAWOS_ZIP, TAWOS_RAW, TAWOS_CLEAN)

    # ── 2. Jira ───────────────────────────────────────────────────────────────
    print("\n=== 2. Jira Dataset ===")
    print("Source: scripts/create_jira_data.py (200 balanced issues, 50 per priority)")

    if JIRA_OUTPUT.exists() and JIRA_OUTPUT.stat().st_size > 0:
        print(f"  jira_balanced_200.csv already exists ({JIRA_OUTPUT.stat().st_size:,} bytes), skipping.")
    else:
        print("  Generating jira_balanced_200.csv…")
        result = subprocess.run(
            [sys.executable, str(CREATE_JIRA)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  Generated successfully.")
        else:
            print(f"  ERROR: {result.stderr}")
            sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n=== Dataset Status ===")
    for f in sorted(DATA_DIR.glob("*.csv")):
        print(f"  {f.name}: {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
