import os
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import threading

CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db_genai"

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
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "dummy"
                embedding_model = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=api_key
                )
                _VECTOR_DB = Chroma(
                    persist_directory=str(CHROMA_DIR),
                    embedding_function=embedding_model,
                )
    return _VECTOR_DB
