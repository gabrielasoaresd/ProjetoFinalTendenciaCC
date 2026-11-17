from compgraph.embeddings import HashEmbedder


def test_hash_embedding_has_fixed_dimension_and_normalization():
    embedder = HashEmbedder(384)
    vector = embedder.encode("GraphRAG combina recuperação e grafos")
    assert len(vector) == 384
    assert abs(sum(value * value for value in vector) ** 0.5 - 1.0) < 1e-6


def test_empty_text_returns_zero_vector():
    vector = HashEmbedder(64).encode("")
    assert len(vector) == 64
    assert all(value == 0 for value in vector)
