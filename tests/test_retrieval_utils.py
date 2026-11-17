from compgraph.retrieval import (
    compile_graph_cypher,
    heuristic_confidence,
    reciprocal_rank_fusion,
    safe_lucene_query,
    validate_readonly_cypher,
)


def test_reciprocal_rank_fusion_rewards_consensus():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "a"]], k=60)
    assert fused["a"] == fused["b"]
    fused = reciprocal_rank_fusion([["a", "b"], ["a", "c"]], k=60)
    assert fused["a"] > fused["b"]


def test_lucene_query_uses_sanitized_terms():
    query = safe_lucene_query('GraphRAG: o que é "Cypher"?')
    assert '"graphrag"' in query
    assert '"cypher"' in query
    assert ";" not in query


def test_compiler_generates_readonly_cypher():
    query = compile_graph_cypher("neighborhood", 2)
    assert "MATCH p" in query
    assert "[*1..2]" in query
    assert validate_readonly_cypher(query)
    shortest = compile_graph_cypher("shortest_path", 3)
    assert "shortestPath" in shortest
    assert validate_readonly_cypher(shortest)


def test_cypher_validator_rejects_write_and_multiple_statements():
    assert not validate_readonly_cypher("MATCH (n) DELETE n RETURN n")
    assert not validate_readonly_cypher("MATCH (n) RETURN n; MATCH (m) RETURN m")
    assert not validate_readonly_cypher("CALL dbms.security.listUsers() YIELD user RETURN user")


def test_confidence_is_heuristic_and_abstains_without_evidence():
    low = heuristic_confidence([], [], "GraphRAG")
    assert low["supported"] is False
    docs = [{"doc_id": "d1", "title": "GraphRAG", "content": "GraphRAG usa Knowledge Graph."}]
    high = heuristic_confidence(docs, [{"type": "USES"}], "GraphRAG Knowledge Graph", 0.1)
    assert high["score"] > 0
    assert high["supported"] is True
    assert "heurístico" in high["explanation"]
