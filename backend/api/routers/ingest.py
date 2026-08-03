"""
POST /ingest  — admin endpoint to trigger document re-ingestion.
"""
import logging

from fastapi import APIRouter, Depends

from api.core.config import Settings, get_settings
from api.schemas.ingest import IngestRequest, IngestResponse
from ingestion.ingest_embed import run_ingestion

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
      3. Embed chunks (Stage 3 winner — text-embedding-3-large)
      4. Upsert to Pinecone

    force_reingest=False (default) skips chunks whose content_hash already
    matches an existing vector; True re-embeds and re-upserts everything.
    """
    logger.info("ingest triggered force=%s", body.force_reingest)

    result = await run_ingestion(force=body.force_reingest, settings=settings)

    return IngestResponse(
        status=result.status,
        documents_processed=result.documents_processed,
        chunks_upserted=result.chunks_upserted,
        message=result.message,
    )
