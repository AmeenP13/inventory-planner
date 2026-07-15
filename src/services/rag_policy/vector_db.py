from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "chroma_db"


_VECTOR_DB_CACHE = None

def load_vector_db():
    global _VECTOR_DB_CACHE
    if _VECTOR_DB_CACHE is not None:
        return _VECTOR_DB_CACHE

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    _VECTOR_DB_CACHE = Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=embedding_model,
        collection_name="inventory_policies"
    )

    print(f"Database Path : {DB_PATH}")
    print(f"Documents in Vector DB : {_VECTOR_DB_CACHE._collection.count()}")

    return _VECTOR_DB_CACHE


if __name__ == "__main__":

    load_vector_db()