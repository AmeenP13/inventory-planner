from state import state
import pandas as pd
def inventory_agent(state:state):
    df=pd.read_csv("agenticAI/data/final_inventory_dataset_real_products.csv")
    product=df.iloc[0].to_dict()
    state['inventory']=product
    return state
