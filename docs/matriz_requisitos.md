# Matriz de rastreabilidade — enunciado x implementação

| Requisito do enunciado | Como foi atendido | Evidência no repositório |
|---|---|---|
| Extração automatizada de entidades (NER) | Catálogo de entidades, aliases, detecção por padrões e canonicalização. | `src/compgraph/catalog.py`, `src/compgraph/extraction.py` |
| Extração de relações (RE) | Padrões verbais controlados produzem triplas com sentença de evidência. | `src/compgraph/catalog.py`, `src/compgraph/extraction.py` |
| Resolução de entidades | Alias equivalente aponta para um ID canônico estável. | `slugify`, `DomainExtractor.extract_entities` |
| Schema LPG | Nós `Document` e `Entity`, relação `MENTIONS` e relações semânticas tipadas. | `src/compgraph/neo4j_store.py`, `docs/modelagem_cypher.md` |
| Constraints de unicidade | IDs de documentos e entidades possuem constraints. | `schema_statements()` |
| Índices de propriedade | RANGE indexes para propriedades no Neo4j 5.26; substituem B-tree geral nas versões atuais. | `schema_statements()` |
| Full-text e Vector Index | Índices full-text para texto e vetoriais para embeddings de documentos e entidades. | `schema_statements()`, `src/compgraph/retrieval.py` |
| Busca híbrida | Busca vetorial + Full-text, fusão RRF com k=60. | `HybridRetriever`, `reciprocal_rank_fusion` |
| Multi-hop traversal | Travessia de 1 a 3 saltos e shortestPath entre entidades. | `compile_graph_cypher`, `HybridRetriever._graph_context` |
| Algoritmo de grafo | PageRank no subgrafo recuperado via NetworkX. | `HybridRetriever._graph_context` |
| Geração/planejamento de Cypher | Ollama opcional sugere plano JSON limitado; compilador gera Cypher parametrizada, read-only. | `src/compgraph/generation.py`, `src/compgraph/retrieval.py` |
| Interface funcional | Interface web em Streamlit com campo de pergunta, fontes, resultados e métricas. | `app.py` |
| Renderização interativa de subgrafo | PyVis apresenta entidades e relações de contexto. | `app.py` |
| Explicabilidade/proveniência | Arestas armazenam evidência e ID do documento; UI mostra fontes, query, parâmetros e score. | `neo4j_store.py`, `app.py` |
| Mitigação de alucinações | Resposta limitada ao contexto recuperado, indicação de evidências e abstenção por suporte insuficiente. | `generation.py`, `heuristic_confidence` |
| Código e reprodutibilidade | README, Docker Compose, requirements, .env.example, testes e scripts. | Raiz do repositório |
| Artigo técnico | Artigo em DOCX com resumo/abstract, fundamentação, arquitetura, avaliação e referências. | `artigo_tecnico_compgraph.docx` |
| Apresentação | Slides de defesa e roteiro de fala. | `apresentacao_compgraph.pptx`, `docs/roteiro_defesa.md` |

## Aderência à rubrica

| Critério | Peso do enunciado | Componentes do pacote |
|---|---:|---|
| Modelagem de grafos (Neo4j) | 25% | Schema LPG, constraints, RANGE, Full-text e Vector indexes |
| Engenharia GraphRAG/KAG | 30% | Text-to-Graph, híbrido RRF, multi-hop, shortestPath, PageRank, LLM local opcional e abstenção |
| Interface e explicabilidade | 20% | Streamlit, PyVis, documentos-fonte, evidência, Cypher, parâmetros e score |
| Qualidade do código e artigo | 25% | Organização modular, testes, README, scripts, artigo e roteiro de defesa |

## Pontos que ainda exigem validação da equipe

1. Executar Neo4j/Streamlit no computador da equipe e registrar a versão realmente usada.
2. Executar o script de avaliação e inserir os resultados reais no artigo.
3. Testar consultas multi-hop com perguntas que tenham caminho de dois ou mais relacionamentos no grafo.
4. Confirmar com o docente o template final e as divergências do enunciado sobre número de integrantes e data.
