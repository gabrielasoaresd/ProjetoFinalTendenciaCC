from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compgraph.config import settings
from compgraph.embeddings import make_embedder
from compgraph.extraction import slugify
from compgraph.pipeline import make_store, prepare_documents


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        from docx import Document
        document = Document(path)
        return "\n".join(p.text for p in document.paragraphs if p.text.strip())
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError("Formato não suportado. Use .txt, .md, .docx ou .pdf.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai entidades/relações e ingere um documento no Neo4j.")
    parser.add_argument("file", type=Path, help="Caminho do documento")
    parser.add_argument("--source", default="", help="URL ou referência de origem para a proveniência")
    args = parser.parse_args()
    path = args.file.expanduser().resolve()
    if not path.exists():
        parser.error(f"Arquivo não encontrado: {path}")
    content = read_document(path)
    if len(content.strip()) < 40:
        parser.error("O documento possui pouco texto extraível; verifique se o PDF é pesquisável ou use OCR externamente.")
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    document = {"doc_id": f"upload_{slugify(path.stem)}_{digest}", "title": path.stem.replace("_", " "),
                "content": content, "source": args.source or path.name,
                "source_label": f"Documento enviado: {path.name}"}
    prepared = prepare_documents([document])
    embedder = make_embedder(settings.embedding_provider, settings.embedding_dimensions,
                             settings.sentence_transformer_model)
    store = make_store()
    try:
        store.verify()
        store.ensure_schema()
        summary = store.ingest(prepared, embedder)
    finally:
        store.close()
    print("Documento ingerido com sucesso:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
