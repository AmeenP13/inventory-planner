import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

POLICY_FOLDER = Path(__file__).resolve().parent / "policies"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50


def _ensure_hf_token() -> None:
    if not os.environ.get("HF_TOKEN"):
        print(
            "Warning: set HF_TOKEN in your environment to avoid unauthenticated HF Hub requests."
        )


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


def _create_embedding_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def _create_vector_db(chunks: list[str], embedding_model: HuggingFaceEmbeddings) -> Chroma:
    return Chroma.from_texts(
        texts=chunks,
        embedding=embedding_model,
        persist_directory=str(CHROMA_DIR),
    )


def main() -> None:
    _ensure_hf_token()

    policy_chunks = _load_policy_documents(POLICY_FOLDER)
    if not policy_chunks:
        print("No policy documents found.")
        return

    print("\nLoading embedding model...")
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