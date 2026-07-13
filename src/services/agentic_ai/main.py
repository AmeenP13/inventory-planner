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
    print('Autonomous AI Inventory')
    
    while True:
        user_input=input('Enter Product Names (or Type Exit):')
        
        if user_input.strip().lower() in{'quit','exit','bye'}:
            print('Exiting Browser')
            break
        
        state={
            'message':[HumanMessage(content=user_input)],
            'inventory':{},
            'all_dates_inventory':[],
            'next_day_inventory':{},
            'demand':{},
            'risk':'',
            'recommendation':'',
            'error':None,
            
        }
        
        try:
            result=graph.invoke(state)
            
            if result.get('error'):
                print(f"\nError:'{result['error']}")
                break
            else:
                print('\n'+result['recommendation'])
                
        except Exception as e:
            print(f'\nUnexcepted Error:{e}')
            
if __name__=='__main__':
    main()