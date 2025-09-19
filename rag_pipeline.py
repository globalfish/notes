import os
import json
from typing import Optional

from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.documents import Document

# Optional imports - only used when initializing
_pgvector = None
_huggingface = None
_ollama = None


def _load_settings(path: str = "settings.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_settings = _load_settings()

# Configurable values (env override -> settings.json -> fallback hard-coded)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or _settings.get("ollama_model") or "gemma3"
OLLAMA_HOST = os.getenv("OLLAMA_HOST") or _settings.get("ollama_host") or "http://localhost:11434"
PG_CONN = os.getenv("PG_CONN") or _settings.get("pg_conn") or "postgresql+psycopg://postgres:postgres@10.0.0.59:5433/notes?options=-csearch_path=private_gpt"
COLLECTION = os.getenv("VECTOR_COLLECTION") or _settings.get("vector_collection") or "meetingNotes"

# Model Download (Executed only once)
MODEL_NAME = _settings.get("hf_model_name") or os.getenv("HF_MODEL_NAME") or "sentence-transformers/all-MiniLM-L6-v2"
HF_MODEL_DIR = os.getenv("HF_MODEL_DIR") or _settings.get("hf_model_dir") or None


_embeddings = None
_store = None
_llm = None


def _init_embeddings():
    global _embeddings, _huggingface
    if _embeddings is None:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            _huggingface = HuggingFaceEmbeddings
            # If a local HF model dir is provided and exists, use it to avoid re-downloading
            model_ref = MODEL_NAME
            if HF_MODEL_DIR and os.path.exists(HF_MODEL_DIR):
                model_ref = HF_MODEL_DIR
            _embeddings = HuggingFaceEmbeddings(model_name=model_ref)
        except Exception:
            _embeddings = None
    return _embeddings


def _init_store():
    global _store, _pgvector
    if _store is None:
        try:
            from langchain_postgres import PGVector

            _pgvector = PGVector
            embeds = _init_embeddings()
            if embeds is None:
                raise RuntimeError("Embeddings unavailable")
            _store = PGVector(connection=PG_CONN, collection_name=COLLECTION, embeddings=embeds, use_jsonb=True)
        except Exception:
            _store = None
    return _store


def _init_llm():
    global _llm, _ollama
    if _llm is None:
        try:
            from langchain_ollama import ChatOllama

            _ollama = ChatOllama
            _llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST)
        except Exception:
            _llm = None
    return _llm


# Chat Prompt
prompt = ChatPromptTemplate.from_template(
    "You are a helpful assistant.  Context: {context} Question: {question} Answer:"
)


def get_chain(filters: Optional[dict] = None):
    """Return a runnable chain. Lazy-initializes the vector store and LLM. Raises RuntimeError if unavailable."""
    store = _init_store()
    llm = _init_llm()
    if store is None:
        raise RuntimeError("Vector store not initialized (check PG_CONN and dependencies)")
    if llm is None:
        raise RuntimeError("LLM not initialized (check OLLAMA_HOST/dependencies)")

    retriever = store.as_retriever(search_kwargs={"filter": filters}) if filters else store.as_retriever()
    return (
        RunnableParallel({
            "context": retriever,
            "question": RunnablePassthrough()
        }) | prompt | llm
    )


