from __future__ import annotations

import math
import re
from typing import Any

import networkx as nx

from .embeddings import Embedder
from .extraction import DomainExtractor
from .neo4j_store import Neo4jStore


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Combina listas ranqueadas sem comparar diretamente scores heterogêneos."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (k + rank)
    return dict(sorted(fused.items(), key=lambda item: item[1], reverse=True))


def lexical_terms(text: str) -> list[str]:
    stopwords = {"como", "qual", "quais", "que", "para", "com", "uma", "dos", "das", "por", "sobre", "entre", "the", "and"}
    return [term for term in re.findall(r"[\w-]+", text.lower(), flags=re.UNICODE) if len(term) > 2 and term not in stopwords]


def safe_lucene_query(text: str) -> str:
    terms = lexical_terms(text)
    # Apenas termos alfanuméricos escapados são inseridos na sintaxe Lucene.
    return " OR ".join('"' + term.replace('"', '') + '"' for term in terms[:12])


def heuristic_confidence(documents: list[dict[str, Any]], triples: list[dict[str, Any]],
                         query: str, min_confidence: float = 0.18) -> dict[str, Any]:
    """Índice heurístico de apoio, não uma probabilidade estatisticamente calibrada."""
    if not documents:
        return {"score": 0.0, "label": "Insuficiente", "supported": False,
                "explanation": "Nenhum documento foi recuperado."}
    q_terms = set(lexical_terms(query))
    content = " ".join((doc.get("title", "") + " " + doc.get("content", "")) for doc in documents).lower()
    coverage = len([t for t in q_terms if t in content]) / max(1, len(q_terms))
    source_factor = min(1.0, len({d.get("doc_id") for d in documents}) / 3.0)
    graph_factor = min(1.0, len(triples) / 3.0)
    score = min(1.0, 0.50 * coverage + 0.25 * source_factor + 0.25 * graph_factor)
    supported = score >= min_confidence and (coverage >= 0.15 or bool(triples))
    label = "Alta" if score >= 0.68 else "Moderada" if score >= 0.40 else "Baixa" if supported else "Insuficiente"
    return {
        "score": round(score, 3), "label": label, "supported": supported,
        "explanation": (
            f"Cobertura lexical={coverage:.2f}; fontes recuperadas={len(documents)}; "
            f"relações rastreáveis={len(triples)}. Índice heurístico, não probabilidade calibrada."
        ),
    }


def compile_graph_cypher(mode: str = "neighborhood", max_hops: int = 2) -> str:
    """Compila somente dois formatos de consulta permitidos (read-only e parametrizados)."""
    hops = max(1, min(int(max_hops), 3))
    if mode == "shortest_path":
        return """
        MATCH p = shortestPath((a:Entity {id: $source_id})-[*..5]-(b:Entity {id: $target_id}))
        WHERE ALL(rel IN relationships(p) WHERE rel.doc_id IN $doc_ids)
        RETURN [n IN nodes(p) | {id:n.id, name:n.name, entity_type:n.entity_type}] AS nodes,
               [r IN relationships(p) | {type:type(r), evidence:r.evidence,
                 source_id:startNode(r).id, target_id:endNode(r).id, doc_id:r.doc_id}] AS rels
        LIMIT 5
        """.strip()
    return f"""
    MATCH p = (seed:Entity)-[*1..{hops}]-(target:Entity)
    WHERE seed.id IN $seed_ids
      AND ALL(rel IN relationships(p) WHERE rel.doc_id IN $doc_ids)
    RETURN [n IN nodes(p) | {{id:n.id, name:n.name, entity_type:n.entity_type}}] AS nodes,
           [r IN relationships(p) | {{type:type(r), evidence:r.evidence,
             source_id:startNode(r).id, target_id:endNode(r).id, doc_id:r.doc_id,
             confidence:r.confidence}}] AS rels
    LIMIT 30
    """.strip()


def validate_readonly_cypher(query: str) -> bool:
    """Barreira adicional para exibição/execução de Cypher: bloqueia escrita e múltiplas sentenças."""
    normalized = re.sub(r"/\*.*?\*/|//[^\n]*", " ", query, flags=re.S).strip()
    if not normalized or ";" in normalized:
        return False
    if re.search(r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|ALTER|LOAD\s+CSV|GRANT|DENY|REVOKE|CALL\s+dbms)\b", normalized, re.I):
        return False
    return bool(re.match(r"^(MATCH|OPTIONAL\s+MATCH)\b", normalized, re.I)) and bool(re.search(r"\bRETURN\b", normalized, re.I))


