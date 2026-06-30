-- ============================================================
-- Inventory Replenishment Agent — Database Schema
-- Database & API Architect — Day 1
-- ============================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id     TEXT PRIMARY KEY,
    supplier_name   TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    cost_price       REAL NOT NULL,
    base_price       REAL NOT NULL,
    supplier_id      TEXT NOT NULL,
    avg_lead_time_day INTEGER NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS inventory_daily (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,
    current_stock   INTEGER NOT NULL,
    expiry_date     TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE (product_id, date)
);

CREATE TABLE IF NOT EXISTS sales (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,
    quantity_sold   INTEGER NOT NULL,
    customer_rating REAL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE (product_id, date)
);

CREATE INDEX IF NOT EXISTS idx_inventory_product_date ON inventory_daily(product_id, date);
CREATE INDEX IF NOT EXISTS idx_sales_product_date ON sales(product_id, date);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id);