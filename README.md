# CompGraph — GraphRAG & KAG em Ciência da Computação

Protótipo acadêmico de recuperação aumentada por grafos e geração aumentada por conhecimento, construído com Python, Neo4j, Streamlit e PyVis.

> **Escopo:** corpus demonstrativo em português sobre GraphRAG, KAG e tecnologias relacionadas. O projeto foi organizado para permitir ingestão de documentos próprios (`.txt`, `.md`, `.pdf` pesquisável e `.docx`). A base padrão contém resumos técnicos autorais vinculados a referências públicas; não representa um benchmark amplo nem substitui a validação humana das extrações.

## 1. O que o sistema entrega

| Pilar do enunciado | Implementação no CompGraph |
|---|---|
| Text-to-Graph (NER/RE) | Catálogo de entidades/aliases, extração de entidades por padrões, extração de relações por verbos, canonicalização e evidência textual preservada. |
| Neo4j LPG | `Document` e `Entity`, relações `MENTIONS` e relações semânticas tipadas, constraints de unicidade, índices RANGE (substitutos dos B-tree no Neo4j 5), Full-text e Vector. |
| Recuperação híbrida | Similaridade vetorial + pesquisa full-text, combinadas por Reciprocal Rank Fusion (RRF). |
| Multi-hop | Travessia de 1 a 3 saltos, caminho mais curto entre entidades e PageRank no subgrafo retornado. |
| Interface e explicabilidade | Streamlit, subgrafo interativo via PyVis, documentos-fonte, evidências, Cypher, parâmetros e indicador heurístico de suporte. |
| LLM/KAG | Planejamento opcional de consulta via Ollama local e geração opcional de resposta grounded. O LLM escolhe um plano limitado; um compilador cria Cypher parametrizada e read-only. |
| Testes e avaliação | Testes unitários, integração Neo4j opcional e conjunto de 8 perguntas com script para gerar métricas reais após ingestão. |

## 2. Arquitetura

```text
Documentos (JSONL / TXT / MD / PDF / DOCX)
                  |
                  v
       Text-to-Graph (NER + RE)
  aliases -> canonicalização -> triplas
                  |
                  v
          Neo4j (LPG Store)
   Document ---- MENTIONS ---- Entity
     embedding                 embedding
         |                        |
         +--- Vector / Full-text -+
                  |
                  v
       Recuperação híbrida (RRF)
                  |
                  v
  Cypher parametrizada + travessia multi-hop
          + PageRank no subgrafo
                  |
                  v
  Resposta fundamentada + proveniência
       Streamlit + visualização PyVis
```

### Estratégia de extração

O extrator utiliza um catálogo versionado (`src/compgraph/catalog.py`) para reconhecer entidades e aliases. A canonicalização converte variações do mesmo termo para um identificador estável. A extração de relações associa pares de entidades presentes na mesma sentença a padrões verbais controlados. Cada aresta armazena o trecho original, o documento de origem, o método e um score inicial de extração. A abordagem é deliberadamente auditável; para produção, amplie o catálogo, adicione revisão humana e compare com um extrator treinado/LLM.

### Schema LPG

- `(:Document {doc_id, title, content, source, embedding})`
- `(:Entity {id, name, entity_type, aliases_text, embedding})`
- `(:Document)-[:MENTIONS {entity_id}]->(:Entity)`
- Relações semânticas tipadas, por exemplo `(:Entity)-[:COMBINES {evidence, doc_id, confidence}]->(:Entity)`.

A instalação cria constraints `entity_id` e `document_id`; índices RANGE para `entity_type` e `source` (equivalentes ao uso geral de índices de propriedade que antes era atendido por B-tree); índices Full-text para documentos e entidades; e índices vetoriais de cosseno com dimensão igual à configuração do embedding. A dimensão padrão é 384.

### Recuperação híbrida

