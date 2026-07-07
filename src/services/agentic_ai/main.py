import os
import sys

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

if project_root not in sys.path:
    sys.path.insert(0, project_root)


from langchain_core.messages import HumanMessage
from src.services.agentic_ai.graph import graph

def main():
    print('Autonomous AI inventory')
    
    while True:
        user_input=input("\nEnter Product Name (or Type Exit):").strip()
        
        if user_input.lower() in {'exit','bye','quit'}:
            print('\nExiting browser')
            break
        state = {
            "message": [HumanMessage(content=user_input)],
            "inventory": {},
            "all_dates_inventory": [],
            "next_day_inventory": {},
            "demand": {},
            "risk": "",
            "policy": "",
            "recommendation": "",
            "error": None,
        }
        
        result=graph.invoke(state)
        
        if result.get('error'):
            print(f'\nError :{result['error']}')
        else:
            print(result['recommendation'])
            
if __name__=='__main__':
    main()
        