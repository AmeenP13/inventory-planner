import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.services.agentic_ai.graph import graph
while True:
    user_input = input("Ask More details about product: ")
    if user_input.lower().strip() in {"quit", "bye", "exit"}:
        print("Exiting browser")
        break
    state = {
        "message": [user_input],
        "inventory": {},
        "all_dates_inventory": [],
        "demand": {},
        "risk": "",
        "policy": "",
        "recommendation": "",
        "error": ""
    }
    try:
        result = graph.invoke(state)
    except Exception as e:
        print("\nERROR calling agent graph:", e)
        continue

    if result.get("error"):
        print("\nERROR:", result["error"])
    else:
        print("\nAI Inventory Recommendation\n")
        print(result.get("recommendation", "No output generated"))