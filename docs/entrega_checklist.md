# Checklist de entrega e defesa

## Preparação acadêmica
- [ ] Confirmar com o docente o tamanho da equipe: o enunciado menciona 6–8 alunos em um trecho, 4–8 em outro e 4–6 na observação final.
- [ ] Confirmar a data de defesa: a primeira página indica 18/11/2026, enquanto a última descreve entrega/defesa uma ou duas semanas antes da AV2.
- [ ] Substituir `[Nomes dos integrantes]`, matrícula e instituição no artigo.
- [ ] Confirmar com o docente se prefere template SBC ou IEEE; aplicar o template oficial, se fornecido.
- [ ] Revisar o texto com a equipe e conferir as referências consultadas.
- [ ] Acrescentar resultados reais de execução no artigo (Hit@K, MRR e recalls) após rodar `scripts/evaluate_neo4j.py`.
- [ ] Registrar versão do Neo4j, Python, modelo de embeddings e modelo LLM efetivamente usados.

## Preparação técnica
- [ ] Instalar Docker e Python 3.10+ no computador da apresentação.
- [ ] Executar `docker compose up -d` e aguardar o Neo4j ficar saudável.
- [ ] Instalar `requirements.txt`.
- [ ] Executar `python scripts/ingest.py` e conferir os totais retornados.
- [ ] Abrir o Neo4j Browser e verificar constraints e índices (`SHOW INDEXES`, `SHOW VECTOR INDEXES`).
- [ ] Abrir a interface com `streamlit run app.py`.
- [ ] Executar pelo menos as perguntas Q1, Q2, Q3, Q5 e Q6.
- [ ] Conferir se a UI apresenta documentos, arestas, evidências, Cypher e parâmetros.
- [ ] Executar `PYTHONPATH=src pytest -q`.
- [ ] Executar `python scripts/evaluate_neo4j.py` e guardar `artifacts/evaluation_results.csv`.
- [ ] Validar que uma pergunta fora do corpus resulta em abstenção ou indicação de evidência insuficiente.
- [ ] Testar ingestão de um arquivo externo `.txt` ou `.pdf` pesquisável.

## Repositório e submissão
- [ ] Criar repositório Git público ou privado.
- [ ] Não versionar `.env`, `.venv`, senhas nem dados privados.
- [ ] Commitar código, corpus demonstrativo, documentação, artigo e slides.
- [ ] Conceder acesso ao docente, se o repositório for privado.
- [ ] Conferir se README contém comandos que funcionam em Windows e Linux.
- [ ] Levar cópia local/backup do projeto e dos slides.

## Defesa oral
- [ ] Definir quem apresenta cada parte: problema, arquitetura, implementação, avaliação e limitações.
- [ ] Preparar demonstração com o banco já iniciado e corpus já ingerido.
- [ ] Ter vídeo ou capturas da interface como plano B (não substituem a demonstração real).
- [ ] Não afirmar que o score heurístico é uma probabilidade ou que a extração está livre de erros.
- [ ] Explicar a diferença entre o protótipo CompGraph e os frameworks GraphRAG/KAG publicados.
