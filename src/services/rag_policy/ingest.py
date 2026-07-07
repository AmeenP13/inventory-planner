import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import shutil

POLICY_FOLDER = Path(__file__).resolve().parent / "policies"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db_genai"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50


def _load_policy_documents(policy_path: Path) -> list[str]:
    chunks = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    for file in policy_path.glob("*.txt"):
        print(f"\nReading: {file.name}")
        text = file.read_text(encoding="utf-8")
        file_chunks = splitter.split_text(text)
        print(f"Number of chunks: {len(file_chunks)}")
        chunks.extend(file_chunks)

    return chunks


def _create_embedding_model() -> GoogleGenerativeAIEmbeddings:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "dummy"
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )


def _create_vector_db(
        chunks: list[str],
        embedding_model: GoogleGenerativeAIEmbeddings) -> Chroma:
    if CHROMA_DIR.exists():
        print(f"Removing old vector index directory at {CHROMA_DIR}")
        shutil.rmtree(CHROMA_DIR)

    return Chroma.from_texts(
        texts=chunks,
        embedding=embedding_model,
        persist_directory=str(CHROMA_DIR),
    )


def main() -> None:
    policy_chunks = _load_policy_documents(POLICY_FOLDER)
    if not policy_chunks:
        print("No policy documents found.")
        return

    print("\nLoading Google GenAI embedding model...")
    embedding_model = _create_embedding_model()
    print("Embedding model loaded successfully.")

    print("\nCreating Chroma Vector Database...")
    vector_db = _create_vector_db(policy_chunks, embedding_model)
    if hasattr(vector_db, "persist"):
        vector_db.persist()

    print("\nPolicies stored successfully in ChromaDB!")
    print(f"\nTotal chunks stored: {len(policy_chunks)}")


if __name__ == "__main__":
    main()
