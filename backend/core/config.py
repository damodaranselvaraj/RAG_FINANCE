
from __future__ import annotations

import os
from pathlib import Path

# Silence ChromaDB's anonymized telemetry (its posthog client version mismatches
# and spams harmless errors otherwise). Must be set before chromadb is imported.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# --- Filesystem layout ------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
## CHROMA_DIR = BACKEND_DIR / "chroma_db"

# The single document we ingest for Task 1. (The folder also contains
# Org_HR_Policy.docx which can be added later by extending DOCUMENTS.)
DOCUMENTS = [
    DATA_DIR / "Finance.docx",
]

# --- Embedding model --------------------------------------------------------
# HuggingFace sentence-transformers model requested by the spec.
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# BGE retrieval models are trained with an instruction prefix on the *query*
# side only. Prefixing the query (not the stored passages) measurably improves
# retrieval quality. See the model card on HuggingFace.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# --- Vector store -----------------------------------------------------------
COLLECTION_NAME = "finance"
# ChromaDB uses an HNSW index; we explicitly select cosine distance so
# similarity is scored the way the spec requires.
HNSW_SPACE = "cosine"

# --- Chunking ---------------------------------------------------------------
CHUNK_SIZE = 900        # target characters per chunk
CHUNK_OVERLAP = 150     # characters shared between adjacent chunks

# --- Retrieval --------------------------------------------------------------
TOP_K = int(os.environ.get("RAG_TOP_K", "4"))

# --- API --------------------------------------------------------------------
API_HOST = os.environ.get("RAG_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("RAG_API_PORT", "8000"))
# Angular dev server origin(s) allowed to call the API.
CORS_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:57512"
]

# --- Vector store selection -------------------------------------------------
# Which backend the query API reads from: "chroma" (default) or "pinecone".
# Set VECTOR_DB=pinecone in the environment to serve answers from Pinecone.
VECTOR_DB = os.environ.get("VECTOR_DB", "chroma").lower()

# --- Pinecone ---------------------------------------------------------------
# The API key lives in AgenticCoding/.env (one level above this backend dir).
ENV_PATH = BACKEND_DIR.parent.parent / ".env"
PINECONE_API_KEY_VAR = "PINECONE_API_KEY"
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX", "hr-policy")
# BAAI/bge-small-en-v1.5 produces 384-dimensional vectors.
EMBED_DIM = 384
PINECONE_METRIC = "cosine"
# Serverless index location (free tier default).
PINECONE_CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")
