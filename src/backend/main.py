"""
main.py
-------
FastAPI application entry point.

Creates the app, registers middleware, and mounts all routers.
Business logic lives in the router modules under src/backend/routers/.
Shared cache state and helpers live in src/backend/cache.py.
"""

import time
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routers import crud, reports, agent, analytics


# ── Lifespan: pre-load vector DB in a background thread ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Pre-loading Chroma vector database and HuggingFace embedding model...")
    try:
        from src.services.rag_policy.vector_db import get_vector_db
        t = threading.Thread(target=get_vector_db, daemon=True)
        t.start()
    except Exception as e:
        print(f"Error pre-loading vector database: {e}")
    yield


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Inventory Replenishment Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed * 1000:.2f}ms"
    print(
        f"[HTTP LOG] {request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- Completed in {elapsed * 1000:.2f}ms"
    )
    return response


@app.get("/")
def root():
    return {"message": "Inventory Replenishment Agent API is running"}


# ── Mount routers ─────────────────────────────────────────────────────
app.include_router(crud.router)
app.include_router(reports.router)
app.include_router(agent.router)
app.include_router(analytics.router)
