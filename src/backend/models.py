"""
models.py
----------
Defines both:
1. SQLAlchemy ORM models for database mapping.
2. Pydantic models to define the JSON shapes for API requests/responses.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


# =====================================================================
# 1. SQLALCHEMY ORM MODELS
# =====================================================================

class SupplierORM(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(String, primary_key=True)
    supplier_name = Column(String, nullable=True)

    products = relationship("ProductORM", back_populates="supplier")


class ProductORM(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    cost_price = Column(Float, nullable=False)
    base_price = Column(Float, nullable=False)
    supplier_id = Column(String, ForeignKey("suppliers.supplier_id"), nullable=False)
    avg_lead_time_day = Column(Integer, nullable=False)

    supplier = relationship("SupplierORM", back_populates="products")
    inventory_records = relationship("InventoryDailyORM", back_populates="product")
    sales_records = relationship("SalesORM", back_populates="product")


class InventoryDailyORM(Base):
    __tablename__ = "inventory_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    date = Column(String, nullable=False)
    current_stock = Column(Integer, nullable=False)
    expiry_date = Column(String, nullable=True)

    product = relationship("ProductORM", back_populates="inventory_records")

    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_inventory_product_date"),
    )


class SalesORM(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    date = Column(String, nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    customer_rating = Column(Float, nullable=True)

    product = relationship("ProductORM", back_populates="sales_records")

    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_sales_product_date"),
    )


# =====================================================================
# 2. PYDANTIC SCHEMAS (API CONTRACTS)
# =====================================================================

class Product(BaseModel):
    product_id: int
    product_name: str
    cost_price: float
    base_price: float
    supplier_id: str
    avg_lead_time_day: int

    # Config for Pydantic v2 ORM mapping
    model_config = ConfigDict(from_attributes=True)


class Supplier(BaseModel):
    supplier_id: str
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryRecord(BaseModel):
    product_id: int
    date: str
    current_stock: int
    expiry_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesRecord(BaseModel):
    product_id: int
    date: str
    quantity_sold: int
    customer_rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryUpdate(BaseModel):
    product_id: int
    date: str
    current_stock: int
    expiry_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderApproval(BaseModel):
    product_id: int
    quantity: int
    supplier_id: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
