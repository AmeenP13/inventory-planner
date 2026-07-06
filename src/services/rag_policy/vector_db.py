from pathlib import Path
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

# Load embedding model
embedding_model = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# Load existing Chroma database
DB_PATH = Path(__file__).resolve().parent / "chroma_db"
vector_db = Chroma(
    persist_directory=str(DB_PATH),
    embedding_function=embedding_model
)