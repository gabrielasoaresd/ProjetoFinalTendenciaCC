# Modelagem LPG e consultas Cypher

## Nós

```cypher
(:Document {
  doc_id: STRING, title: STRING, content: STRING,
  source: STRING, source_label: STRING, embedding: LIST<FLOAT>
})

(:Entity {
  id: STRING, name: STRING, entity_type: STRING,
  aliases_text: STRING, embedding: LIST<FLOAT>
})
```

## Relacionamentos

```cypher
(:Document)-[:MENTIONS {entity_id: STRING}]->(:Entity)
(:Entity)-[:USES|COMBINES|IMPLEMENTS|STORES|ENABLES|... {
  key: STRING, doc_id: STRING, evidence: STRING,
  confidence: FLOAT, extraction_method: STRING
}]->(:Entity)
```

## Constraints e índices

```cypher
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE RANGE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.entity_type);

CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS
FOR (d:Document) ON EACH [d.title, d.content];

CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
FOR (d:Document) ON (d.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};
```

## Exemplo multi-hop

```cypher
MATCH p = (seed:Entity)-[*1..2]-(target:Entity)
WHERE seed.id IN $seed_ids
  AND ALL(rel IN relationships(p) WHERE rel.doc_id IN $doc_ids)
RETURN [n IN nodes(p) | {id:n.id, name:n.name}] AS nodes,
       [r IN relationships(p) | {
         type:type(r), evidence:r.evidence,
         source_id:startNode(r).id, target_id:endNode(r).id,
         doc_id:r.doc_id
       }] AS relationships
LIMIT 30;
```

## Exemplo shortest path

```cypher
MATCH p = shortestPath(
  (a:Entity {id: $source_id})-[*..5]-(b:Entity {id: $target_id})
)
WHERE ALL(rel IN relationships(p) WHERE rel.doc_id IN $doc_ids)
RETURN p
LIMIT 5;
```

Os parâmetros são enviados pelo driver; nenhum valor da pergunta é concatenado na consulta. Os tipos de relacionamento são criados apenas a partir do catálogo controlado do extrator.
