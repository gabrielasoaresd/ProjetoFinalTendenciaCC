from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compgraph.config import settings
from compgraph.embeddings import make_embedder
from compgraph.extraction import DomainExtractor
from compgraph.pipeline import make_store
from compgraph.retrieval import HybridRetriever


def reciprocal_rank(expected: set[str], ranked: list[str]) -> float:
    for index, item in enumerate(ranked, start=1):
        if item in expected:
            return 1.0 / index
    return 0.0


def main() -> None:
    questions = json.loads((ROOT / "data/evaluation_questions.json").read_text(encoding="utf-8"))
    embedder = make_embedder(settings.embedding_provider, settings.embedding_dimensions,
                             settings.sentence_transformer_model)
    extractor = DomainExtractor()
    store = make_store()
    rows = []
    try:
        store.verify()
        retriever = HybridRetriever(store, embedder, extractor, settings.top_k_documents,
                                    settings.max_graph_hops, settings.min_confidence)
        for case in questions:
            result = retriever.retrieve(case["question"])
            expected_docs = set(case["expected_doc_ids"])
            retrieved = [doc["doc_id"] for doc in result["documents"]]
            retrieved_entities = {node["id"] for node in result["graph_nodes"]}
            expected_entities = set(case["expected_entities"])
            expected_relations = set(case["expected_relations"])
            relation_types = {edge.get("type") for edge in result["graph_edges"]}
            rows.append({
                "id": case["id"], "question": case["question"],
                "hit_at_k": int(bool(expected_docs.intersection(retrieved))),
                "mrr": reciprocal_rank(expected_docs, retrieved),
                "entity_recall": len(expected_entities.intersection(retrieved_entities)) / max(1, len(expected_entities)),
                "relation_recall": len(expected_relations.intersection(relation_types)) / max(1, len(expected_relations)) if expected_relations else "NA",
                "documents_retrieved": "|".join(retrieved),
                "confidence_score": result["confidence"]["score"],
                "graph_edges": len(result["graph_edges"]),
            })
    finally:
        store.close()
    output = ROOT / "artifacts/evaluation_results.csv"
    output.parent.mkdir(exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Avaliação concluída: {output}")
    print(f"Hit@K médio: {sum(row['hit_at_k'] for row in rows) / len(rows):.3f}")
    print(f"MRR médio: {sum(row['mrr'] for row in rows) / len(rows):.3f}")
    print("Observação: as questões e rótulos de referência estão em data/evaluation_questions.json.")


if __name__ == "__main__":
    main()