class HybridRetriever:
    def __init__(self, store: Neo4jStore, embedder: Embedder, extractor: DomainExtractor,
                 top_k: int = 5, max_hops: int = 2, min_confidence: float = 0.18):
        self.store = store
        self.embedder = embedder
        self.extractor = extractor
        self.top_k = top_k
        self.max_hops = max_hops
        self.min_confidence = min_confidence

    def _vector_search(self, question: str) -> list[dict[str, Any]]:
        embedding = self.embedder.encode(question)
        rows = self.store.run("""
        CALL db.index.vector.queryNodes('document_embeddings', $k, $embedding)
        YIELD node, score
        RETURN node.doc_id AS doc_id, node.title AS title, node.content AS content,
               node.source AS source, node.source_label AS source_label, score
        ORDER BY score DESC
        """, {"k": self.top_k * 2, "embedding": embedding})
        return rows

    def _fulltext_search(self, question: str) -> list[dict[str, Any]]:
        query = safe_lucene_query(question)
        if not query:
            return []
        rows = self.store.run("""
        CALL db.index.fulltext.queryNodes('document_fulltext', $query)
        YIELD node, score
        RETURN node.doc_id AS doc_id, node.title AS title, node.content AS content,
               node.source AS source, node.source_label AS source_label, score
        ORDER BY score DESC
        LIMIT $k
        """, {"query": query, "k": self.top_k * 2})
        return rows

    def _graph_context(self, question: str, doc_ids: list[str], plan: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
        question_mentions = self.extractor.extract_entities(question)
        seed_ids = list(dict.fromkeys(m.entity_id for m in question_mentions))
        if doc_ids:
            mention_rows = self.store.run("""
            MATCH (d:Document)-[:MENTIONS]->(e:Entity)
            WHERE d.doc_id IN $doc_ids
            RETURN DISTINCT e.id AS id, e.name AS name, e.entity_type AS entity_type
            """, {"doc_ids": doc_ids})
            seed_ids.extend(row["id"] for row in mention_rows)
        seed_ids = list(dict.fromkeys(seed_ids))
        if not seed_ids or not doc_ids:
            return [], [], compile_graph_cypher("neighborhood", self.max_hops), {"seed_ids": seed_ids, "doc_ids": doc_ids}

        mode = (plan or {}).get("mode", "shortest_path" if len(question_mentions) >= 2 else "neighborhood")
        if mode not in {"neighborhood", "shortest_path"}:
            mode = "neighborhood"
        hops = (plan or {}).get("max_hops", self.max_hops)
        query = compile_graph_cypher(mode, hops)
        params: dict[str, Any]
        if mode == "shortest_path" and len(question_mentions) >= 2:
            params = {"source_id": question_mentions[0].entity_id,
                      "target_id": question_mentions[1].entity_id,
                      "doc_ids": doc_ids}
            if not validate_readonly_cypher(query):
                raise ValueError("A consulta gerada não passou na validação read-only.")
            rows = self.store.run(query, params)
            if not rows:
                mode = "neighborhood"
                query = compile_graph_cypher(mode, hops)
                params = {"seed_ids": seed_ids, "doc_ids": doc_ids}
                rows = self.store.run(query, params)
        else:
            mode = "neighborhood"
            query = compile_graph_cypher(mode, hops)
            params = {"seed_ids": seed_ids, "doc_ids": doc_ids}
            if not validate_readonly_cypher(query):
                raise ValueError("A consulta gerada não passou na validação read-only.")
            rows = self.store.run(query, params)

        unique_nodes: dict[str, dict[str, Any]] = {}
        unique_edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for row in rows:
            for node in row.get("nodes", []):
                unique_nodes[node["id"]] = node
            for rel in row.get("rels", []):
                key = (rel.get("source_id", ""), rel.get("type", ""), rel.get("target_id", ""), rel.get("doc_id", ""))
                unique_edges[key] = rel
        nodes = list(unique_nodes.values())
        edges = list(unique_edges.values())
        graph = nx.DiGraph()
        graph.add_nodes_from(node["id"] for node in nodes)
        for edge in edges:
            graph.add_edge(edge.get("source_id"), edge.get("target_id"))
        try:
            ranks = nx.pagerank(graph, alpha=0.85) if graph.number_of_nodes() else {}
        except nx.NetworkXError:
            ranks = {}
        for node in nodes:
            node["pagerank"] = round(float(ranks.get(node["id"], 0.0)), 4)
        nodes.sort(key=lambda n: n.get("pagerank", 0), reverse=True)
        return nodes, edges, query, params

    def retrieve(self, question: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        vector_rows = self._vector_search(question)
        text_rows = self._fulltext_search(question)
        vector_rank = [r["doc_id"] for r in vector_rows]
        text_rank = [r["doc_id"] for r in text_rows]
        fused = reciprocal_rank_fusion([vector_rank, text_rank])
        row_by_id: dict[str, dict[str, Any]] = {}
        for row in vector_rows + text_rows:
            row_by_id.setdefault(row["doc_id"], row)
        selected_ids = list(fused)[:self.top_k]
        documents = []
        for doc_id in selected_ids:
            doc = row_by_id[doc_id].copy()
            doc["rrf_score"] = round(fused[doc_id], 5)
            documents.append(doc)
        graph_nodes, graph_edges, cypher, cypher_params = self._graph_context(question, selected_ids, plan)
        confidence = heuristic_confidence(documents, graph_edges, question, self.min_confidence)
        return {
            "question": question,
            "documents": documents,
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "cypher": cypher,
            "cypher_params": cypher_params,
            "confidence": confidence,
            "retrieval": {"vector_candidates": len(vector_rank), "fulltext_candidates": len(text_rank),
                          "fused_candidates": len(fused), "seed_entities": len(graph_nodes)},
        }
