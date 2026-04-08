import os
import json
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.metrics import confusion_matrix, f1_score, classification_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path("results")
REPORTS_DIR = Path("reports")
FIGURES_DIR = REPORTS_DIR / "figures"

TRIAGE_CACHE = RESULTS_DIR / "triage_cache.json"
ESTIMATION_CACHE = RESULTS_DIR / "estimation_cache.json"
TRIAGE_METRICS = RESULTS_DIR / "triage_metrics.json"
ESTIMATION_METRICS = RESULTS_DIR / "estimation_metrics.json"


def ensure_directories():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_triage() -> dict:
    logger.info("=" * 60)
    logger.info("Analyzing Triage Results")
    logger.info("=" * 60)
    
    cache = load_json(TRIAGE_CACHE)
    metrics = load_json(TRIAGE_METRICS)
    
    if not cache:
        logger.warning("No triage cache found. Run evaluate_triage.py first.")
        return {}
    
    results = list(cache.values())
    
    y_true = []
    y_pred = []
    
    for r in results:
        if r.get("priority") and r.get("prediction"):
            y_true.append(r["priority"])
            y_pred.append(r["prediction"])
    
    if not y_true:
        logger.error("No valid triage predictions found")
        return {}
    
    labels = ["Critical", "Major", "Minor", "Trivial"]
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    f1_macro = f1_score(y_true, y_pred, labels=labels, average="macro")
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True)
    
    stats_triage = {
        "f1_macro": f1_macro,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
        "per_class": {}
    }
    
    for label in labels:
        if label in report:
            stats_triage["per_class"][label] = {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": report[label]["support"]
            }
    
    logger.info(f"F1-Macro: {f1_macro:.4f}")
    logger.info("Per-class metrics:")
    for label, m in stats_triage["per_class"].items():
        logger.info(f"  {label:10} - P: {m['precision']:.3f}, R: {m['recall']:.3f}, F1: {m['f1']:.3f}")
    
    return stats_triage


def analyze_estimation() -> dict:
    logger.info("=" * 60)
    logger.info("Analyzing Estimation Results")
    logger.info("=" * 60)
    
    cache = load_json(ESTIMATION_CACHE)
    metrics = load_json(ESTIMATION_METRICS)
    
    if not cache:
        logger.warning("No estimation cache found. Run evaluate_estimation.py first.")
        return {}
    
    results = list(cache.values())
    
    y_true = []
    y_pred = []
    
    for r in results:
        if r.get("story_points") is not None and r.get("prediction") is not None:
            y_true.append(r["story_points"])
            y_pred.append(r["prediction"])
    
    if not y_true:
        logger.error("No valid estimation predictions found")
        return {}
    
    errors = [abs(t - p) for t, p in zip(y_true, y_pred)]
    mae = np.mean(errors)
    mdae = np.median(errors)
    rmse = np.sqrt(np.mean([e**2 for e in errors]))
    
    stats_estimation = {
        "mae": mae,
        "mdae": mdae,
        "rmse": rmse,
        "mean_true": np.mean(y_true),
        "mean_pred": np.mean(y_pred),
        "std_true": np.std(y_true),
        "std_pred": np.std(y_pred),
        "sample_size": len(y_true)
    }
    
    logger.info(f"MAE: {mae:.4f}")
    logger.info(f"MdAE: {mdae:.4f}")
    logger.info(f"RMSE: {rmse:.4f}")
    logger.info(f"Mean True: {np.mean(y_true):.2f}, Mean Pred: {np.mean(y_pred):.2f}")
    
    return stats_estimation


def wilcoxon_test() -> Optional[dict]:
    logger.info("=" * 60)
    logger.info("Wilcoxon Signed-Rank Test")
    logger.info("=" * 60)
    
    cache = load_json(ESTIMATION_CACHE)
    
    if not cache:
        logger.warning("No estimation data for Wilcoxon test")
        return None
    
    results = list(cache.values())
    
    y_true = []
    y_pred = []
    
    for r in results:
        if r.get("story_points") is not None and r.get("prediction") is not None:
            y_true.append(r["story_points"])
            y_pred.append(r["prediction"])
    
    if len(y_true) < 10:
        logger.warning("Insufficient samples for Wilcoxon test")
        return None
    
    try:
        stat, p_value = stats.wilcoxon(y_true, y_pred, alternative='two-sided')
        
        wilcoxon_result = {
            "statistic": float(stat),
            "p_value": float(p_value),
            "n_samples": len(y_true),
            "significant": p_value < 0.05
        }
        
        logger.info(f"Statistic: {stat:.4f}")
        logger.info(f"P-value: {p_value:.4f}")
        logger.info(f"Significant at α=0.05: {wilcoxon_result['significant']}")
        
        return wilcoxon_result
        
    except Exception as e:
        logger.error(f"Wilcoxon test failed: {e}")
        return None


