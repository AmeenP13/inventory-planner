"""
database.py
------------
Handles the SQLite connection for the FastAPI app.
"""

import sqlite3
from pathlib import Path

# inventory.db sits one level up from app/, inside backend/
DB_PATH = Path(__file__).resolve().parent.parent / "inventory.db"


def get_connection():
    """Returns a new SQLite connection with rows accessible by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn