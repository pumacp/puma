"""
Code Generator Agent - Genera código desde especificaciones .spec.md
"""

import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeGeneratorAgent:
    """Agente que genera código desde especificaciones SDD"""
    
    def __init__(self, model: str = "qwen2.5:3b"):
        self.model = model
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        logger.info(f"CodeGeneratorAgent initialized with model: {model}")
    
    def read_spec(self, spec_path: str) -> str:
        """Lee una especificación .spec.md"""
        path = Path(spec_path)
        if path.exists():
            return path.read_text()
        return ""
    
    def generate_code(self, spec_name: str) -> dict:
        """
        Genera código desde una especificación
        Por ahora, delega a los scripts existentes
        """
        logger.info(f"Generating code for spec: {spec_name}")
        
        spec_file = f"specs/{spec_name}.spec.md"
        spec_content = self.read_spec(spec_file)
        
        if not spec_content:
            return {"status": "error", "message": f"Spec not found: {spec_name}"}
        
        return {
            "status": "generated",
            "spec": spec_name,
            "delegated_to": f"src/evaluate_{spec_name}.py",
            "code": "Use existing implementation"
        }
    
    def generate_from_prompt(self, prompt: str, context: dict = None) -> str:
        """Genera código desde un prompt libre"""
        logger.info("Generating code from prompt")
        return "# Code generation delegated to existing implementation"


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python code_generator_agent.py <spec_name>")
        sys.exit(1)
    
    spec_name = sys.argv[1]
    agent = CodeGeneratorAgent()
    result = agent.generate_code(spec_name)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()