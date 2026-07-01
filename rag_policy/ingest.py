from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma



# Step 1: Read Policy Documents


policy_folder = Path("rag_policy/policies")

all_chunks = []

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)

for file in policy_folder.glob("*.txt"):

    print(f"\nReading: {file.name}")

    text = file.read_text(encoding="utf-8")

    chunks = splitter.split_text(text)

    print(f"Number of chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {i}")
        print(chunk)

    all_chunks.extend(chunks)



# Step 2: Create Embedding Model


print("\nLoading embedding model...")

embedding_model = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("Embedding model loaded successfully.")


# Step 3: Store in ChromaDB

print("\nCreating Chroma Vector Database...")

vector_db = Chroma.from_texts(
    texts=all_chunks,
    embedding=embedding_model,
    persist_directory="rag_policy/chroma_db"
)

vector_db.persist()

print("\nPolicies stored successfully in ChromaDB!")

print(f"\nTotal chunks stored: {len(all_chunks)}")