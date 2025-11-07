# app/api_routes.py
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .schemas import StructuredReport
from .symptom_chain import run_extraction  # synchronous function
from .utils import detect_red_flags

# optional imports for retriever
try:
    import pinecone
    from sentence_transformers import SentenceTransformer
except Exception:
    pinecone = None
    SentenceTransformer = None

router = APIRouter()

# in-memory session store (replace with DB in prod)
SESSIONS = {}

# ThreadPoolExecutor to run blocking LLM/embedding tasks without blocking event loop
executor = ThreadPoolExecutor(max_workers=3)

# --- Session endpoints ---


@router.post("/symptom-session/start")
async def start_session(patient_id: Optional[str] = None, initial_text: str = ""):
    session_id = str(uuid4())
    SESSIONS[session_id] = {
        "patient_id": patient_id,
        "chat_history": initial_text or "Hello, what brings you today?",
        "created_at": datetime.utcnow().isoformat(),
        "status": "in_progress",
    }
    return {
        "session_id": session_id,
        "bot_message": SESSIONS[session_id]["chat_history"],
    }


@router.post("/symptom-session/{session_id}/message")
async def message(session_id: str, text: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    # append user's message
    session["chat_history"] += f"\nPatient: {text}\nBot: "

    # finalize when user indicates done
    if text.strip().lower() in ["done", "finish", "that's all", "i'm done"]:
        # run blocking extraction in threadpool
        parsed = await asyncio.get_event_loop().run_in_executor(
            executor, run_extraction, session["chat_history"]
        )

        # safety checks
        if detect_red_flags(parsed):
            parsed["urgency"] = "emergency"
            parsed["recommended_next_action"] = "go-to-emergency"

        session["structured"] = parsed
        session["status"] = "completed"
        return {"is_done": True, "structured": parsed}

    # otherwise return a placeholder bot question (replace with dynamic question-generation later)
    bot_q = "Can you tell me when the symptoms started?"
    session["chat_history"] += bot_q
    return {"is_done": False, "bot_message": bot_q}


# --- Retriever endpoint (optional) ---


class RetrieverQuery(BaseModel):
    text: str
    k: int = 5
    filter_tags: Optional[List[str]] = None


PINECONE_INDEX = os.getenv("PINECONE_INDEX", "medical-knowledge")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")

pinecone_index = None
embedder_for_retriever = None

if PINECONE_API_KEY and pinecone is not None:
    try:
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
        pinecone_index = pinecone.Index(PINECONE_INDEX)
    except Exception as e:
        pinecone_index = None
        print("Pinecone init error:", e)

if SentenceTransformer is not None:
    try:
        embedder_for_retriever = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        embedder_for_retriever = None
        print("Embedder init error:", e)


@router.post("/retriever/query")
async def retriever_query(body: RetrieverQuery):
    if pinecone_index is None or embedder_for_retriever is None:
        raise HTTPException(
            status_code=500,
            detail="Retriever not configured (Pinecone or embedder missing)",
        )

    def _sync_query():
        qvec = embedder_for_retriever.encode(body.text).tolist()
        res = pinecone_index.query(vector=qvec, top_k=body.k, include_metadata=True)
        hits = []
        for m in res.get("matches", []):
            hits.append(
                {
                    "id": m.get("id"),
                    "score": m.get("score"),
                    "text_chunk": m.get("metadata", {}).get("text_chunk"),
                    "source": m.get("metadata", {}).get("source"),
                    "category": m.get("metadata", {}).get("category"),
                    "tags": m.get("metadata", {}).get("tags"),
                }
            )
        return hits

    hits = await asyncio.get_event_loop().run_in_executor(executor, _sync_query)
    return {"query": body.text, "results": hits}
