from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "chroma_db"


def load_vector_db():

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    vector_db = Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=embedding_model
    )

    print(f"Database Path: {DB_PATH}")
    print(f"Documents in DB: {vector_db._collection.count()}")

    return vector_db