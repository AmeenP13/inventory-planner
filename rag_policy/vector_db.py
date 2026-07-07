from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

DB_PATH = "rag_policy/chroma_db"


def load_vector_db():
    try:

        embedding_model = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        vector_db = Chroma(
            persist_directory=DB_PATH,
            embedding_function=embedding_model
        )

        return vector_db

    except Exception as e:
        print(f"Error loading Vector Database: {e}")
        return None