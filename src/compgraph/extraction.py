from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Any

from .catalog import ENTITY_CATALOG, RELATION_PATTERNS


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized.lower()).strip("_")
    return normalized or hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


@dataclass(frozen=True)
class Mention:
    entity_id: str
    name: str
    entity_type: str
    start: int
    end: int
    surface: str


@dataclass(frozen=True)
class Triple:
    source_id: str
    source_name: str
    relation: str
    target_id: str
    target_name: str
    evidence: str
    confidence: float = 0.90
    extraction_method: str = "catalog+pattern"


class DomainExtractor:
    """NER e RE determinísticos com aliases e padrões de relação em português.

    É uma estratégia de extração supervisionada por schema: previsível e inspecionável,
    adequada ao corpus de demonstração. O catálogo deve ser ampliado para outros domínios.
    """

    def __init__(self, catalog: list[dict[str, Any]] | None = None):
        self.catalog = catalog or ENTITY_CATALOG
        self._compiled: list[tuple[dict[str, Any], str, re.Pattern[str]]] = []
        for entity in self.catalog:
            for alias in sorted(entity["aliases"], key=len, reverse=True):
                pattern = re.compile(r"(?<!\w)" + re.escape(alias).replace(r"\ ", r"\s+") + r"(?!\w)", re.IGNORECASE)
                self._compiled.append((entity, alias, pattern))
        self._relation_patterns = {
            label: [re.compile(r"\b" + pat + r"\b", re.IGNORECASE) for pat in pats]
            for label, pats in RELATION_PATTERNS.items()
        }

    def extract_entities(self, text: str) -> list[Mention]:
        candidates: list[Mention] = []
        for entity, _alias, pattern in self._compiled:
            for match in pattern.finditer(text):
                candidates.append(Mention(
                    entity_id=slugify(entity["name"]),
                    name=entity["name"],
                    entity_type=entity["type"],
                    start=match.start(), end=match.end(), surface=match.group(0),
                ))
        # Longest match wins where aliases overlap (e.g. RAG inside a longer expression).
        candidates.sort(key=lambda m: (m.start, -(m.end - m.start), m.entity_id))
        selected: list[Mention] = []
        for candidate in candidates:
            if any(candidate.start < prior.end and prior.start < candidate.end for prior in selected):
                continue
            selected.append(candidate)
        selected.sort(key=lambda m: m.start)
        # Canonicalize repeated mentions in a document only once for the node list.
        return selected

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

    def extract_relations(self, text: str) -> list[Triple]:
        triples: list[Triple] = []
        for sentence in self._sentences(text):
            mentions = self.extract_entities(sentence)
            if len(mentions) < 2:
                continue
            relation_hits: list[tuple[int, str]] = []
            for label, patterns in self._relation_patterns.items():
                for pattern in patterns:
                    hit = pattern.search(sentence)
                    if hit:
                        relation_hits.append((hit.start(), label))
            if not relation_hits:
                continue
            relation_hits.sort(key=lambda x: x[0])
            # Primeiro par de entidades da frase, ordenado por posição; a evidência original
            # é preservada e aparece na UI para auditoria humana.
            source, target = mentions[0], mentions[1]
            relation = relation_hits[0][1]
            if source.entity_id == target.entity_id:
                continue
            triple = Triple(
                source_id=source.entity_id,
                source_name=source.name,
                relation=relation,
                target_id=target.entity_id,
                target_name=target.name,
                evidence=sentence,
            )
            if not any((t.source_id, t.relation, t.target_id, t.evidence) ==
                       (triple.source_id, triple.relation, triple.target_id, triple.evidence) for t in triples):
                triples.append(triple)
        return triples

    def extract_document(self, document: dict[str, Any]) -> dict[str, Any]:
        text = normalize_text(document.get("content", ""))
        mentions = self.extract_entities(text)
        triples = self.extract_relations(text)
        unique_entities = {}
        for mention in mentions:
            unique_entities[mention.entity_id] = {
                "id": mention.entity_id,
                "name": mention.name,
                "entity_type": mention.entity_type,
            }
        for triple in triples:
            unique_entities.setdefault(triple.source_id, {
                "id": triple.source_id, "name": triple.source_name,
                "entity_type": self._type_for(triple.source_id),
            })
            unique_entities.setdefault(triple.target_id, {
                "id": triple.target_id, "name": triple.target_name,
                "entity_type": self._type_for(triple.target_id),
            })
        return {
            **document,
            "content": text,
            "entities": list(unique_entities.values()),
            "triples": [asdict(t) for t in triples],
        }

    def _type_for(self, entity_id: str) -> str:
        for entity in self.catalog:
            if slugify(entity["name"]) == entity_id:
                return entity["type"]
        return "Concept"
