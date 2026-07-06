import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from typing import Any, Dict
from src.services.agentic_ai.graph import graph

EXIT_COMMANDS = {"quit", "bye", "exit"}


def build_initial_state(user_input: str) -> Dict[str, Any]:
    return {
        "message": [user_input],
        "inventory": {},
        "all_dates_inventory": [],
        "demand": {},
        "risk": "",
        "policy": "",
        "recommendation": "",
        "error": None,
    }


def should_exit(user_input: str) -> bool:
    return user_input.lower().strip() in EXIT_COMMANDS


def print_result(state: Dict[str, Any]) -> None:
    if state.get("error"):
        print("\nERROR:", state["error"])
        return

    print("\nAI Inventory Recommendation\n")
    print(state.get("recommendation", "No output generated"))


def main() -> None:
    while True:
        user_input = input("Enter product name: ").strip()
        if should_exit(user_input):
            print("Exiting browser")
            break
        if not user_input:
            print("Please enter a product name or type 'exit' to quit.")
            continue

        state = build_initial_state(user_input)
        try:
            result = graph.invoke(state)
        except Exception as e:
            print("\nERROR calling agent graph:", e)
            continue

        print_result(result)


if __name__ == "__main__":
    main()
