from pathlib import Path
import re

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from sqlite_db import create_table, insert_policy

BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR / "policies" / "Company_Inventory_Policies_1000.pdf"
DB_PATH = BASE_DIR / "chroma_db"


def extract_metadata(text):
    """
    Extract metadata from both inventory policies
    and general system policies.
    """

    metadata = {}

    text = text.replace("\n", " ").strip()

    # Inventory policy
    inventory_pattern = r"(POL-\d+)\s*(.*?)\[(.*?)\]"

    match = re.search(inventory_pattern, text)

    if match:
        metadata["policy_id"] = match.group(1).strip()
        metadata["policy_type"] = match.group(2).replace(":", "").strip()
        metadata["product"] = match.group(3).strip()
        return metadata

    # General system policy
    generic_pattern = r"(POL-\d+)"

    match = re.search(generic_pattern, text)

    if match:
        metadata["policy_id"] = match.group(1)
        metadata["policy_type"] = "General Policy"
        metadata["product"] = "N/A"
        return metadata

    return {}


def split_policies(documents):
    """
    Split PDF into one Document per policy.
    """

    full_text = ""

    for doc in documents:
        full_text += "\n" + doc.page_content

    policy_texts = re.split(r"(?=POL-\d+)", full_text)

    policy_documents = []

    page_number = 1

    for policy in policy_texts:

        policy = policy.strip()

        if not policy.startswith("POL-"):
            continue

        metadata = extract_metadata(policy)

        if not metadata:
            continue

        metadata["page"] = page_number
        metadata["source"] = PDF_PATH.name

        page_number += 1

        policy_documents.append(
            Document(
                page_content=policy,
                metadata=metadata
            )
        )

    return policy_documents


def ingest_policies():

    try:

        if not PDF_PATH.exists():
            print("Policy PDF not found.")
            return

        print("Loading PDF...")

        loader = PyPDFLoader(str(PDF_PATH))
        documents = loader.load()

        print(f"Pages Loaded : {len(documents)}")

        print("Splitting Policies...")

        policy_documents = split_policies(documents)

        print(f"Policies Found : {len(policy_documents)}")

        print("Creating SQLite Database...")

        create_table()

        for policy in policy_documents:
            insert_policy(policy.metadata)

        print("SQLite Metadata Stored Successfully.")

        print("Loading Embedding Model...")

        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        print("Creating Chroma Vector Database...")

        vector_db = Chroma.from_documents(
            documents=policy_documents,
            embedding=embedding_model,
            persist_directory=str(DB_PATH),
            collection_name="inventory_policies"
        )

        print(f"Documents Stored : {vector_db._collection.count()}")

        print("Vector Database Created Successfully.")
        print(f"Total Policies Stored : {len(policy_documents)}")

    except Exception as e:

        print(f"Unexpected Error : {e}")


if __name__ == "__main__":
    ingest_policies()