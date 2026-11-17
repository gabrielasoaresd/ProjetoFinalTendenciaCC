from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import streamlit.components.v1 as components

from compgraph.config import settings
from compgraph.embeddings import make_embedder
from compgraph.extraction import DomainExtractor
from compgraph.generation import OllamaClient, generate_answer
from compgraph.pipeline import make_store, prepare_documents, run_ingestion
from compgraph.extraction import slugify
from compgraph.retrieval import HybridRetriever

st.set_page_config(page_title="CompGraph | GraphRAG & KAG", page_icon="🕸️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 2.5rem; max-width: 1450px;}
.small-muted {color: #64748b; font-size: .88rem;}
.evidence-card {border: 1px solid rgba(120,130,150,.25); border-radius: 12px; padding: 12px 14px; margin: 8px 0;}
.metric-label {font-size: .8rem; color: #64748b;}
</style>
""", unsafe_allow_html=True)

st.title("🕸️ CompGraph")
st.subheader("Assistente acadêmico baseado em GraphRAG e KAG")
st.caption("Tecnologias e conceitos de Ciência da Computação • Recuperação híbrida • Raciocínio multi-hop • Proveniência")

@st.cache_resource(show_spinner=False)
def get_resources():
    store = make_store()
    embedder = make_embedder(settings.embedding_provider, settings.embedding_dimensions,
                             settings.sentence_transformer_model)
    extractor = DomainExtractor()
    retriever = HybridRetriever(store, embedder, extractor, settings.top_k_documents,
                                settings.max_graph_hops, settings.min_confidence)
    ollama = None
    if settings.llm_provider == "ollama":
        ollama = OllamaClient(settings.ollama_base_url, settings.ollama_model)
    return store, embedder, extractor, retriever, ollama

store = None
retriever = None
extractor = DomainExtractor()
ollama = None
connected = False
try:
    store, embedder, extractor, retriever, ollama = get_resources()
    store.verify()
    connected = True
except Exception as exc:
    st.error(f"Não foi possível conectar ao Neo4j: {exc}")
    st.info("Inicie o banco com `docker compose up -d` e confira as variáveis do arquivo `.env`.")

with st.sidebar:
    st.header("Configuração")
    st.markdown(f"**Neo4j:** {'Conectado' if connected else 'Desconectado'}")
    st.markdown(f"**Embeddings:** `{settings.embedding_provider}` ({settings.embedding_dimensions} dimensões)")
    st.markdown(f"**LLM:** `{settings.llm_provider}`")
    if st.button("Executar ingestão do corpus", disabled=not connected, use_container_width=True):
        try:
            with st.spinner("Extraindo entidades, relações e indexando documentos..."):
                summary = run_ingestion()
            get_resources.clear()
            st.success(f"Ingestão concluída: {summary['documents']} documentos, {summary['entities']} entidades e {summary['relations']} relações.")
            st.rerun()
        except Exception as exc:
            st.error(f"Falha na ingestão: {exc}")
    st.markdown("**Adicionar documento**")
    uploaded_file = st.file_uploader("TXT, MD, PDF pesquisável ou DOCX", type=["txt", "md", "pdf", "docx"], key="doc_upload")
    uploaded_source = st.text_input("URL/referência da fonte (opcional)", key="upload_source")
    if st.button("Extrair e ingerir documento", disabled=not (connected and uploaded_file), use_container_width=True):
        try:
            raw = uploaded_file.getvalue()
            suffix = Path(uploaded_file.name).suffix.lower()
            if suffix in {".txt", ".md"}:
                content = raw.decode("utf-8", errors="replace")
            elif suffix == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw))
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
            else:
                from docx import Document
                document_docx = Document(io.BytesIO(raw))
                content = "\n".join(p.text for p in document_docx.paragraphs if p.text.strip())
            if len(content.strip()) < 40:
                raise ValueError("Não foi possível extrair texto suficiente. PDFs digitalizados exigem OCR externo.")
            digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
            document = {"doc_id": f"upload_{slugify(Path(uploaded_file.name).stem)}_{digest}",
                        "title": Path(uploaded_file.name).stem, "content": content,
                        "source": uploaded_source or uploaded_file.name,
                        "source_label": f"Documento enviado: {uploaded_file.name}"}
            prepared = prepare_documents([document])
            store.ensure_schema()
            summary = store.ingest(prepared, embedder)
            get_resources.clear()
            st.success(f"Documento ingerido: {summary['entities']} entidades e {summary['relations']} relações extraídas.")
            st.rerun()
        except Exception as exc:
            st.error(f"Falha ao processar documento: {exc}")
    st.divider()
    st.markdown("**Perguntas sugeridas**")
    st.markdown("- O que o GraphRAG combina?")
    st.markdown("- Como Neo4j representa conhecimento usando LPG e Cypher?")
    st.markdown("- Como funciona a recuperação híbrida?")
    st.markdown("- Como consultar conexões em múltiplos saltos?")
    st.divider()
    st.caption("Corpus de demonstração com resumos técnicos e referências públicas. A confiança é heurística, não probabilidade calibrada.")

if connected:
    try:
        stats = store.stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Documentos", stats.get("documents", 0))
        c2.metric("Entidades", stats.get("entities", 0))
        c3.metric("Relacionamentos", stats.get("relationships", 0))
        c4.metric("Saltos máximos", settings.max_graph_hops)
    except Exception as exc:
        st.warning(f"Não foi possível obter estatísticas: {exc}")

st.divider()
with st.form("question_form"):
    question = st.text_input("Faça uma pergunta sobre o corpus", placeholder="Ex.: Como GraphRAG conecta documentos por meio de um grafo?")
    submitted = st.form_submit_button("Consultar base de conhecimento", type="primary", disabled=not connected)

if submitted:
    if not question.strip():
        st.warning("Digite uma pergunta para continuar.")
    else:
        try:
            with st.spinner("Recuperando documentos, combinando rankings e percorrendo o grafo..."):
                plan = None
                plan_source = "Planejador heurístico + compilador Cypher seguro"
                if ollama is not None:
                    try:
                        recognized = [m.name for m in extractor.extract_entities(question)]
                        plan = ollama.plan(question, recognized)
                        plan_source = f"Planejador LLM ({settings.ollama_model}) + compilador Cypher seguro"
                    except Exception:
                        plan = None
                result = retriever.retrieve(question, plan=plan)
                answer, generation_source = generate_answer(question, result, ollama)
            st.session_state["last_result"] = result
            st.session_state["last_answer"] = answer
            st.session_state["last_generation_source"] = generation_source
            st.session_state["last_plan_source"] = plan_source
        except Exception as exc:
            st.exception(exc)

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    confidence = result["confidence"]
    st.subheader("Resposta fundamentada")
    left, right = st.columns([3, 1])
    with left:
        st.markdown(st.session_state["last_answer"])
    with right:
        st.metric("Suporte heurístico", f"{confidence['score'] * 100:.0f}/100", confidence["label"])
        st.progress(float(confidence["score"]))
        st.caption(confidence["explanation"])
    st.caption(f"Geração: {st.session_state['last_generation_source']} • Planejamento: {st.session_state['last_plan_source']}")

    tab_sources, tab_graph, tab_trace = st.tabs(["Fontes recuperadas", "Subgrafo de contexto", "Rastreabilidade técnica"])
    with tab_sources:
        if not result["documents"]:
            st.warning("Nenhum documento foi recuperado.")
        for index, doc in enumerate(result["documents"], start=1):
            with st.expander(f"[E{index}] {doc['title']} · RRF {doc['rrf_score']}", expanded=index == 1):
                st.write(doc["content"])
                if doc.get("source"):
                    st.markdown(f"Fonte: [{doc.get('source_label', 'referência')}]({doc['source']})")
    with tab_graph:
        if not result["graph_nodes"]:
            st.info("Não foi encontrado subgrafo para os documentos recuperados. Confira se a ingestão foi concluída.")
        else:
            try:
                from pyvis.network import Network
                net = Network(height="520px", width="100%", directed=True, bgcolor="#0b1220", font_color="#f8fafc")
                type_colors = {"Architecture": "#7dd3fc", "Technology": "#86efac", "Concept": "#c4b5fd",
                               "Algorithm": "#fcd34d", "Language": "#fda4af", "DataModel": "#fdba74"}
                for node in result["graph_nodes"]:
                    net.add_node(node["id"], label=node["name"], title=f"{node.get('entity_type')} · PageRank {node.get('pagerank', 0)}",
                                 color=type_colors.get(node.get("entity_type"), "#cbd5e1"), size=22)
                for edge in result["graph_edges"]:
                    source_id = edge.get("source_id")
                    target_id = edge.get("target_id")
                    if source_id and target_id:
                        evidence = edge.get("evidence", "")
                        net.add_edge(source_id, target_id, label=edge.get("type", ""), title=evidence, arrows="to")
                net.set_options('{"physics":{"stabilization":true,"barnesHut":{"gravitationalConstant":-5000,"springLength":130}},"interaction":{"hover":true,"navigationButtons":true}}')
                components.html(net.generate_html(), height=540, scrolling=True)
            except ImportError:
                st.warning("PyVis não instalado. Instale `requirements.txt` para habilitar a visualização interativa.")
            if result["graph_edges"]:
                st.markdown("**Relações e evidências**")
                for edge in result["graph_edges"]:
                    st.markdown(f"- `{edge.get('source_id')}` —**{edge.get('type')}**→ `{edge.get('target_id')}`  \n  Evidência: “{edge.get('evidence', '')}”")
    with tab_trace:
        st.markdown("**Cypher compilada**")
        st.code(result["cypher"], language="cypher")
        st.markdown("**Parâmetros vinculados**")
        st.json(result.get("cypher_params", {}))
        st.markdown("**Métricas de recuperação**")
        st.json(result["retrieval"])
        st.markdown("**Entidades centrais no subgrafo (PageRank)**")
        if result["graph_nodes"]:
            st.dataframe([{"Entidade": n["name"], "Tipo": n["entity_type"], "PageRank": n.get("pagerank", 0)}
                          for n in result["graph_nodes"]], use_container_width=True, hide_index=True)
        st.caption("A consulta Cypher é compilada a partir de um plano limitado (vizinhança ou caminho mais curto), usa parâmetros e opera em transação somente leitura. O modo Ollama pode sugerir o plano, mas não recebe permissão para executar Cypher arbitrária.")

st.divider()
st.caption("CompGraph • Projeto acadêmico GraphRAG/KAG • Corpus demonstrativo versionado em data/corpus.jsonl")
