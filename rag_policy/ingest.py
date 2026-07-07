from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma


PDF_PATH = "rag_policy/policies/Company_Inventory_Policies_1000.pdf"
DB_PATH = "rag_policy/chroma_db"


def ingest_policies():
    try:
        pdf_file = Path(PDF_PATH)

        # Check if PDF exists
        if not pdf_file.exists():
            print("Error: Policy PDF not found.")
            return

        print("Loading PDF...")

        loader = PyPDFLoader(PDF_PATH)
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
            print("Error: No chunks were created.")
            return

        print(f"Chunks Created: {len(chunks)}")

        print("Loading embedding model...")

        embedding_model = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        print("Creating Chroma Database...")

        Chroma.from_documents(
            documents=chunks,
            embedding=embedding_model,
            persist_directory=DB_PATH
        )

        print("Vector Database Created Successfully!")
        print(f"Total Chunks Stored: {len(chunks)}")

    except Exception as e:
        print(f"Unexpected Error: {e}")


if __name__ == "__main__":
    ingest_policies()