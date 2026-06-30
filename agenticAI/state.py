from langgraph.graph.message import add_messages
from typing import TypedDict,Annotated
class state(TypedDict):
    message:Annotated[list,add_messages]
    product_name:str
    inventory:str
    demand:dict
    risk:str
    recommendation:str
    response:str
    policy:str
    