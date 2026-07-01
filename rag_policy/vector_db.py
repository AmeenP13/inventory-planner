from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

# Load embedding model
embedding_model = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# Load existing Chroma database
vector_db = Chroma(
    persist_directory="rag_policy/chroma_db",
    embedding_function=embedding_model
)