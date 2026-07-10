from dotenv import load_dotenv
load_dotenv()

try:
    from .vector_db import get_vector_db
except ImportError:
    from vector_db import get_vector_db


def search_policy(user_query: str) -> str:
    import os

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("Google Gemini API Key is not configured.")

    try:
        print(f"[RAG] Searching policy for: {user_query}")

        vector_db = get_vector_db()
        results = vector_db.similarity_search(user_query, k=1)

        print(f"[RAG] Results found: {len(results)}")

        if results:
            print(f"[RAG] Policy: {results[0].page_content}")
            return results[0].page_content

    except Exception as e:
        print(f"[RAG ERROR] {e}")

    return "No policy found."


if __name__ == "__main__":
    query = "What should I do if inventory is below 5 days?"
    answer = search_policy(query)

    print("\nQuestion:")
    print(query)

    print("\nRetrieved Policy:")
    print(answer)