# scripts/ingest_to_pinecone.py
import os
import uuid
import json
from time import sleep
from tqdm import tqdm
import pandas as pd
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import pinecone
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "niva_db")
RAW_COLL = "raw_chunks"
META_COLL = "knowledge_chunks"
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "medical-knowledge")

# Initialize clients
mc = MongoClient(MONGO_URI)
mdb = mc[MONGO_DB]

# CSV path (mounted or local)
CSV_PATH = os.getenv("CSV_PATH", "./data/medical_knowledge.csv")

# Load DataFrame from CSV or from Mongo raw collection if CSV missing
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
else:
    df = pd.DataFrame(list(mdb[RAW_COLL].find()))
    if df.empty:
        raise SystemExit(
            "No CSV found and raw_chunks collection is empty. Place CSV at " + CSV_PATH
        )

# Initialize embedder & Pinecone
embedder = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim
pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENV")
)
if PINECONE_INDEX not in pinecone.list_indexes():
    # create index with dimension 384 for MiniLM
    pinecone.create_index(PINECONE_INDEX, dimension=384)
index = pinecone.Index(PINECONE_INDEX)


def make_text_chunk(row):
    parts = []
    # adjust field names according to your CSV columns
    for col in ["title", "question", "answer", "content", "guideline"]:
        if col in row and pd.notna(row[col]):
            parts.append(str(row[col]))
    if not parts:
        parts = [json.dumps(row.to_dict(), default=str)]
    return "\n\n".join(parts)


batch_size = 64
to_upsert = []
meta_docs = []
print(f"Preparing {len(df)} chunks for embedding...")

for _, r in tqdm(df.iterrows(), total=len(df)):
    text = make_text_chunk(r)
    chunk_id = str(uuid.uuid4())
    metadata = {
        "id": chunk_id,
        "text_chunk": text[:1500],
        "source": r.get("source") if "source" in r else "uploaded_csv",
        "category": r.get("category") if "category" in r else "general",
        "tags": (
            r.get("tags").split(",") if "tags" in r and pd.notna(r.get("tags")) else []
        ),
        "row": r.to_dict(),
    }
    vec = embedder.encode(text).tolist()
    to_upsert.append((chunk_id, vec, metadata))
    meta_docs.append(metadata)

    if len(to_upsert) >= batch_size:
        index.upsert(vectors=to_upsert)
        try:
            mdb[META_COLL].insert_many(meta_docs)
        except Exception as e:
            print("Mongo insert error:", e)
        to_upsert = []
        meta_docs = []
        sleep(0.1)

# final flush
if to_upsert:
    index.upsert(vectors=to_upsert)
    if meta_docs:
        mdb[META_COLL].insert_many(meta_docs)

print("Ingestion complete.")
print("Total stored in Mongo collection:", mdb[META_COLL].count_documents({}))
