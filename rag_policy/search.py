from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

embedding_model = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vector_db = Chroma(
    persist_directory="rag_policy/chroma_db",
    embedding_function=embedding_model
)

def search_policy(user_query):

    results = vector_db.similarity_search(
        user_query,
        k=1
    )

    if results:
        return results[0].page_content

    return "No policy found."


if __name__ == "__main__":

    query = "What should I do if inventory is below 5 days?"

    answer = search_policy(query)

    print("\nQuestion:")
    print(query)

    print("\nRetrieved Policy:")
    print(answer)