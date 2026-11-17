from compgraph.extraction import DomainExtractor, slugify
from compgraph.pipeline import load_corpus, prepare_documents


def test_entity_resolution_canonicalizes_aliases():
    extractor = DomainExtractor()
    mentions = extractor.extract_entities("GraphRAG combina Graph RAG e Retrieval-Augmented Generation.")
    ids = [mention.entity_id for mention in mentions]
    assert ids.count("graphrag") == 2
    assert "rag" in ids


def test_relation_extraction_preserves_evidence():
    extractor = DomainExtractor()
    triples = extractor.extract_relations("Neo4j implementa o modelo LPG.")
    assert len(triples) == 1
    assert triples[0].source_id == "neo4j"
    assert triples[0].relation == "IMPLEMENTS"
    assert triples[0].target_id == "lpg"
    assert triples[0].evidence == "Neo4j implementa o modelo LPG."


def test_corpus_is_valid_and_processed():
    raw = load_corpus()
    prepared = prepare_documents(raw)
    assert len(prepared) >= 10
    assert all(item["entities"] for item in prepared)
    assert all(item["doc_id"] and item["content"] for item in prepared)
    assert sum(len(item["triples"]) for item in prepared) >= 10


def test_slugify_is_stable():
    assert slugify("Knowledge Graph") == "knowledge_graph"
