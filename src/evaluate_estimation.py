import os
import sys
import json
import logging
import time
import signal
from pathlib import Path
from typing import Optional
import pandas as pd
import re
from sklearn.metrics import mean_absolute_error
from codecarbon import track_emissions

# Allow importing from src/puma package
_src_root = str(Path(__file__).parent.parent)
if _src_root not in sys.path:
    sys.path.insert(0, _src_root)

from history import save_to_history, get_ollama_model_info

# Re-export from new module location for forward compatibility
from puma.scenarios.estimation_tawos import (  # noqa: F401
    parse_story_points,
    EstimationEvaluator,
    calculate_metrics,
    FIBONACCI_SERIES,
    FEW_SHOT_EXAMPLES,
    DETERMINISTIC_OPTIONS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
TAWOS_INPUT = DATA_DIR / "tawos_clean.csv"
CACHE_FILE = RESULTS_DIR / "estimation_cache.json"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("LLM_MODEL", "qwen2.5:3b")

# Estimation evaluation configuration
# Target MAE score (original requirement: 3.0)
ESTIMATION_TARGET_MAE = float(os.environ.get("ESTIMATION_TARGET_MAE", "3.0"))
# Project to evaluate (MESOS, APSTUD, XD)
ESTIMATION_PROJECT = os.environ.get("ESTIMATION_PROJECT", "MESOS")
# Temperature for LLM (0.0 = deterministic)
ESTIMATION_TEMPERATURE = float(os.environ.get("ESTIMATION_TEMPERATURE", "0.0"))
# Random seed for reproducibility
ESTIMATION_SEED = int(os.environ.get("ESTIMATION_SEED", "42"))
# Maximum number of items to evaluate (0 = all items)
ESTIMATION_NUM_ITEMS = int(os.environ.get("ESTIMATION_NUM_ITEMS", "0"))
# Evaluation timeout in seconds (0 = no timeout)
EVALUATION_TIMEOUT = int(os.environ.get("EVALUATION_TIMEOUT", "0"))

DETERMINISTIC_OPTIONS = {
    "temperature": ESTIMATION_TEMPERATURE,
    "seed": ESTIMATION_SEED,
    "num_predict": 50
}

FIBONACCI_SERIES = [1, 2, 3, 5, 8, 13, 21]

FEW_SHOT_EXAMPLES = [
    {
        "title": "Fix typo in login button label",
        "description": "The login button text says 'Subit' instead of 'Submit'. This is a minor cosmetic issue.",
        "story_points": 1
    },
    {
        "title": "Implement user session timeout",
        "description": "Users are logged out after 30 minutes of inactivity. Need to add session management and redirect to login page. Include unit tests for session validation.",
        "story_points": 5
    },
    {
        "title": "Design and implement microservices architecture",
        "description": "Migrate monolithic application to microservices. Include API gateway, service discovery, load balancing, and database sharding. Must maintain backward compatibility during transition.",
        "story_points": 21
    }
]

SYSTEM_PROMPT = (
    "Eres un experto en estimación de esfuerzo ágil. "
    "Analiza el título y descripción de la historia de usuario. "
    "Responde ÚNICAMENTE con un número entero o decimal que represente los Story Points. "
    "Los Story Points siguen la serie de Fibonacci modificada: 1, 2, 3, 5, 8, 13, 21. "
    "No añadas ninguna explicación, texto adicional ni puntuación."
)


def build_few_shot_prompt(title: str, description: str) -> str:
    examples_text = ""
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"\nEjemplo {i}:\nTítulo: {ex['title']}\nDescripción: {ex['description']}\nStory Points: {ex['story_points']}"
    
    prompt = f"{examples_text}\n\nAhora estima este caso:\nTítulo: {title}\nDescripción: {description}\nStory Points:"
    return prompt


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


def parse_story_points(response: str) -> Optional[float]:
    response_clean = response.strip().strip('.').strip(',').strip()
    
    numbers = re.findall(r'\d+\.?\d*', response_clean)
    
    if not numbers:
        logger.warning(f"Could not parse story points from: '{response}'")
        return None
    
    try:
        value = float(numbers[0])
        
        if value in FIBONACCI_SERIES:
            return value
        
        closest = min(FIBONACCI_SERIES, key=lambda x: abs(x - value))
        
        if abs(closest - value) <= 1:
            logger.debug(f"Parsed {value} -> rounded to closest Fibonacci: {closest}")
            return closest
        
        return value
        
    except ValueError:
        logger.warning(f"Could not convert to float: '{numbers[0]}'")
        return None


class EstimationEvaluator:
    def __init__(self, model: str = MODEL_NAME, timeout: int = 0):
        import ollama
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = model
        self.timeout = timeout
        self.start_time = time.time()
        self._shutdown_requested = False
        
        # Registrar handler para señales de shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"EstimationEvaluator initialized with model: {model}")
        logger.info(f"Timeout configured: {timeout if timeout > 0 else 'none'} seconds")
    
    def _signal_handler(self, signum, frame):
        logger.info("Shutdown signal received, finishing current item...")
        self._shutdown_requested = True
    
    def _check_timeout(self) -> bool:
        if self.timeout > 0:
            elapsed = time.time() - self.start_time
            if elapsed >= self.timeout:
                logger.info(f"Timeout reached after {elapsed:.0f} seconds")
                return True
        return False
    
    def evaluate_item(self, item_id: str, title: str, description: str) -> Optional[float]:
        if self._shutdown_requested:
            return None
            
        if self._check_timeout():
            return None
            
        user_prompt = build_few_shot_prompt(title, description)
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                options=DETERMINISTIC_OPTIONS
            )
            
            story_points = parse_story_points(response["message"]["content"])
            logger.debug(f"Item {item_id}: {story_points}")
            return story_points
            
        except Exception as e:
            logger.error(f"Error evaluating item {item_id}: {e}")
            return None
    
    def evaluate_batch(self, df: pd.DataFrame, project_filter: str = None, max_items: int = 0) -> list:
        cache = load_cache()
        
        if project_filter:
            df = df[df.get('project', 'Unknown') == project_filter].copy()
            logger.info(f"Filtered to project: {project_filter} ({len(df)} items)")
        
        # Aplicar límite de items si está configurado
        original_count = len(df)
        if max_items > 0 and len(df) > max_items:
            df = df.head(max_items)
            logger.info(f"Limited to {max_items} items (from {original_count} available)")
        else:
            logger.info(f"Processing all {len(df)} items")
        
        results = []
        skipped = 0
        processed = 0
        cache_hits = 0
        
        for idx, row in df.iterrows():
            if self._shutdown_requested:
                logger.info("Shutdown requested, stopping evaluation")
                break
            
            if self._check_timeout():
                logger.info("Timeout reached, stopping evaluation")
                break
            
            item_id = str(row.get("item_id", f"item_{idx}"))
            
            if item_id in cache:
                cached = cache[item_id]
                if "prediction" in cached and cached["prediction"] is not None:
                    logger.debug(f"Using cached result for: {item_id}")
                    skipped += 1
                    cache_hits += 1
                    results.append({
                        "item_id": item_id,
                        "title": row.get("title", ""),
                        "description": row.get("description", ""),
                        "story_points": cached.get("story_points", row.get("story_points", 0)),
                        "prediction": cached["prediction"]
                    })
                    continue
            
            title = row.get("title", "")
            description = row.get("description", "")
            true_sp = row.get("story_points", 0)
            
            prediction = self.evaluate_item(item_id, title, description)
            
            if prediction is None and self._shutdown_requested:
                break
            
            result = {
                "item_id": item_id,
                "title": title,
                "description": description,
                "story_points": true_sp,
                "prediction": prediction
            }
            
            cache[item_id] = {"story_points": true_sp, "prediction": prediction}
            results.append(result)
            processed += 1
            
            if processed % 10 == 0:
                save_cache(cache)
                elapsed = time.time() - self.start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(df) - processed - skipped) / rate if rate > 0 else 0
                logger.info(f"Processed {processed} items, {skipped} cached, {cache_hits} cache hits. ETA: {eta/60:.1f} min")
        
        save_cache(cache)
        logger.info(f"Batch complete: {processed} new, {skipped} cached (resume)")
        
        return results


