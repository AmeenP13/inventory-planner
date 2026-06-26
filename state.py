from langgraph.graph.message import add_messages
from typing import TypedDict,Annotated
class state(TypedDict):
    message:Annotated[list,add_messages]
    inventory:dict
    demand:dict
    risk:str
    policy:str
    recommented:str