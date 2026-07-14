from sqlite_db import keyword_search
from vector_db import load_vector_db


def search_policy(query):
    """
    Hybrid Search

    1. SQLite performs keyword search.
    2. Retrieves the best matching policy_id.
    3. Chroma fetches the complete policy using metadata.
    """

    try:

        if not query or not query.strip():
            return {
                "status": "error",
                "message": "Query cannot be empty."
            }

        # -----------------------------
        # Step 1 : SQLite Keyword Search
        # -----------------------------

        policy = keyword_search(query)

        if policy is None:
            return {
                "status": "error",
                "message": "No matching policy found."
            }

        policy_id = policy["policy_id"]

        # -----------------------------
        # Step 2 : Load Chroma Database
        # -----------------------------

        vector_db = load_vector_db()

        # -----------------------------
        # Step 3 : Retrieve Policy
        # -----------------------------

        results = vector_db.get(
            where={
                "policy_id": policy_id
            }
        )

        if len(results["documents"]) == 0:
            return {
                "status": "error",
                "message": "Policy not found in Vector Database."
            }

        metadata = results["metadatas"][0]
        content = results["documents"][0]

        return {
            "status": "success",
            "result": {
                "policy_id": metadata.get("policy_id"),
                "policy_type": metadata.get("policy_type"),
                "product": metadata.get("product"),
                "page": metadata.get("page", "N/A"),
                "source": metadata.get("source"),
                "content": content
            }
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":

    test_query = "Overstock Limit Grapes"

    response = search_policy(test_query)

    print(response)