"""
database.py
-----------
Handles the SQLite connection and SQLAlchemy engine/session setup for the FastAPI app.
"""

from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# inventory.db sits in the root data/ folder
DB_PATH = Path(__file__).resolve().parent.parent.parent / \
    "data" / "inventory.db"

# SQLAlchemy engine & session configuration
# check_same_thread: False is necessary for SQLite when accessed by multi-threaded FastAPI app
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency that yields a new database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for obtaining a database session outside of FastAPI HTTP request context (e.g. agents)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
