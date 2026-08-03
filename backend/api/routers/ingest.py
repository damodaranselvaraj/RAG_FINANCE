"""
POST /ingest  — admin endpoint to trigger document re-ingestion.
"""
import logging

from fastapi import APIRouter, Depends

from api.core.config import Settings, get_settings
from api.schemas.ingest import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Trigger document ingestion pipeline",
)
async def ingest(
    body: IngestRequest,
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """
    Triggers the offline ingestion pipeline:
      1. Parse PDFs (Stage 1 winner)
      2. Chunk text (Stage 2 winner)
      3. Embed chunks (Stage 3 winner)
      4. Upsert to Pinecone + build BM25 index (Stage 4/5)
      5. Load FRED CSV into SQLite

    Stub — replace the body with a call to the ingestion module once built:
        from ingestion.ingest_embed import run_ingestion
        result = await run_ingestion(force=body.force_reingest, settings=settings)
    """
    logger.info("ingest triggered force=%s", body.force_reingest)

    # Stub response until the ingestion module is wired.
    return IngestResponse(
        status="accepted",
        documents_processed=0,
        chunks_upserted=0,
        message="Ingestion pipeline not yet implemented. Stub response.",
    )
