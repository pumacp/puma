"""
PUMA Agentic Orchestrator
Coordina el flujo de trabajo entre agentes usando LangGraph
"""

import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orquestador de agentes para PUMA"""
    
    def __init__(self, model: str = "qwen2.5:3b"):
        self.model = model
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        logger.info(f"Orchestrator initialized with model: {model}")
    
    def load_spec(self, spec_name: str) -> dict:
        """Carga especificación desde specs/"""
        spec_path = Path(f"specs/{spec_name}.spec.md")
        if spec_path.exists():
            logger.info(f"Loaded spec: {spec_name}")
            return {"status": "loaded", "spec": spec_name}
        logger.warning(f"Spec not found: {spec_name}")
        return {"status": "not_found", "spec": spec_name}
    
    def run_agent(self, agent_name: str, input_data: dict) -> dict:
        """Ejecuta un agente específico"""
        logger.info(f"Running agent: {agent_name}")
        
        if agent_name == "triage":
            return self._run_triage_agent(input_data)
        elif agent_name == "estimation":
            return self._run_estimation_agent(input_data)
        else:
            return {"status": "error", "message": f"Unknown agent: {agent_name}"}
    
    def _run_triage_agent(self, input_data: dict) -> dict:
        """Ejecuta el agente de triage"""
        logger.info("Triage Agent execution (delegated to evaluate_triage.py)")
        return {"status": "delegated", "to": "src/evaluate_triage.py"}
    
    def _run_estimation_agent(self, input_data: dict) -> dict:
        """Ejecuta el agente de estimación"""
        logger.info("Estimation Agent execution (delegated to evaluate_estimation.py)")
        return {"status": "delegated", "to": "src/evaluate_estimation.py"}
    
    def run_workflow(self, spec_name: str, input_data: dict) -> dict:
        """Ejecuta el flujo completo: Spec → Generate → Test → Review → Deploy"""
        logger.info(f"Starting workflow for: {spec_name}")
        
        result = self.load_spec(spec_name)
        if result["status"] == "not_found":
            return result
        
        agent_result = self.run_agent(spec_name, input_data)
        
        return {
            "workflow": "completed",
            "spec": spec_name,
            "agent_result": agent_result
        }


def main():
    import sys
    
    spec = sys.argv[1] if len(sys.argv) > 1 else "triage"
    
    orchestrator = Orchestrator()
    result = orchestrator.run_workflow(spec, {})
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()