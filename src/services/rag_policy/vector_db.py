
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "chroma_db"

import os
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

_VECTOR_DB = None

def load_vector_db():
    """
    Load the Chroma Vector DB using the local HuggingFace embeddings.
    """
    global _VECTOR_DB
    if _VECTOR_DB is not None:
        return _VECTOR_DB
        
    try:
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        _VECTOR_DB = Chroma(
            persist_directory=str(DB_PATH),
            embedding_function=embedding_model
        )
        return _VECTOR_DB
    except Exception as e:
        print(f"Error loading vector database: {e}")
        return None

