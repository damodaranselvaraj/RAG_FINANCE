"""
Stage 4 (vector upsert) — pushes embedded chunks into the pre-existing
Pinecone index (created externally for text-embedding-3-large @
Settings.embedding_dimensions). This module never creates, deletes, or
reconfigures the index — it only connects, validates, and upserts.
"""
from __future__ import annotations

from dataclasses import fields
from functools import lru_cache

from pinecone import Pinecone

from api.core.config import Settings, get_settings
from ingestion.embeddings import EmbeddedChunk
from ingestion.parsers.parser import Chunk


class IndexDimensionMismatch(RuntimeError):
    """The configured embedding_dimensions doesn't match the live index."""


@lru_cache(maxsize=2)
def _get_client(api_key: str) -> Pinecone:
    if not api_key:
        raise RuntimeError("Settings.pinecone_api_key is not set.")
    return Pinecone(api_key=api_key)


def get_index(settings: Settings | None = None):
    """Return (Pinecone client, Index handle) for Settings.pinecone_index_name."""
    settings = settings or get_settings()
    pc = _get_client(settings.pinecone_api_key)
    return pc, pc.Index(settings.pinecone_index_name)


def verify_index_dimensions(pc: Pinecone, settings: Settings) -> None:
    """Fail fast — before spending any OpenAI calls — if the live index's
    dimension doesn't match what we're configured to embed at."""
    info = pc.describe_index(settings.pinecone_index_name)
    if info.dimension != settings.embedding_dimensions:
        raise IndexDimensionMismatch(
            f"Pinecone index {settings.pinecone_index_name!r} has dimension="
            f"{info.dimension}, but Settings.embedding_dimensions="
            f"{settings.embedding_dimensions}."
        )


def _chunk_metadata(chunk: Chunk) -> dict:
    """All non-None Chunk fields, Pinecone-safe (no null values allowed).

    Includes `text` itself — there's no separate blob store, so
    retrieval/context_builder.py reads chunk text back out of the metadata on
    retrieved matches. Also includes `chunk_id`, duplicating the vector ID;
    harmless, and simpler than special-casing it out.
    """
    raw = {f.name: getattr(chunk, f.name) for f in fields(chunk)}
    return {k: v for k, v in raw.items() if v is not None}


def to_pinecone_vectors(
    embedded_chunks: list[EmbeddedChunk],
) -> list[tuple[str, list[float], dict]]:
    return [
        (ec.chunk.chunk_id, ec.values, _chunk_metadata(ec.chunk))
        for ec in embedded_chunks
    ]


def existing_chunk_ids(
    index,
    chunk_ids: list[str],
    namespace: str | None = None,
    batch_size: int = 100,
) -> set[str]:
    """Which of these chunk_ids already have a vector stored.

    chunk_id is itself a content hash (see parser.py), so "ID exists" is
    equivalent to "content unchanged" — this is what lets run_ingestion skip
    re-embedding unchanged chunks when force=False.
    """
    found: set[str] = set()
    for i in range(0, len(chunk_ids), batch_size):
        batch = chunk_ids[i : i + batch_size]
        resp = index.fetch(ids=batch, namespace=namespace)
        found.update(resp.vectors.keys())
    return found


def upsert_embedded_chunks(
    embedded_chunks: list[EmbeddedChunk],
    settings: Settings | None = None,
) -> int:
    """Upsert vectors, batched. Returns the number of vectors sent.

    Upsert is by chunk_id, so re-running with the same chunks overwrites
    rather than duplicates — this is the idempotency guarantee, independent
    of whether the caller skipped unchanged chunks upstream.
    """
    if not embedded_chunks:
        return 0

    settings = settings or get_settings()
    pc, index = get_index(settings)
    verify_index_dimensions(pc, settings)

    vectors = to_pinecone_vectors(embedded_chunks)
    index.upsert(
        vectors=vectors,
        namespace=settings.pinecone_namespace,
        batch_size=settings.pinecone_upsert_batch_size,
        show_progress=True,
    )
    return len(vectors)
