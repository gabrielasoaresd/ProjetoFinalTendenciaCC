from __future__ import annotations

import time
from typing import Any

from .embeddings import Embedder


def schema_statements(dimension: int = 384) -> list[str]:
    return [
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
        "CREATE RANGE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
        "CREATE RANGE INDEX document_source_idx IF NOT EXISTS FOR (d:Document) ON (d.source)",
        "CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.title, d.content]",
        "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.aliases_text]",
        f"CREATE VECTOR INDEX document_embeddings IF NOT EXISTS FOR (d:Document) ON (d.embedding) OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, `vector.similarity_function`: 'cosine'}}}}",
        f"CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS FOR (e:Entity) ON (e.embedding) OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, `vector.similarity_function`: 'cosine'}}}}",
    ]


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", embedding_dimension: int = 384):
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("Instale as dependências do projeto com `pip install -r requirements.txt`.") from exc
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.embedding_dimension = embedding_dimension

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def run(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def ensure_schema(self, wait_seconds: int = 30) -> None:
        for statement in schema_statements(self.embedding_dimension):
            self.run(statement)
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            states = self.run(
                "SHOW VECTOR INDEXES YIELD name, state RETURN collect({name:name,state:state}) AS indexes"
            )
            indexes = states[0]["indexes"] if states else []
            expected = {"document_embeddings", "entity_embeddings"}
            online = {item["name"] for item in indexes if item["state"] == "ONLINE"}
            if expected.issubset(online):
                return
            time.sleep(1)
        # A chamada não falha apenas pelo atraso de população: a consulta subsequente
        # apresentará erro explícito caso os índices ainda não estejam disponíveis.

    def ingest(self, documents: list[dict[str, Any]], embedder: Embedder) -> dict[str, int]:
        document_rows = []
        entity_rows: dict[str, dict[str, Any]] = {}
        mention_rows = []
        relation_rows = []
        for doc in documents:
            document_rows.append({
                "doc_id": doc["doc_id"], "title": doc["title"],
                "content": doc["content"], "source": doc.get("source", ""),
                "source_label": doc.get("source_label", "Fonte de demonstração"),
                "embedding": embedder.encode(doc["title"] + ". " + doc["content"]),
            })
            for entity in doc["entities"]:
                existing = entity_rows.get(entity["id"], entity)
                existing = {**existing, "embedding": embedder.encode(entity["name"] + " " + entity["entity_type"])}
                entity_rows[entity["id"]] = existing
                mention_rows.append({"doc_id": doc["doc_id"], "entity_id": entity["id"]})
            for triple in doc["triples"]:
                relation_rows.append({**triple, "doc_id": doc["doc_id"],
                                      "key": f"{doc['doc_id']}|{triple['source_id']}|{triple['relation']}|{triple['target_id']}"})

        self.run("""
        UNWIND $rows AS row
        MERGE (d:Document {doc_id: row.doc_id})
        SET d.title = row.title, d.content = row.content, d.source = row.source,
            d.source_label = row.source_label, d.embedding = row.embedding
        """, {"rows": document_rows})
        self.run("""
        UNWIND $rows AS row
        MERGE (e:Entity {id: row.id})
        SET e.name = row.name, e.entity_type = row.entity_type,
            e.embedding = row.embedding, e.aliases_text = row.name
        """, {"rows": list(entity_rows.values())})
        self.run("""
        UNWIND $rows AS row
        MATCH (d:Document {doc_id: row.doc_id})
        MATCH (e:Entity {id: row.entity_id})
        MERGE (d)-[:MENTIONS {entity_id: row.entity_id}]->(e)
        """, {"rows": mention_rows})
        for relation_type in sorted({r["relation"] for r in relation_rows}):
            if not relation_type.isidentifier() or not relation_type.isupper():
                raise ValueError(f"Tipo de relação inválido: {relation_type}")
            rows = [r for r in relation_rows if r["relation"] == relation_type]
            query = f"""
            UNWIND $rows AS row
            MATCH (s:Entity {{id: row.source_id}})
            MATCH (t:Entity {{id: row.target_id}})
            MERGE (s)-[r:{relation_type} {{key: row.key}}]->(t)
            SET r.doc_id = row.doc_id, r.evidence = row.evidence,
                r.confidence = row.confidence, r.extraction_method = row.extraction_method
            """
            self.run(query, {"rows": rows})
        return {"documents": len(document_rows), "entities": len(entity_rows),
                "relations": len(relation_rows), "mentions": len(mention_rows)}

    def stats(self) -> dict[str, int]:
        row = self.run("""
        MATCH (d:Document) WITH count(d) AS documents
        MATCH (e:Entity) WITH documents, count(e) AS entities
        OPTIONAL MATCH ()-[r]->() RETURN documents, entities, count(r) AS relationships
        """)
        return row[0] if row else {"documents": 0, "entities": 0, "relationships": 0}
