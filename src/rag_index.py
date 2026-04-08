"""
RAG Indexer - Indexa datos y specs para Context Engineering
Uso opcional: docker exec puma_evaluator python src/rag_index.py
"""

import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
SPECS_DIR = Path("specs")


def index_data():
    """Indexa archivos de datos"""
    logger.info("Indexing data directory...")
    
    indexed = []
    for ext in ["*.csv", "*.json"]:
        for file in DATA_DIR.glob(ext):
            indexed.append(str(file))
            logger.info(f"  Indexed: {file.name}")
    
    return indexed


def index_specs():
    """Indexa archivos de especificaciones"""
    logger.info("Indexing specs directory...")
    
    indexed = []
    for ext in ["*.md", "*.spec.md", "*.json"]:
        for file in SPECS_DIR.rglob(ext):
            indexed.append(str(file))
            logger.info(f"  Indexed: {file.relative_to(SPECS_DIR)}")
    
    return indexed


def create_index():
    """Crea índice RAG (placeholder)"""
    logger.info("=" * 50)
    logger.info("PUMA RAG Indexer")
    logger.info("=" * 50)
    
    data_files = index_data()
    specs_files = index_specs()
    
    logger.info("")
    logger.info(f"Total indexed: {len(data_files) + len(specs_files)} files")
    logger.info(f"  - Data: {len(data_files)} files")
    logger.info(f"  - Specs: {len(specs_files)} files")
    logger.info("")
    logger.info("Note: ChromaDB integration requires additional dependencies")
    logger.info("      Install: pip install chromadb langchain-ollama")
    
    return {
        "data_files": data_files,
        "specs_files": specs_files,
        "total": len(data_files) + len(specs_files)
    }


def main():
    result = create_index()
    logger.info("Index created successfully!")


if __name__ == "__main__":
    main()