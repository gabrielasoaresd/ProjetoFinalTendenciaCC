from __future__ import annotations

import json
import re
from typing import Any

import requests


class OllamaClient:
    """Cliente opcional para um modelo local. Sem Ollama, a aplicação usa resposta extrativa."""
    def __init__(self, base_url: str, model: str, timeout: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False,
                  "options": {"temperature": temperature}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return str(response.json().get("response", "")).strip()

    def answer(self, question: str, evidence: list[str]) -> str:
        prompt = (
            "Você é um assistente acadêmico. Responda em português usando EXCLUSIVAMENTE as evidências abaixo. "
            "Não invente fatos. Quando as evidências não sustentarem a resposta, diga que não há informação suficiente. "
            "Cite os identificadores [E1], [E2] etc. após cada afirmação.\n\n"
            f"PERGUNTA: {question}\n\nEVIDÊNCIAS:\n" + "\n".join(evidence)
        )
        return self.generate(prompt)

    def plan(self, question: str, candidate_entities: list[str]) -> dict[str, Any]:
        prompt = (
            "Escolha um plano de recuperação para uma base Neo4j. Retorne APENAS JSON válido com as chaves "
            '"mode" ("neighborhood" ou "shortest_path") e "max_hops" (1, 2 ou 3). '
            "Use shortest_path somente se a pergunta conectar explicitamente duas entidades. "
            "Não gere Cypher.\n"
            f"Pergunta: {question}\nEntidades reconhecidas: {candidate_entities}"
        )
        raw = self.generate(prompt, temperature=0.0)
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {"mode": "neighborhood", "max_hops": 2}
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"mode": "neighborhood", "max_hops": 2}
        mode = value.get("mode") if value.get("mode") in {"neighborhood", "shortest_path"} else "neighborhood"
        hops = value.get("max_hops", 2)
        try:
            hops = max(1, min(3, int(hops)))
        except (TypeError, ValueError):
            hops = 2
        return {"mode": mode, "max_hops": hops}


def build_extractive_answer(result: dict[str, Any]) -> str:
    docs = result.get("documents", [])
    edges = result.get("graph_edges", [])
    if not result.get("confidence", {}).get("supported"):
        return (
            "Não encontrei evidências suficientes no corpus para responder com segurança. "
            "Tente reformular a pergunta ou inclua documentos que tratem diretamente do assunto."
        )
    lines = []
    for index, doc in enumerate(docs[:3], start=1):
        excerpt = re.sub(r"\s+", " ", doc.get("content", "")).strip()
        if len(excerpt) > 440:
            excerpt = excerpt[:437].rsplit(" ", 1)[0] + "..."
        lines.append(f"[E{index}] {doc.get('title', 'Documento')}: {excerpt}")
    if edges:
        triples = []
        for edge in edges[:5]:
            triples.append(
                f"{edge.get('source_id')} -[{edge.get('type')}]-> {edge.get('target_id')} "
                f"(evidência: ‘{edge.get('evidence', '')}’)"
            )
        lines.append("Relações do subgrafo: " + "; ".join(triples) + ".")
    return "Com base no corpus recuperado, seguem as evidências relevantes:\n\n" + "\n".join(lines)


def generate_answer(question: str, result: dict[str, Any], ollama: OllamaClient | None = None) -> tuple[str, str]:
    evidence = []
    for index, doc in enumerate(result.get("documents", [])[:5], start=1):
        evidence.append(f"[E{index}] {doc.get('title')}: {doc.get('content')}")
    for edge in result.get("graph_edges", [])[:10]:
        evidence.append(
            f"[G] {edge.get('source_id')} -[{edge.get('type')}]-> {edge.get('target_id')}; "
            f"trecho: {edge.get('evidence')}"
        )
    if ollama is not None and evidence:
        try:
            answer = ollama.answer(question, evidence)
            if answer:
                return answer, "Ollama local (grounded)"
        except requests.RequestException:
            pass
    return build_extractive_answer(result), "Extrativa (sem serviço externo)"
