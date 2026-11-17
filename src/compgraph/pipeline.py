from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR, settings
from .embeddings import make_embedder
from .extraction import DomainExtractor
from .neo4j_store import Neo4jStore


def load_corpus(path: Path | None = None) -> list[dict[str, Any]]:
    corpus_path = path or (DATA_DIR / "corpus.jsonl")
    documents = []
    with corpus_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido em {corpus_path}:{line_number}: {exc}") from exc
            required = {"doc_id", "title", "content", "source"}
            missing = required - document.keys()
            if missing:
                raise ValueError(f"Campos ausentes em {corpus_path}:{line_number}: {sorted(missing)}")
            documents.append(document)
    return documents


def prepare_documents(documents: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    extractor = DomainExtractor()
    raw_documents = documents if documents is not None else load_corpus()
    return [extractor.extract_document(document) for document in raw_documents]


def make_store() -> Neo4jStore:
    return Neo4jStore(settings.neo4j_uri, settings.neo4j_user,
                      settings.neo4j_password, settings.neo4j_database,
                      settings.embedding_dimensions)


def run_ingestion() -> dict[str, int]:
    embedder = make_embedder(settings.embedding_provider, settings.embedding_dimensions,
                             settings.sentence_transformer_model)
    documents = prepare_documents()
    store = make_store()
    try:
        store.verify()
        store.ensure_schema()
        return store.ingest(documents, embedder)
    finally:
        store.close()
