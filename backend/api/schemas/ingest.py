"""
Pydantic schemas for POST /ingest.
"""
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    force_reingest: bool = Field(
        default=False,
        description="Re-ingest all documents even if content_hash matches existing vectors",
    )


class IngestResponse(BaseModel):
    status: str
    documents_processed: int = 0
    chunks_upserted: int = 0
    message: str = ""
