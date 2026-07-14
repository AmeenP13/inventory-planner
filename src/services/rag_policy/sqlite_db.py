from pathlib import Path
import sqlite3
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "policy_metadata.db"


def get_connection():
    """
    Create SQLite connection.
    """
    return sqlite3.connect(DB_PATH)


def create_table():
    """
    Create metadata table if it doesn't exist.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (

            policy_id TEXT PRIMARY KEY,

            policy_type TEXT NOT NULL,

            product TEXT NOT NULL,

            page INTEGER,

            source TEXT

        )
    """)

    conn.commit()
    conn.close()


def insert_policy(metadata):
    """
    Insert one policy metadata into SQLite.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO policies(

            policy_id,

            policy_type,

            product,

            page,

            source

        )
        VALUES (?, ?, ?, ?, ?)
    """,
    (
        metadata.get("policy_id"),
        metadata.get("policy_type"),
        metadata.get("product"),
        metadata.get("page"),
        metadata.get("source")
    ))

    conn.commit()
    conn.close()


def keyword_search(query):
    """
    Keyword search with scoring.
    Returns only the best matching policy.
    """

    keywords = query.lower().split()

    conn = get_connection()
    cursor = conn.cursor()

    scores = defaultdict(lambda: {

        "score": 0,

        "policy_id": "",

        "policy_type": "",

        "product": "",

        "page": "",

        "source": ""

    })

    for keyword in keywords:

        cursor.execute("""
            SELECT

                policy_id,

                policy_type,

                product,

                page,

                source

            FROM policies

            WHERE

                LOWER(policy_id) LIKE ?

                OR LOWER(policy_type) LIKE ?

                OR LOWER(product) LIKE ?

        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%"
        ))

        rows = cursor.fetchall()

        for row in rows:

            pid = row[0]

            scores[pid]["score"] += 1

            scores[pid]["policy_id"] = row[0]
            scores[pid]["policy_type"] = row[1]
            scores[pid]["product"] = row[2]
            scores[pid]["page"] = row[3]
            scores[pid]["source"] = row[4]

    conn.close()

    if not scores:
        return None

    best_policy = max(
        scores.values(),
        key=lambda x: x["score"]
    )

    best_policy.pop("score")

    return best_policy


if __name__ == "__main__":

    create_table()

    result = keyword_search("Overstock Limit Grapes")

    print(result)