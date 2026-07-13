from pathlib import Path
import re

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR / "policies" / "Company_Inventory_Policies_1000.pdf"
DB_PATH = BASE_DIR / "chroma_db"


def extract_metadata(text):
    """
    Extract metadata from policy text.

    Example:
    POL-0430Overstock Limit [Grapes]:
    """

    metadata = {}

    text = text.replace("\n", " ").strip()

    pattern = r"(POL-\d+)(.*?)\[(.*?)\]"

    match = re.search(pattern, text)

    if match:
        metadata["policy_id"] = match.group(1).strip()
        metadata["policy_type"] = match.group(2).replace(":", "").strip()
        metadata["product"] = match.group(3).strip()

    return metadata


def ingest_policies():

    try:

        if not PDF_PATH.exists():
            print("Error: Policy PDF not found.")
            return

        print("Loading PDF...")

        loader = PyPDFLoader(str(PDF_PATH))
        documents = loader.load()

        if not documents:
            print("Error: PDF is empty.")
            return

        print(f"Pages Loaded: {len(documents)}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        chunks = splitter.split_documents(documents)

        if not chunks:
            print("Error: No chunks created.")
            return

        print(f"Chunks Created: {len(chunks)}")

        print("Adding metadata...")

        for chunk in chunks:

            metadata = extract_metadata(chunk.page_content)

            chunk.metadata.update(metadata)

            chunk.metadata["source"] = PDF_PATH.name

        print("Loading embedding model...")

        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        print("Creating Chroma Database...")

        Chroma.from_documents(
            documents=chunks,
            embedding=embedding_model,
            persist_directory=str(DB_PATH)
        )

        print("Vector Database Created Successfully!")
        print(f"Total Chunks Stored: {len(chunks)}")

    except Exception as e:
        print(f"Unexpected Error: {e}")


if __name__ == "__main__":
    ingest_policies()