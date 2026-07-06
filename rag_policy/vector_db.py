from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_DIR = Path("rag_policy/chroma_db")


def _ensure_vector_store() -> None:
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        from rag_policy.ingest import main as build_policy_db

        print("Chroma vector store not found. Building from policy documents...")
        build_policy_db()


def get_vector_db() -> Chroma:
    _ensure_vector_store()
    embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embedding_model,
    )