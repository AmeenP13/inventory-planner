from graph import graph

state = {
    "message": [],
    "inventory": {},
    "demand": {},
    "risk": "",
    "policy": "",
    "recommendation": "",
    "error": ""
}
while True:
    user_input = input("Ask More details about product: ")
    if user_input.lower().strip() in {"quit", "bye", "exit"}:
        print("Exiting browser")
        break
    state["message"].append(user_input)
    result = graph.invoke(state)
    state = result
    if result.get("error"):
        print("\nERROR:", result["error"])
    else:
        print("\nAI Inventory Recommendation")
        print(result.get("recommendation", "No output generated"))