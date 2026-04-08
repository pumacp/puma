import os
import logging
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit
from pathlib import Path
import requests
from io import StringIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
JIRA_OUTPUT = DATA_DIR / "jira_balanced_200.csv"
TAWOS_OUTPUT = DATA_DIR / "tawos_clean.csv"


def download_jira_data():
    jira_path = DATA_DIR / "jira_raw.csv"
    
    if jira_path.exists():
        logger.info(f"Found existing Jira data at {jira_path}")
        return pd.read_csv(jira_path)
    
    urls_to_try = [
        "https://raw.githubusercontent.com/marcoortu/jira-social-repository/master/data/jira_issues.csv",
        "https://raw.githubusercontent.com/marcoortu/jira-social-repository/main/data/jira_issues.csv",
    ]
    
    for url in urls_to_try:
        try:
            logger.info(f"Attempting to download Jira data from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            df.to_csv(jira_path, index=False)
            logger.info(f"Jira data saved to {jira_path}")
            return df
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            continue
    
    logger.warning("Could not download Jira from GitHub, trying alternative sources...")
    
    try:
        url = "https://zenodo.org/records/5901804/files/ThePublicJiraDataset.csv"
        logger.info(f"Attempting to download from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), nrows=10000)
        df.to_csv(jira_path, index=False)
        logger.info(f"Jira data saved to {jira_path}")
        return df
    except Exception as e:
        logger.warning(f"Failed to download from Zenodo: {e}")
    
    raise FileNotFoundError("Could not download Jira data from any source")


def prepare_jira_dataset():
    logger.info("Preparing Jira balanced dataset (50 issues per class)...")
    
    try:
        df = download_jira_data()
    except FileNotFoundError:
        logger.warning("Using sample data structure for Jira")
        columns = ['issue_key', 'title', 'description', 'priority']
        df = pd.DataFrame(columns=columns)
    
    priority_col = None
    for col in ['priority', 'Priority', 'Priority Id', 'priority_id']:
        if col in df.columns:
            priority_col = col
            break
    
    if priority_col is None:
        logger.error(f"Available columns: {df.columns.tolist()}")
        logger.error("Dataset must contain 'priority' column")
        raise ValueError("Missing 'priority' column in Jira dataset")
    
    valid_priorities = ['Critical', 'Major', 'Minor', 'Trivial']
    priority_mapping = {
        'Blocker': 'Critical',
        'Critical': 'Critical',
        'Highest': 'Critical',
        'Major': 'Major',
        'High': 'Major',
        'Normal': 'Major',
        'Medium': 'Major',
        'Minor': 'Minor',
        'Low': 'Minor',
        'Trivial': 'Trivial',
        'Lowest': 'Trivial'
    }
    
    df['priority_normalized'] = df[priority_col].map(
        lambda x: priority_mapping.get(str(x).title(), str(x).title()) if pd.notna(x) else None
    )
    df = df[df['priority_normalized'].isin(valid_priorities)].copy()
    
    if df.empty:
        logger.error("No valid priorities found in dataset")
        raise ValueError("Empty dataset after filtering priorities")
    
    title_col = None
    for col in ['title', 'Title', 'summary', 'Summary', 'issue_summary']:
        if col in df.columns:
            title_col = col
            break
    
    desc_col = None
    for col in ['description', 'Description', 'issue_description', 'desc']:
        if col in df.columns:
            desc_col = col
            break
    
    key_col = None
    for col in ['issue_key', 'issuekey', 'key', 'Issue Key']:
        if col in df.columns:
            key_col = col
            break
    
    df = df.rename(columns={
        title_col: 'title' if title_col else 'title',
        desc_col: 'description' if desc_col else 'description',
        key_col: 'issue_key' if key_col else 'issue_key',
        'priority_normalized': 'priority'
    })
    
    if 'title' not in df.columns:
        df['title'] = ''
    if 'description' not in df.columns:
        df['description'] = ''
    if 'issue_key' not in df.columns:
        df['issue_key'] = [f"ISSUE-{i}" for i in range(len(df))]
    
    df['title'] = df['title'].fillna('')
    df['description'] = df['description'].fillna('')
    
    ISSUES_PER_CLASS = 50
    balanced_dfs = []
    
    for priority in valid_priorities:
        class_df = df[df['priority'] == priority]
        
        if len(class_df) >= ISSUES_PER_CLASS:
            sss = StratifiedShuffleSplit(n_splits=1, test_size=ISSUES_PER_CLASS, random_state=42)
            for _, idx in sss.split(class_df, class_df['priority']):
                sampled = class_df.iloc[idx].copy()
                balanced_dfs.append(sampled)
                logger.info(f"Sampled {len(sampled)} issues for priority '{priority}'")
        else:
            logger.warning(f"Not enough issues for '{priority}': {len(class_df)} available, using all ({len(class_df)})")
            if len(class_df) > 0:
                balanced_dfs.append(class_df.copy())
    
    if not balanced_dfs:
        logger.error("No issues available after filtering")
        raise ValueError("Empty dataset after filtering priorities")
    
    result_df = pd.concat(balanced_dfs, ignore_index=True)
    result_df = result_df[['issue_key', 'title', 'description', 'priority']]
    
    result_df.to_csv(JIRA_OUTPUT, index=False)
    logger.info(f"Jira balanced dataset saved to {JIRA_OUTPUT} ({len(result_df)} total issues)")
    
    return result_df


def download_tawos_data():
    tawos_path = DATA_DIR / "tawos_raw.csv"
    
    if tawos_path.exists():
        logger.info(f"Found existing TAWOS data at {tawos_path}")
        return pd.read_csv(tawos_path)
    
    try:
        logger.info("Downloading TAWOS data from Hugging Face...")
        hf_url = "https://huggingface.co/datasets/giseldo/TAWOS/resolve/main/tawosdeep.csv"
        
        response = requests.get(hf_url, timeout=120)
        response.raise_for_status()
        
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        if 'storypoint' in df.columns:
            df = df.rename(columns={'storypoint': 'story_points'})
        
        df['project'] = df['issuekey'].str.split('-').str[0]
        
        df.to_csv(tawos_path, index=False)
        logger.info(f"TAWOS data saved to {tawos_path} ({len(df)} records)")
        return df
        
    except Exception as e:
        logger.warning(f"Failed to download from Hugging Face: {e}")
    
    fallback_urls = [
        "https://raw.githubusercontent.com/SOLAR-group/TAWOS/main/dataset.csv",
    ]
    
    for url in fallback_urls:
        try:
            logger.info(f"Trying {url}")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            df.to_csv(tawos_path, index=False)
            logger.info(f"TAWOS data saved to {tawos_path}")
            return df
        except Exception as e:
            logger.warning(f"Failed: {e}")
            continue
    
    raise FileNotFoundError("Could not download TAWOS data from any source")


def prepare_tawos_dataset():
    logger.info("Preparing TAWOS dataset...")
    
    try:
        df = download_tawos_data()
    except FileNotFoundError:
        logger.warning("Using sample data structure for TAWOS")
        columns = ['project', 'title', 'description', 'story_points']
        df = pd.DataFrame(columns=columns)
    
    if 'storypoint' in df.columns:
        df = df.rename(columns={'storypoint': 'story_points'})
    
    story_col = None
    for col in ['story_points', 'storypoint', 'Story Points', 'SP', 'story_point']:
        if col in df.columns:
            story_col = col
            break
    
    title_col = None
    for col in ['title', 'Title', 'summary', 'Summary', 'issue_title']:
        if col in df.columns:
            title_col = col
            break
    
    desc_col = None
    for col in ['description', 'Description', 'issue_description', 'desc', 'text']:
        if col in df.columns:
            desc_col = col
            break
    
    if story_col and title_col:
        df_clean = pd.DataFrame()
        df_clean['story_points'] = pd.to_numeric(df[story_col], errors='coerce')
        df_clean['title'] = df[title_col] if title_col else ''
        
        if desc_col and desc_col in df.columns:
            df_clean['description'] = df[desc_col].fillna('')
        else:
            df_clean['description'] = ''
        
        if 'project' in df.columns:
            df_clean['project'] = df['project'].fillna('Unknown')
        elif 'issuekey' in df.columns:
            df_clean['project'] = df['issuekey'].str.split('-').str[0].fillna('Unknown')
        else:
            df_clean['project'] = 'Unknown'
    else:
        required_cols = ['title', 'description', 'story_points']
        missing = [c for c in required_cols if c not in df.columns]
        
        if missing:
            logger.warning(f"Missing columns: {missing}, using available columns")
            available = [c for c in required_cols if c in df.columns]
            if not available:
                raise ValueError("No required columns available in TAWOS dataset")
            df_clean = df[available].copy()
        else:
            df_clean = df[required_cols].copy()
    
    df_clean = df_clean.dropna(subset=['title', 'story_points'])
    df_clean['story_points'] = df_clean['story_points'].astype(float)
    df_clean['title'] = df_clean['title'].fillna('')
    df_clean['description'] = df_clean['description'].fillna('')
    df_clean['project'] = df_clean['project'].fillna('Unknown')
    
    df_clean = df_clean[['project', 'title', 'description', 'story_points']]
    df_clean.to_csv(TAWOS_OUTPUT, index=False)
    
    logger.info(f"TAWOS cleaned dataset saved to {TAWOS_OUTPUT} ({len(df_clean)} records)")
    logger.info(f"Projects: {df_clean['project'].unique().tolist()[:10]}...")
    
    return df_clean


def main():
    DATA_DIR.mkdir(exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("Starting Data Preparation Pipeline")
    logger.info("=" * 50)
    
    try:
        jira_df = prepare_jira_dataset()
        logger.info(f"Jira dataset: {len(jira_df)} issues")
    except Exception as e:
        logger.error(f"Jira preparation failed: {e}")
    
    try:
        tawos_df = prepare_tawos_dataset()
        logger.info(f"TAWOS dataset: {len(tawos_df)} records")
    except Exception as e:
        logger.error(f"TAWOS preparation failed: {e}")
    
    logger.info("Data preparation complete!")


if __name__ == "__main__":
    main()