1. Busca vetorial nos embeddings dos documentos.
2. Busca lexical em índice Full-text.
3. Fusão das listas por RRF: `RRF(d) = Σ 1 / (k + rank(d))`, com `k = 60`.
4. Seleção de entidades citadas pelos documentos retornados.
5. Travessia do subgrafo em até `MAX_GRAPH_HOPS` saltos. Quando a pergunta explicita duas entidades, o plano pode selecionar `shortestPath`.
6. PageRank é calculado no subgrafo recuperado com NetworkX para ordenar entidades centrais.

**Nota sobre segurança:** o modelo opcional não executa Cypher livre. Ele sugere um plano JSON limitado (`neighborhood` ou `shortest_path`); o compilador cria consultas parametrizadas e validadas como somente leitura. Isso é intencional para reduzir riscos de prompt injection e escrita acidental no banco.

## 3. Requisitos

- Python 3.10 ou superior.
- Docker Desktop / Docker Engine com Docker Compose.
- 2 GB de memória livre recomendados para Neo4j local e execução da interface.
- Navegador web.

O modo padrão usa vetorização local por hashing e não baixa modelos. Para embeddings semânticos multilíngues, instale `requirements-semantic.txt`. O modelo de linguagem é opcional e pode ser executado localmente por Ollama.

## 4. Instalação e execução

### Linux / macOS / Git Bash

```bash
git clone <URL_DO_REPOSITORIO>
cd projeto_graphrag_kag
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
docker compose up -d
python scripts/ingest.py
streamlit run app.py
```

A interface estará em `http://localhost:8501`. O Neo4j Browser estará em `http://localhost:7474`.

### Windows PowerShell

```powershell
git clone <URL_DO_REPOSITORIO>
cd projeto_graphrag_kag
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
python scripts/ingest.py
streamlit run app.py
```

Credenciais locais padrão: usuário `neo4j`, senha `compgraph_password`. Altere-as antes de publicar qualquer instância acessível pela rede. O serviço mapeia Bolt em `7687` e HTTP em `7474`.

### Ingestão de documentos adicionais

Pela barra lateral da interface, envie um arquivo `.txt`, `.md`, `.pdf` pesquisável ou `.docx`. Também é possível usar a CLI:

```bash
python scripts/ingest_file.py ./meu_documento.pdf --source "https://exemplo.org/documento"
```

PDFs digitalizados como imagem não são processados por OCR nesta versão. Extraia o texto antes de enviar. O ID do documento usa hash do conteúdo para evitar colisões de nomes simples.

### Embeddings semânticos (opcional)

```bash
pip install -r requirements-semantic.txt
```

No `.env`, configure:

