# Roteiro sugerido para a defesa (8–10 minutos)

## 1. Abertura e problema (1 min)
“Nosso projeto, CompGraph, é um protótipo que explora GraphRAG e KAG para responder perguntas sobre conceitos de Ciência da Computação. A motivação é que uma busca vetorial isolada pode recuperar trechos parecidos sem explicitar como conceitos diferentes se conectam. Ao estruturar entidades e relações em um grafo, conseguimos recuperar caminhos e mostrar de onde veio a resposta.”

## 2. Objetivo e recorte (45 s)
“O domínio escolhido é o próprio ecossistema de GraphRAG/KAG. O corpus inicial possui resumos técnicos associados a referências públicas e pode receber documentos TXT, Markdown, PDF pesquisável e DOCX. É uma prova de conceito: priorizamos rastreabilidade e reprodução, não volume de dados.”

## 3. Pipeline Text-to-Graph (1 min)
“Primeiro, o pipeline identifica entidades com um catálogo de nomes e aliases. Depois, extrai relações por padrões verbais, resolve aliases para um ID canônico e preserva o trecho que justificou cada aresta. Isso torna a extração auditável. A limitação é que a estratégia é dependente do domínio e precisa ser ampliada para novos vocabulários.”

## 4. Neo4j e LPG (1 min)
“No Neo4j, documentos e entidades são nós. A relação MENTIONS liga cada documento às entidades citadas. Relações semânticas, como COMBINES ou IMPLEMENTS, conectam entidades. Criamos constraints de unicidade, índices RANGE (a alternativa atual aos índices B-tree gerais no Neo4j 5), Full-text e Vector de 384 dimensões.”

## 5. Recuperação híbrida e multi-hop (1 min 30 s)
“A pergunta gera um embedding e também uma consulta lexical. As duas listas são combinadas por Reciprocal Rank Fusion, sem comparar diretamente scores de escalas diferentes. Em seguida, os documentos selecionados fornecem entidades-semente para uma travessia de até três saltos. Quando existem duas entidades explícitas, o plano pode selecionar shortestPath. Calculamos PageRank no subgrafo para ordenar os nós centrais.”

## 6. Demonstração da interface (2 min)
1. Perguntar “O que o GraphRAG combina?” e mostrar documentos recuperados.
2. Abrir “Subgrafo de contexto” e apontar nós, arestas e trechos de evidência.
3. Abrir “Rastreabilidade técnica” e mostrar Cypher, parâmetros e métricas.
4. Perguntar algo fora do corpus e mostrar a abstenção por falta de evidência.
5. Se houver tempo, enviar um TXT/PDF pesquisável pela barra lateral e fazer uma nova consulta.

## 7. Avaliação e limitações (1 min)
“Temos testes unitários para extração, embeddings, fusão de ranking, validação das consultas e score heurístico. A bateria de oito perguntas produz Hit@K, MRR, Entity Recall e Relation Recall depois da execução com Neo4j. O embedding offline por hashing é um fallback lexical; para avaliar semântica, ativamos Sentence Transformers. O LLM é opcional e local via Ollama. A confiança não é calibrada estatisticamente.”

## 8. Encerramento (30 s)
“O principal resultado é a integração demonstrável entre recuperação textual, estrutura LPG, travessia de grafos e explicabilidade. O protótipo mostra não só uma resposta, mas também documentos, relações e caminhos que sustentam essa resposta. Como próximos passos, ampliar o corpus, validar a extração com anotação humana e comparar vetor, full-text e híbrido em uma avaliação controlada.”

## Perguntas que podem aparecer

**Por que usar grafo e não somente RAG vetorial?** Para perguntas que dependem de relações explícitas e caminhos entre entidades; o grafo adiciona estrutura e provenance, mas não substitui a recuperação textual.

**O sistema elimina alucinações?** Não. O sistema reduz o espaço para afirmações sem suporte ao fornecer evidências e permitir abstenção. Ainda exige avaliação e revisão.

**Por que extração por regras?** É reprodutível e permite inspecionar cada regra. A troca é cobertura e flexibilidade menores do que um extrator robusto treinado/LLM.

**O que é KAG neste projeto?** É uma inspiração arquitetural de geração aumentada por conhecimento. O CompGraph não é uma implementação do framework OpenSPG/KAG; implementa um subconjunto didático de indexação cruzada, recuperação híbrida e raciocínio guiado por estrutura.

**O PageRank comprova relevância factual?** Não. Ele mede centralidade estrutural e só serve para ordenar nós no subgrafo.

**A confiança de 80% significa 80% de chance de estar certo?** Não. É um score heurístico de suporte calculado por cobertura lexical, fontes e relações; não foi calibrado contra probabilidades observadas.
