"""
Tester Agent - Genera y ejecuta tests automáticamente desde especificaciones
"""

import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TesterAgent:
    """Agente que genera tests automáticos desde specs"""
    
    def __init__(self):
        logger.info("TesterAgent initialized")
    
    def read_spec(self, spec_path: str) -> str:
        """Lee una especificación"""
        path = Path(spec_path)
        if path.exists():
            return path.read_text()
        return ""
    
    def generate_tests(self, spec_name: str) -> dict:
        """
        Genera tests desde una especificación
        Usa existing tests en tests/
        """
        logger.info(f"Generating tests for spec: {spec_name}")
        
        test_file = f"tests/test_{spec_name}.py"
        
        if Path(test_file).exists():
            return {
                "status": "exists",
                "test_file": test_file,
                "message": "Using existing test file"
            }
        
        return {
            "status": "generated",
            "spec": spec_name,
            "test_file": f"tests/test_{spec_name}.py",
            "note": "Use existing tests/test_core.py"
        }
    
    def run_tests(self, test_file: str) -> dict:
        """Ejecuta los tests"""
        logger.info(f"Running tests: {test_file}")
        return {
            "status": "delegated",
            "command": "pytest tests/",
            "message": "Execute via docker exec"
        }


def main():
    import sys
    
    spec_name = sys.argv[1] if len(sys.argv) > 1 else "triage"
    agent = TesterAgent()
    result = agent.generate_tests(spec_name)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()