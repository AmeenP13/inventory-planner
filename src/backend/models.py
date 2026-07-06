"""
models.py
----------
Pydantic models define the JSON "shape" for every API response.
This is the contract the Frontend and Agent developers will rely on.
"""

from pydantic import BaseModel
from typing import Optional


class Product(BaseModel):
    product_id: int
    product_name: str
    cost_price: float
    base_price: float
    supplier_id: str
    avg_lead_time_day: int


class Supplier(BaseModel):
    supplier_id: str
    supplier_name: Optional[str] = None


class InventoryRecord(BaseModel):
    product_id: int
    date: str
    current_stock: int
    expiry_date: Optional[str] = None


class SalesRecord(BaseModel):
    product_id: int
    date: str
    quantity_sold: int
    customer_rating: Optional[float] = None


class InventoryUpdate(BaseModel):
    product_id: int
    date: str
    current_stock: int
    expiry_date: Optional[str] = None


class OrderApproval(BaseModel):
    product_id: int
    quantity: int
    supplier_id: str
    notes: Optional[str] = None