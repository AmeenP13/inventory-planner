from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import threading

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"

_VECTOR_DB = None
_db_lock = threading.Lock()


def _ensure_vector_store() -> None:
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        from .ingest import main as build_policy_db

        print("Chroma vector store not found. Building from policy documents...")
        build_policy_db()


def get_vector_db() -> Chroma:
    global _VECTOR_DB
    if _VECTOR_DB is None:
        with _db_lock:
            if _VECTOR_DB is None:
                _ensure_vector_store()
                embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
                _VECTOR_DB = Chroma(
                    persist_directory=str(CHROMA_DIR),
                    embedding_function=embedding_model,
                )
    return _VECTOR_DB

