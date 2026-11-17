# Protocolo de avaliação

## Perguntas e rótulos

O arquivo `data/evaluation_questions.json` contém oito perguntas, entidades esperadas, tipos de relação esperados e IDs dos documentos de referência. São rótulos de referência construídos manualmente para o corpus de demonstração.

## Métricas implementadas

- **Hit@K:** 1 quando pelo menos um documento esperado aparece nos K documentos recuperados.
- **MRR:** inverso do ranking do primeiro documento esperado.
- **Entity Recall:** fração das entidades esperadas encontradas no subgrafo de contexto.
- **Relation Recall:** fração dos tipos de relação esperados encontrados no subgrafo.
- **Confidence score:** índice heurístico que combina cobertura lexical, número de fontes e número de relações; não deve ser interpretado como probabilidade.

## Execução

1. Iniciar Neo4j e ingerir o corpus (`python scripts/ingest.py`).
2. Rodar `python scripts/evaluate_neo4j.py`.
3. Arquivar `artifacts/evaluation_results.csv` junto ao relatório.
4. Reportar média e resultados por pergunta, sem generalizar além do corpus de demonstração.

## Comparação recomendada para a versão final

Para demonstrar o valor da arquitetura híbrida, executar a mesma bateria em três configurações: somente full-text, somente vetor e híbrida (RRF + grafo). Registrar Hit@K e MRR para cada abordagem. O código-base já contém as consultas individuais; a comparação controlada pode ser adicionada como extensão da avaliação. Não declarar melhoria quantitativa antes de obter esses resultados.