```env
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_DIMENSIONS=384
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

**Importante:** o modelo é baixado na primeira execução, se ainda não estiver em cache. Depois, reinicie a ingestão para recriar os embeddings. Não altere a dimensão sem recriar os índices vetoriais e reingerir todos os documentos.

### LLM local (opcional)

Instale o Ollama e baixe um modelo compatível, por exemplo `qwen2.5:3b`. Inicie o serviço e configure:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

Sem Ollama, o sistema responde em modo extrativo, citando trechos retornados pelo retrieval. O planejamento heurístico e a compilação Cypher permanecem funcionais.

## 5. Perguntas para demonstração

1. O que o GraphRAG combina?
2. Como Neo4j representa o conhecimento e qual linguagem o consulta?
3. Como a recuperação híbrida combina busca vetorial e textual?
4. Quais tarefas constroem um grafo a partir de texto?
5. Como encontrar conexões entre entidades em mais de um salto?
6. Como a interface demonstra a origem da resposta?
7. Qual algoritmo ajuda a identificar nós centrais?
8. Qual a diferença entre embeddings e LLM?

## 6. Testes e avaliação

```bash
PYTHONPATH=src pytest -q
```

O teste de integração ao Neo4j fica desativado por padrão. Com o banco ativo:

```bash
RUN_NEO4J_INTEGRATION=1 PYTHONPATH=src pytest -m integration -q
```

No PowerShell:

```powershell
$env:RUN_NEO4J_INTEGRATION="1"
$env:PYTHONPATH="src"
pytest -m integration -q
```

Para avaliar as 8 perguntas rotuladas em `data/evaluation_questions.json`:

```bash
python scripts/evaluate_neo4j.py
```

O script cria `artifacts/evaluation_results.csv` com Hit@K, MRR, recall de entidades, recall de tipos de relação, documentos retornados, score heurístico e quantidade de arestas. Execute-o somente após a ingestão do corpus. Não há resultados de benchmark pré-preenchidos neste pacote porque a execução integrada depende de um serviço Neo4j ativo.

### Testes executados durante a montagem deste pacote

- Testes unitários locais: **11 aprovados**.
- Teste de integração Neo4j: **1 ignorado**, aguardando Neo4j ativo e `RUN_NEO4J_INTEGRATION=1`.
- O ambiente de montagem não disponibilizou Docker/Neo4j; portanto, a validação ponta a ponta do banco deve ser feita no computador da equipe antes da defesa.

## 7. Estrutura do repositório

```text
projeto_graphrag_kag/
├── app.py
├── docker-compose.yml
├── requirements.txt
├── requirements-semantic.txt
├── .env.example
├── data/
│   ├── corpus.jsonl
│   └── evaluation_questions.json
├── src/compgraph/
│   ├── catalog.py
│   ├── config.py
│   ├── embeddings.py
│   ├── extraction.py
│   ├── generation.py
│   ├── neo4j_store.py
│   ├── pipeline.py
│   └── retrieval.py
├── scripts/
│   ├── ingest.py
│   ├── ingest_file.py
│   └── evaluate_neo4j.py
├── tests/
└── docs/
```

## 8. Limitações e decisões de projeto

- O catálogo e os padrões NER/RE são orientados ao domínio e precisam de extensão para documentos de outros assuntos.
- O corpus embarcado contém 12 resumos autorais de demonstração associados a referências públicas; a cobertura ainda é pequena.
- O embedding padrão por hashing de n-gramas é reprodutível/offline, mas não representa semântica como um encoder Transformer. Ative Sentence Transformers para avaliação semântica.
- O gerador LLM é opcional. Sem Ollama, a resposta é extrativa e não tenta simular uma resposta generativa.
- A confiança é um índice heurístico baseado em cobertura, quantidade de fontes e relações, não uma probabilidade calibrada.
- PageRank é calculado no subgrafo retornado; não há dependência do plugin Graph Data Science (GDS).
- PDFs digitalizados precisam de OCR externo.
- A execução com Docker/Neo4j e a avaliação de retrieval ainda devem ser realizadas pela equipe no ambiente de entrega.

## 9. Referências técnicas

- EDGE, D. et al. *From Local to Global: A Graph RAG Approach to Query-Focused Summarization*. arXiv:2404.16130, 2024. https://arxiv.org/abs/2404.16130
- LIANG, L. et al. *KAG: Boosting LLMs in Professional Domains via Knowledge Augmented Generation*. arXiv:2409.13731, 2024. https://arxiv.org/abs/2409.13731
- NEO4J. *Cypher Manual: Vector indexes*. https://neo4j.com/docs/cypher-manual/5/indexes/semantic-indexes/vector-indexes/
- NEO4J. *Cypher Manual: Full-text indexes*. https://neo4j.com/docs/cypher-manual/5/indexes/semantic-indexes/full-text-indexes/
- NEO4J. *Python Driver Manual*. https://neo4j.com/docs/python-manual/current/
- STREAMLIT. *Documentation*. https://docs.streamlit.io/
- NETWORKX. *Link analysis algorithms*. https://networkx.org/documentation/stable/reference/algorithms/link_analysis.html

## 10. Antes de entregar

Leia `docs/entrega_checklist.md` e substitua os campos entre colchetes no artigo e na apresentação. A equipe deve gravar a execução real, preencher as métricas do script de avaliação e conceder acesso ao repositório ao docente.