def plot_f1_comparison(stats_triage: dict):
    logger.info("Generating F1-Macro comparison chart...")
    
    if not stats_triage.get("per_class"):
        logger.warning("No triage stats to plot")
        return
    
    classes = list(stats_triage["per_class"].keys())
    f1_scores = [stats_triage["per_class"][c]["f1"] for c in classes]
    
    plt.figure(figsize=(10, 6))
    
    colors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71']
    bars = plt.bar(classes, f1_scores, color=colors, edgecolor='black', linewidth=1.2)
    
    plt.axhline(y=0.55, color='red', linestyle='--', linewidth=2, label='Target (0.55)')
    plt.axhline(y=stats_triage["f1_macro"], color='blue', linestyle='-', linewidth=2, 
                label=f'F1-Macro ({stats_triage["f1_macro"]:.3f})')
    
    for bar, score in zip(bars, f1_scores):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'{score:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.xlabel('Priority Class', fontsize=12)
    plt.ylabel('F1-Score', fontsize=12)
    plt.title('Triage Classification - F1-Score by Priority Class', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.ylim(0, 1.0)
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = FIGURES_DIR / "f1_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved to {output_path}")


def plot_mae_comparison(stats_estimation: dict):
    logger.info("Generating MAE comparison chart...")
    
    if not stats_estimation:
        logger.warning("No estimation stats to plot")
        return
    
    metrics = ['MAE', 'MdAE', 'RMSE']
    values = [stats_estimation.get('mae', 0), 
              stats_estimation.get('mdae', 0), 
              stats_estimation.get('rmse', 0)]
    
    plt.figure(figsize=(8, 6))
    
    colors = ['#3498db', '#2ecc71', '#9b59b6']
    bars = plt.bar(metrics, values, color=colors, edgecolor='black', linewidth=1.2)
    
    plt.axhline(y=3.0, color='red', linestyle='--', linewidth=2, label='Target (3.0)')
    
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                f'{val:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.xlabel('Metric', fontsize=12)
    plt.ylabel('Error Value', fontsize=12)
    plt.title('Estimation - Error Metrics', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.ylim(0, max(values) * 1.3)
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = FIGURES_DIR / "mae_comparison.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved to {output_path}")


def plot_confusion_matrix(stats_triage: dict):
    logger.info("Generating confusion matrix heatmap...")
    
    if not stats_triage.get("confusion_matrix"):
        logger.warning("No confusion matrix to plot")
        return
    
    cm = np.array(stats_triage["confusion_matrix"])
    labels = stats_triage.get("labels", ["Critical", "Major", "Minor", "Trivial"])
    
    plt.figure(figsize=(8, 6))
    
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=labels, yticklabels=labels,
                cbar_kws={'label': 'Count'})
    
    plt.xlabel('Predicted', fontsize=12)
    plt.ylabel('Actual', fontsize=12)
    plt.title('Triage - Confusion Matrix', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    output_path = FIGURES_DIR / "confusion_matrix.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved to {output_path}")


def generate_summary_report(stats_triage: dict, stats_estimation: dict, wilcoxon: dict):
    logger.info("=" * 60)
    logger.info("FINAL SUMMARY REPORT")
    logger.info("=" * 60)
    
    report = {
        "triage": stats_triage,
        "estimation": stats_estimation,
        "wilcoxon_test": wilcoxon
    }
    
    report_file = REPORTS_DIR / "summary_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Report saved to {report_file}")
    
    logger.info("\n" + "=" * 60)
    logger.info("TRIAGE RESULTS")
    logger.info("=" * 60)
    f1_macro = stats_triage.get('f1_macro') if stats_triage else None
    if f1_macro is not None and isinstance(f1_macro, (int, float)):
        logger.info(f"F1-Macro: {f1_macro:.4f}")
        logger.info(f"Target: >= 0.55")
        logger.info(f"Status: {'PASSED' if f1_macro >= 0.55 else 'FAILED'}")
    else:
        logger.info("F1-Macro: N/A (no valid predictions)")
    
    logger.info("\n" + "=" * 60)
    logger.info("ESTIMATION RESULTS")
    logger.info("=" * 60)
    mae = stats_estimation.get('mae') if stats_estimation else None
    if mae is not None and isinstance(mae, (int, float)):
        logger.info(f"MAE: {mae:.4f}")
        mdae = stats_estimation.get('mdae')
        if mdae is not None and isinstance(mdae, (int, float)):
            logger.info(f"MdAE: {mdae:.4f}")
        logger.info(f"Target: <= 3.0")
        logger.info(f"Status: {'PASSED' if mae <= 3.0 else 'FAILED'}")
    else:
        logger.info("MAE: N/A (no valid predictions)")
    
    if wilcoxon:
        p_value = wilcoxon.get('p_value')
        logger.info("\n" + "=" * 60)
        logger.info("WILCOXON TEST")
        logger.info("=" * 60)
        if p_value is not None and isinstance(p_value, (int, float)):
            logger.info(f"P-value: {p_value:.4f}")
        else:
            logger.info(f"P-value: {p_value}")
        logger.info(f"Significant: {wilcoxon.get('significant', 'N/A')}")
    
    return report


def main():
    logger.info("Starting Statistical Analysis (Phase 5)")
    
    ensure_directories()
    
    stats_triage = analyze_triage()
    stats_estimation = analyze_estimation()
    wilcoxon = wilcoxon_test()
    
    if stats_triage:
        plot_f1_comparison(stats_triage)
        plot_confusion_matrix(stats_triage)
    
    if stats_estimation:
        plot_mae_comparison(stats_estimation)
    
    report = generate_summary_report(stats_triage, stats_estimation, wilcoxon)
    
    logger.info("=" * 60)
    logger.info("Statistical Analysis Complete")
    logger.info(f"Figures saved to: {FIGURES_DIR}")
    logger.info("=" * 60)
    
    return report


if __name__ == "__main__":
    main()
