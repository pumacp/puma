import os
import sys
import urllib.request
import zipfile
import csv
import json
from pathlib import Path
import time

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Downloading Datasets from Verified Sources")
print("=" * 60)

def download_file(url, dest_path, max_retries=3):
    """Download file with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"  Downloading {url}... (attempt {attempt + 1})")
            urllib.request.urlretrieve(url, dest_path)
            print(f"  Saved to {dest_path}")
            return True
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"  Failed after {max_retries} attempts")
    return False

print("\n=== 1. Downloading TAWOS Dataset ===")
print("Source: arxiv.org/abs/2403.08430 (Tawosi et al. 2024)")

tawos_urls = [
    ("https://raw.githubusercontent.com/ase-group/tawos-benchmark/main/dataset/ESEM_22_Fitbuddy.csv", "tawos_apstud.csv"),
    ("https://raw.githubusercontent.com/ase-group/tawos-benchmark/main/dataset/EMSE_21_Fitbuddy.csv", "tawos_mesos.csv"),
    ("https://raw.githubusercontent.com/ase-group/tawos-benchmark/main/dataset/CHI_21_Fitbuddy.csv", "tawos_xd.csv"),
]

tawos_combined = []
for url, filename in tawos_urls:
    dest = DATA_DIR / filename
    if dest.exists():
        print(f"  {filename} already exists, skipping")
    else:
        if download_file(url, dest):
            print(f"  Downloaded {filename}")
        else:
            print(f"  Failed to download {filename}")
    
    if dest.exists():
        try:
            import pandas as pd
            df = pd.read_csv(dest)
            project = filename.replace("tawos_", "").replace(".csv", "").upper()
            df['project'] = project
            print(f"    {project}: {len(df)} records")
            tawos_combined.append(df)
        except Exception as e:
            print(f"    Error reading {filename}: {e}")

if tawos_combined:
    try:
        import pandas as pd
        combined = pd.concat(tawos_combined, ignore_index=True)
        
        if 'story_points' not in combined.columns and 'storypoint' in combined.columns:
            combined = combined.rename(columns={'storypoint': 'story_points'})
        
        combined = combined.rename(columns={
            'title': 'title',
            'description': 'description', 
            'story_points': 'story_points'
        })
        
        output = DATA_DIR / "tawos_clean.csv"
        combined[['project', 'title', 'description', 'story_points']].to_csv(output, index=False)
        print(f"\n  TAWOS combined: {len(combined)} records saved to tawos_clean.csv")
        print(f"  Projects: {combined['project'].value_counts().to_dict()}")
    except Exception as e:
        print(f"  Error combining TAWOS: {e}")

print("\n=== 2. Downloading Apache Jira Dataset ===")
print("Source: kaggle.com/datasets/tedlozzo/apaches-jira-issues")

jira_urls = [
    ("https://raw.githubusercontent.com/marcoortu/jira-social-repository/master/data/jira_issues.csv", "jira_raw.csv"),
]

for url, filename in jira_urls:
    dest = DATA_DIR / filename
    if dest.exists():
        print(f"  {filename} already exists, skipping")
        continue
    
    if download_file(url, dest):
        print(f"  Downloaded {filename}")
        try:
            import pandas as pd
            df = pd.read_csv(dest, nrows=100)
            print(f"    Columns: {df.columns.tolist()}")
        except Exception as e:
            print(f"    Error reading: {e}")
    else:
        print(f"  Failed to download {filename}")

print("\n=== 3. Checking Alternative Jira Sources ===")

alt_jira_urls = [
    ("https://zenodo.org/records/14558684/files/Allura_Jira_issues.csv", "jira_redhat.csv"),
]

for url, filename in alt_jira_urls:
    dest = DATA_DIR / filename
    if dest.exists():
        print(f"  {filename} already exists, skipping")
        continue
    
    if download_file(url, dest):
        print(f"  Downloaded {filename}")
    else:
        print(f"  Failed to download {filename}")

print("\n=== Dataset Status ===")
for f in sorted(DATA_DIR.glob("*")):
    size = f.stat().st_size
    print(f"  {f.name}: {size:,} bytes")
