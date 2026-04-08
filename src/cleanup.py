import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path("results")
REPORTS_DIR = Path("reports")


def cleanup_results():
    logger.info("==========================================")
    logger.info("  PUMA Benchmark - Reset Results")
    logger.info("==========================================")
    logger.info("")

    if not RESULTS_DIR.exists():
        logger.warning(f"Results directory not found: {RESULTS_DIR}")
        return

    logger.info("Cleaning results directory...")

    cleaned = 0
    
    for ext in ["*.json", "*.csv"]:
        for file in RESULTS_DIR.glob(ext):
            try:
                file.unlink()
                cleaned += 1
                logger.info(f"  Removed: {file.name}")
            except Exception as e:
                logger.warning(f"  Could not remove {file.name}: {e}")

    if (REPORTS_DIR / "figures").exists():
        for ext in ["*.png", "*.pdf"]:
            for file in REPORTS_DIR.glob(ext):
                try:
                    file.unlink()
                    cleaned += 1
                    logger.info(f"  Removed: reports/{file.name}")
                except Exception as e:
                    logger.warning(f"  Could not remove reports/{file.name}: {e}")

    logger.info("")
    logger.info("==========================================")
    logger.info(f"  Results cleaned: {cleaned} files removed")
    logger.info("==========================================")
    logger.info("")
    logger.info("You can now run fresh benchmarks:")
    logger.info("  - docker exec puma_evaluator python src/evaluate_triage.py")
    logger.info("  - docker exec puma_evaluator python src/evaluate_estimation.py")


if __name__ == "__main__":
    cleanup_results()