from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional for tests
    pass

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "compgraph_password")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "hash").lower()
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
    sentence_transformer_model: str = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "none").lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    top_k_documents: int = int(os.getenv("TOP_K_DOCUMENTS", "5"))
    max_graph_hops: int = int(os.getenv("MAX_GRAPH_HOPS", "2"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.18"))


settings = Settings()
