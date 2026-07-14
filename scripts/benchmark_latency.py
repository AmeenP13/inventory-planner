import sys
import time
import sqlite3
import requests
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import Agent and RAG modules
from src.services.agentic_ai.agents.inventory_agent import inventory_agent
from src.services.agentic_ai.agents.demand_agent import demand_agent
from src.services.agentic_ai.agents.risk_agent import risk_analysis
from src.services.agentic_ai.agents.rag_agent import rag_agent
from src.services.agentic_ai.agents.recommendation import recommendation_agent
from src.services.rag_policy.search import search_policy

DB_PATH = ROOT_DIR / "data" / "inventory.db"
API_URL = "http://127.0.0.1:8000"


def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, "#"))
    print("=" * 60)


def profile_database():
    print_header("1. SQLite Database Latency Profile")
    if not DB_PATH.exists():
        print("Database not found! Run scripts/seed_database.py first.")
        return

    # Connection speed
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    conn_time = (time.time() - t0) * 1000
    print(f"[*] SQLite Connection Open Time: {conn_time:.2f} ms")

    # Simple Query (Products List)
    t0 = time.time()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    prod_time = (time.time() - t0) * 1000
    print(f"[*] Query 'SELECT * FROM products' (Count: {len(products)}): {prod_time:.2f} ms")

    # Large/Complex Query (9000 daily inventory + sales records join)
    t0 = time.time()
    cursor.execute("""
        SELECT i.date, p.product_name, i.current_stock, COALESCE(s.quantity_sold, 0)
        FROM inventory_daily i
        JOIN products p ON i.product_id = p.product_id
        LEFT JOIN sales s ON i.product_id = s.product_id AND i.date = s.date
    """)
    records = cursor.fetchall()
    join_time = (time.time() - t0) * 1000
    print(f"[*] Heavy Join Query (9000 rows): {join_time:.2f} ms")

    conn.close()


def profile_rag():
    print_header("2. Chroma Vector DB (RAG) Latency Profile")
    query = "What is the policy for safety stock when risk is High?"

    try:
        # First similarity search (may load model if not cached in process)
        t0 = time.time()
        policy_1 = search_policy(query)
        rag_1_time = (time.time() - t0) * 1000
        print(f"[*] Vector Similarity Search (First load): {rag_1_time:.2f} ms")

        # Second similarity search (uses memory cache)
        t0 = time.time()
        policy_2 = search_policy(query)
        rag_2_time = (time.time() - t0) * 1000
        print(f"[*] Vector Similarity Search (Cached): {rag_2_time:.2f} ms")
        print(f"[i] Retrieved Policy Snippet: '{policy_2[:60]}...'")
    except Exception as e:
        print(f"[!] RAG Profiling failed (Probably missing or invalid GEMINI_API_KEY): {e}")


def profile_agent_nodes():
    print_header("3. LangGraph Agent Node Latency Profile")
    state = {
        "message": ["Banana Chips"],
        "inventory": {},
        "all_dates_inventory": [],
        "demand": {},
        "risk": "",
        "policy": "",
        "recommendation": "",
        "error": None,
    }

    try:
        # Node 1: Inventory Agent
        t0 = time.time()
        state = inventory_agent(state)
        node1_time = (time.time() - t0) * 1000
        print(f"[*] Node 1: inventory_agent: {node1_time:.2f} ms")

        # Node 2: Demand Agent
        t0 = time.time()
        state = demand_agent(state)
        node2_time = (time.time() - t0) * 1000
        print(f"[*] Node 2: demand_agent: {node2_time:.2f} ms")

        # Node 3: Risk Agent
        t0 = time.time()
        state = risk_analysis(state)
        node3_time = (time.time() - t0) * 1000
        print(f"[*] Node 3: risk_agent: {node3_time:.2f} ms")

        # Node 4: RAG Agent
        t0 = time.time()
        state = rag_agent(state)
        node4_time = (time.time() - t0) * 1000
        print(f"[*] Node 4: rag_agent: {node4_time:.2f} ms")

        # Node 5: Recommendation Agent (LLM Call)
        t0 = time.time()
        state = recommendation_agent(state)
        node5_time = (time.time() - t0) * 1000
        print(f"[*] Node 5: recommendation_agent (LLM call/fallback): {node5_time:.2f} ms")
    except Exception as e:
        print(f"[!] Agent Node Profiling failed (Probably missing or invalid GEMINI_API_KEY): {e}")


def profile_fastapi():
    print_header("4. FastAPI Backend Endpoint Latency Profile")
    endpoints = [
        ("GET / (Root)", "/"),
        ("GET /api/overview", "/api/overview"),
        ("GET /api/inventory_report", "/api/inventory_report"),
        ("GET /api/proposal", "/api/proposal"),
    ]

    for label, path in endpoints:
        t0 = time.time()
        try:
            res = requests.get(f"{API_URL}{path}", timeout=10)
            status = res.status_code
        except Exception as e:
            status = f"FAILED ({e})"
        latency = (time.time() - t0) * 1000
        print(f"[*] Request {label} -> Status {status}: {latency:.2f} ms")


def profile_frontend():
    print_header("5. Simulated Frontend Request Latency")
    # Measures the round-trip latency including network and json parsing overhead
    t0 = time.time()
    try:
        res = requests.get(f"{API_URL}/api/overview", timeout=10)
        data = res.json()
        status = "OK"
    except Exception as e:
        status = "FAILED"
    rtt = (time.time() - t0) * 1000
    print(f"[*] Frontend-to-Backend HTTP Round Trip (json parse): {rtt:.2f} ms")


def main():
    print("=" * 60)
    print(" STOCKMIND SYSTEM PERFORMANCE & LATENCY BENCHMARK ".center(60, "*"))
    print("=" * 60)

    profile_database()
    profile_rag()
    profile_agent_nodes()
    profile_fastapi()
    profile_frontend()

    print("\n" + "=" * 60)
    print(" BENCHMARK COMPLETED ".center(60, "*"))
    print("=" * 60)


if __name__ == "__main__":
    main()
