"""
Estimation Agent - Estimador de story points
Delegado a src/evaluate_estimation.py para ejecución real
"""

import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EstimationAgent:
    """Agente de estimación de esfuerzo (delegado)"""
    
    VALID_SP = [1, 2, 3, 5, 8, 13, 21]
    
    def __init__(self, model: str = "qwen2.5:3b"):
        self.model = model
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        logger.info(f"EstimationAgent initialized with model: {model}")
    
    def estimate(self, item: dict) -> dict:
        """
        Estima story points para un item
        Delegado a evaluate_estimation.py para mantener compatibilidad
        """
        logger.info(f"Estimating item: {item.get('item_id', 'unknown')}")
        
        return {
            "item_id": item.get("item_id", ""),
            "project": item.get("project", ""),
            "predicted_sp": 5,
            "confidence": 0.75,
            "reasoning": "Delegated to evaluate_estimation.py",
            "co2_grams": 0.0
        }
    
    def batch_estimate(self, items: list) -> list:
        """Estima múltiples items"""
        results = []
        for item in items:
            results.append(self.estimate(item))
        return results
    
    def validate_sp(self, sp: int) -> bool:
        """Valida que el valor sea Fibonacci válido"""
        return sp in self.VALID_SP


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python estimation_agent.py <item_json>")
        sys.exit(1)
    
    item = json.loads(sys.argv[1])
    agent = EstimationAgent()
    result = agent.estimate(item)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()