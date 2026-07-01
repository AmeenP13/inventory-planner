from vector_db import vector_db

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