def calculate_metrics(results: list) -> dict:
    y_true = []
    y_pred = []
    errors = []
    
    for r in results:
        if r["story_points"] is not None and r["prediction"] is not None:
            y_true.append(r["story_points"])
            y_pred.append(r["prediction"])
            errors.append(abs(r["story_points"] - r["prediction"]))
    
    if not y_true:
        logger.error("No valid predictions to calculate metrics")
        return {}
    
    mae = mean_absolute_error(y_true, y_pred)
    mdae = sorted(errors)[len(errors) // 2]
    
    metrics = {
        "mae": mae,
        "mdae": mdae,
        "total_samples": len(y_true),
        "valid_predictions": len(y_pred),
        "model": MODEL_NAME,
        "options": DETERMINISTIC_OPTIONS,
        "few_shot_examples": len(FEW_SHOT_EXAMPLES)
    }
    
    return metrics


@track_emissions(project_name="puma_estimation")
def run_evaluation(project: str = "MESOS"):
    logger.info("=" * 60)
    logger.info("Starting Estimation Evaluation (Phase 4)")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Project: {project}")
    logger.info(f"Ollama Host: {OLLAMA_HOST}")
    logger.info(f"Max items: {ESTIMATION_NUM_ITEMS if ESTIMATION_NUM_ITEMS > 0 else 'all'}")
    logger.info(f"Timeout: {EVALUATION_TIMEOUT if EVALUATION_TIMEOUT > 0 else 'none'}")
    logger.info("=" * 60)
    
    if not TAWOS_INPUT.exists():
        logger.error(f"Input file not found: {TAWOS_INPUT}")
        logger.info("Run 'python src/data_prep.py' first to generate the dataset")
        return
    
    df = pd.read_csv(TAWOS_INPUT)
    logger.info(f"Loaded {len(df)} items from {TAWOS_INPUT}")
    
    # Contar items ya procesados en cache
    cache = load_cache()
    cache_count = sum(1 for k, v in cache.items() if v.get("prediction") is not None)
    logger.info(f"Cache contains {cache_count} previously evaluated items")
    
    evaluator = EstimationEvaluator(timeout=EVALUATION_TIMEOUT)
    
    results = evaluator.evaluate_batch(df, project_filter=project, max_items=ESTIMATION_NUM_ITEMS)
    
    if not results:
        logger.warning("No results generated (timeout or shutdown)")
        return None
    
    metrics = calculate_metrics(results)
    
    logger.info("=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    mae = metrics.get('mae')
    mdae = metrics.get('mdae')
    if mae is not None:
        logger.info(f"MAE: {mae:.4f}")
        logger.info(f"MdAE: {mdae:.4f}")
    else:
        logger.info("MAE: N/A (no valid predictions)")
        logger.info("MdAE: N/A")
    logger.info(f"Valid predictions: {metrics.get('valid_predictions', 0)}/{metrics.get('total_samples', 0)}")
    
    target = ESTIMATION_TARGET_MAE
    if mae is not None:
        status = "PASSED" if mae <= target else "ABOVE TARGET"
        logger.info(f"\nTarget: MAE <= {target}")
        logger.info(f"Status: {status}")

        model_info = get_ollama_model_info(OLLAMA_HOST)
        save_to_history(
            task_type="estimation",
            model_name=model_info.get("model_name", MODEL_NAME),
            model_size_gb=model_info.get("model_size_gb"),
            metric_name="mae",
            metric_value=mae,
            target_value=target,
            status=status
        )
    else:
        logger.info(f"\nTarget: MAE <= {target}")
        logger.info(f"Status: INCOMPLETE (timeout or no valid predictions)")
    
    metrics_file = RESULTS_DIR / "estimation_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Metrics saved to {metrics_file}")
    
    return metrics


if __name__ == "__main__":
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else ESTIMATION_PROJECT
    run_evaluation(project)
