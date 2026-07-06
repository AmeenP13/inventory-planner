from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated, List, Dict, Any, Optional
class State(TypedDict):
    message: Annotated[list, add_messages]
    inventory: Dict[str, Any]
    all_dates_inventory: Optional[List[Dict[str, Any]]]
    next_day_inventory: Optional[Dict[str, Any]]
    demand: Dict[str, float]
    risk: str
    policy: str
    recommendation: str
    error: Optional[str]