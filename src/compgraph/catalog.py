"""Vocabulário de domínio e aliases usados na canonicalização de entidades.

O catálogo explícito mantém a extração auditável e reduz entidades duplicadas.
Para um domínio novo, amplie este arquivo ou substitua-o por um schema versionado.
"""
ENTITY_CATALOG = [
    {"name": "GraphRAG", "type": "Architecture", "aliases": ["Graph RAG", "GraphRAG"]},
    {"name": "KAG", "type": "Architecture", "aliases": ["Knowledge-Augmented Generation", "Knowledge Augmented Generation", "KAG"]},
    {"name": "RAG", "type": "Architecture", "aliases": ["Retrieval-Augmented Generation", "Retrieval Augmented Generation", "RAG"]},
    {"name": "Knowledge Graph", "type": "Concept", "aliases": ["knowledge graph", "knowledge graphs", "grafo de conhecimento", "grafos de conhecimento"]},
    {"name": "Neo4j", "type": "Technology", "aliases": ["Neo4j"]},
    {"name": "LPG", "type": "DataModel", "aliases": ["Labeled Property Graph", "Labeled Property Graphs", "LPG"]},
    {"name": "Cypher", "type": "Language", "aliases": ["Cypher"]},
    {"name": "Embeddings", "type": "Concept", "aliases": ["embedding", "embeddings", "vetores de representação", "vetor de embedding"]},
    {"name": "Busca vetorial", "type": "RetrievalMethod", "aliases": ["busca vetorial", "pesquisa vetorial", "vector search"]},
    {"name": "Full-text Search", "type": "RetrievalMethod", "aliases": ["full-text search", "full text search", "busca textual", "índice fulltext", "índice de texto completo"]},
    {"name": "Recuperação híbrida", "type": "RetrievalMethod", "aliases": ["recuperação híbrida", "busca híbrida", "hybrid retrieval"]},
    {"name": "Raciocínio multi-hop", "type": "Reasoning", "aliases": ["multi-hop reasoning", "raciocínio multi-hop", "travessia multi-hop", "multi hop"]},
    {"name": "Text-to-Graph", "type": "Pipeline", "aliases": ["Text-to-Graph", "text to graph"]},
    {"name": "NER", "type": "NLPTask", "aliases": ["Named Entity Recognition", "reconhecimento de entidades nomeadas", "NER"]},
    {"name": "RE", "type": "NLPTask", "aliases": ["Relation Extraction", "extração de relações", "RE"]},
    {"name": "PageRank", "type": "Algorithm", "aliases": ["PageRank", "page rank"]},
    {"name": "Leiden", "type": "Algorithm", "aliases": ["Leiden", "algoritmo de Leiden"]},
    {"name": "Streamlit", "type": "Technology", "aliases": ["Streamlit"]},
    {"name": "PyVis", "type": "Technology", "aliases": ["PyVis", "pyvis"]},
    {"name": "LLM", "type": "Model", "aliases": ["Large Language Model", "Large Language Models", "modelo de linguagem", "modelos de linguagem", "LLM", "LLMs"]},
]

RELATION_PATTERNS = {
    "COMBINES": [r"combina", r"integra", r"articula"],
    "USES": [r"usa", r"utiliza", r"emprega", r"recorre a"],
    "IMPLEMENTS": [r"implementa", r"materializa"],
    "STORES": [r"armazena", r"persiste", r"guarda"],
    "ENABLES": [r"permite", r"possibilita", r"viabiliza", r"facilita"],
    "MITIGATES": [r"mitiga", r"reduz", r"diminui"],
    "RETRIEVES": [r"recupera", r"busca", r"localiza"],
    "INDEXES": [r"indexa", r"indexam"],
    "VISUALIZES": [r"visualiza", r"renderiza", r"exibe"],
    "EXTRACTS": [r"extrai", r"identifica", r"detecta"],
    "TRAVERSES": [r"percorre", r"navega", r"atravessa"],
    "BASED_ON": [r"baseia-se em", r"fundamenta-se em", r"é baseado em", r"são baseados em"],
    "SUPPORTS": [r"suporta", r"apoia", r"sustenta"],
}
