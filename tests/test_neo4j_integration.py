"""Teste de integração opcional: RUN_NEO4J_INTEGRATION=1 pytest -m integration."""
import os
import pytest

pytestmark = pytest.mark.integration


def test_neo4j_connection_and_schema():
    if os.getenv("RUN_NEO4J_INTEGRATION") != "1":
        pytest.skip("Defina RUN_NEO4J_INTEGRATION=1 com Neo4j ativo para executar.")
    from compgraph.pipeline import make_store
    store = make_store()
    try:
        store.verify()
        stats = store.stats()
        assert "documents" in stats
    finally:
        store.close()
