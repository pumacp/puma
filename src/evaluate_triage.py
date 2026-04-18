import os
import json
import logging
import sys
from pathlib import Path

# Allow importing from src/puma package
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from pathlib import Path
from typing import Optional
from sklearn.metrics import confusion_matrix, f1_score, classification_report
from codecarbon import track_emissions
from history import save_to_history, get_ollama_model_info

# Re-export from new module location for forward compatibility
from puma.scenarios.triage_jira import (  # noqa: F401
    parse_prediction,
    TriageEvaluator,
    calculate_metrics,
    VALID_PRIORITIES,
    DETERMINISTIC_OPTIONS,
    SYSTEM_PROMPT,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
JIRA_INPUT = DATA_DIR / "jira_balanced_200.csv"
CACHE_FILE = RESULTS_DIR / "triage_cache.json"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("LLM_MODEL", "qwen2.5:3b")

# Triage evaluation configuration
# Target F1-macro score (original requirement: 0.55)
TRIAGE_TARGET_F1 = float(os.environ.get("TRIAGE_TARGET_F1", "0.55"))
# Temperature for LLM (0.0 = deterministic)
TRIAGE_TEMPERATURE = float(os.environ.get("TRIAGE_TEMPERATURE", "0.0"))
# Random seed for reproducibility
TRIAGE_SEED = int(os.environ.get("TRIAGE_SEED", "42"))

SYSTEM_PROMPT = (
    "Eres un experto en gestión de proyectos TIC. "
    "Analiza el título y descripción de la incidencia y responde ÚNICAMENTE "
    "con una de estas palabras exactas: Critical, Major, Minor o Trivial. "
    "No añadas ninguna explicación ni puntuación extra."
)

DETERMINISTIC_OPTIONS = {
    "temperature": TRIAGE_TEMPERATURE,
    "seed": TRIAGE_SEED,
    "num_predict": 10
}

VALID_PRIORITIES = ["Critical", "Major", "Minor", "Trivial"]


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Cache file corrupted, starting fresh")
    return {}


def save_cache(cache: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def parse_prediction(response: str) -> Optional[str]:
    response_clean = response.strip().strip('.').strip(',')
    
    for priority in VALID_PRIORITIES:
        if priority.lower() in response_clean.lower():
            return priority
    
    logger.warning(f"Could not parse response: '{response}'")
    return None


class TriageEvaluator:
    def __init__(self, model: str = MODEL_NAME):
        import ollama
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = model
        logger.info(f"TriageEvaluator initialized with model: {model}")
    
    def evaluate_issue(self, issue_key: str, title: str, description: str) -> Optional[str]:
        user_prompt = f"Título: {title}\n\nDescripción: {description}"
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                options=DETERMINISTIC_OPTIONS
            )
            
            prediction = parse_prediction(response["message"]["content"])
            logger.debug(f"Issue {issue_key}: {prediction}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error evaluating issue {issue_key}: {e}")
            return None
    
    def evaluate_batch(self, df: pd.DataFrame) -> dict:
        cache = load_cache()
        
        results = []
        skipped = 0
        processed = 0
        
        for idx, row in df.iterrows():
            issue_key = str(row.get("issue_key", f"issue_{idx}"))
            
            if issue_key in cache:
                logger.info(f"Skipping cached issue: {issue_key}")
                skipped += 1
                results.append({
                    "issue_key": issue_key,
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "priority": row.get("priority", ""),
                    "prediction": cache[issue_key]["prediction"]
                })
                continue
            
            title = row.get("title", "")
            description = row.get("description", "")
            true_priority = row.get("priority", "")
            
            prediction = self.evaluate_issue(issue_key, title, description)
            
            result = {
                "issue_key": issue_key,
                "title": title,
                "description": description,
                "priority": true_priority,
                "prediction": prediction
            }
            
            cache[issue_key] = {"priority": true_priority, "prediction": prediction}
            results.append(result)
            processed += 1
            
            if processed % 10 == 0:
                save_cache(cache)
                logger.info(f"Processed {processed} issues, saved cache")
        
        save_cache(cache)
        logger.info(f"Batch complete: {processed} new, {skipped} cached")
        
        return results


def calculate_metrics(results: list) -> dict:
    y_true = []
    y_pred = []
    
    for r in results:
        if r["priority"] and r["prediction"]:
            y_true.append(r["priority"])
            y_pred.append(r["prediction"])
    
    if not y_true:
        logger.error("No valid predictions to calculate metrics")
        return {}
    
    labels = VALID_PRIORITIES
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    f1_macro = f1_score(y_true, y_pred, labels=labels, average="macro")
    
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True)
    
    metrics = {
        "f1_macro": f1_macro,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
        "classification_report": report,
        "total_samples": len(y_true),
        "model": MODEL_NAME,
        "options": DETERMINISTIC_OPTIONS
    }
    
    return metrics


@track_emissions(project_name="puma_triage")
def run_evaluation():
    logger.info("=" * 60)
    logger.info("Starting Triage Evaluation (Phase 3)")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Ollama Host: {OLLAMA_HOST}")
    logger.info("=" * 60)
    
    if not JIRA_INPUT.exists():
        logger.error(f"Input file not found: {JIRA_INPUT}")
        logger.info("Run 'python src/data_prep.py' first to generate the dataset")
        return
    
    df = pd.read_csv(JIRA_INPUT)
    logger.info(f"Loaded {len(df)} issues from {JIRA_INPUT}")
    
    evaluator = TriageEvaluator()
    
    results = evaluator.evaluate_batch(df)
    
    metrics = calculate_metrics(results)
    
    logger.info("=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    
    f1_value = metrics.get('f1_macro')
    if f1_value is not None:
        logger.info(f"F1-Macro: {f1_value:.4f}")
    else:
        logger.info("F1-Macro: N/A (no valid predictions)")
    
    if "classification_report" in metrics:
        logger.info("\nPer-class metrics:")
        for priority in VALID_PRIORITIES:
            if priority in metrics["classification_report"]:
                p = metrics["classification_report"][priority]
                logger.info(f"  {priority:10} - Precision: {p['precision']:.3f}, Recall: {p['recall']:.3f}, F1: {p['f1-score']:.3f}")
    
    target = TRIAGE_TARGET_F1
    f1 = metrics.get("f1_macro", 0)
    status = "PASSED" if f1 >= target else "BELOW TARGET"
    logger.info(f"\nTarget: F1-macro >= {target}")
    logger.info(f"Status: {status}")

    model_info = get_ollama_model_info(OLLAMA_HOST)
    save_to_history(
        task_type="triage",
        model_name=model_info.get("model_name", MODEL_NAME),
        model_size_gb=model_info.get("model_size_gb"),
        metric_name="f1_macro",
        metric_value=f1 if f1 else 0.0,
        target_value=target,
        status=status
    )
    
    metrics_file = RESULTS_DIR / "triage_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Metrics saved to {metrics_file}")
    
    return metrics


if __name__ == "__main__":
    run_evaluation()
