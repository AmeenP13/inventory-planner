from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    message: Annotated[list, add_messages]

    inventory: Dict[str, Any]
    all_dates_inventory: Optional[List[Dict[str, Any]]]
    next_day_inventory: Optional[Dict[str, Any]]

    demand: Dict[str, Any]
    risk: str

    # NEW
    policy_query: str
    inventory_status: str

    policy: str
    policy_query: Optional[str]
    recommendation: str

    error: Optional[str]