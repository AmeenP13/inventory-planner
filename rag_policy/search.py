from vector_db import load_vector_db


def search_policy(user_query):

    try:

        if not user_query.strip():
            return "Error: Query cannot be empty."

        vector_db = load_vector_db()

        if vector_db is None:
            return "Error: Unable to load Vector Database."

        results = vector_db.similarity_search(
            user_query,
            k=1
        )

        if len(results) == 0:
            return "No policy found."

        answer = ""
        for i, doc in enumerate(results, start=1):

            answer += f"\nResult {i}\n"
            answer += doc.page_content
            answer += "\n"

        return answer

    except Exception as e:
        return f"Unexpected Error: {e}"


if __name__ == "__main__":

    while True:

        query = input("\nEnter your question (type 'exit' to quit): ")

        if query.lower() == "exit":
            print("Exiting...")
            break

        result = search_policy(query)

        print("\nRetrieved Policies:")
        print(result)