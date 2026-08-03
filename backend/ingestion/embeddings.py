"""
Stage 3 (embedding) — turns parsed/chunked text into vectors.

Default production model is OpenAI text-embedding-3-large, truncated to
Settings.embedding_dimensions (1024) via the API's native `dimensions` param,
matching the pre-existing Pinecone index this feeds into (see
pinecone_upsert.py). Not to be confused with parsers/parser.py's own
_get_embed_model, which loads a separate, independently-configured embedding
model only for Stage 2's optional "semantic" chunk-boundary detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from api.core.config import Settings, get_settings
from ingestion.parsers.parser import Chunk


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    values: list[float]


@lru_cache(maxsize=4)
def _get_embed_model(model_name: str, dimensions: int, api_key: str, batch_size: int):
    """Lazily construct (and cache) the OpenAI embedding client.

    Imported locally so importing this module doesn't require the openai
    client unless embed_chunks() is actually called.
    """
    if not api_key:
        raise RuntimeError(
            "Settings.openai_api_key is not set — required to embed chunks "
            f"with {model_name!r}."
        )
    from llama_index.embeddings.openai import OpenAIEmbedding

    return OpenAIEmbedding(
        model=model_name,
        dimensions=dimensions,
        api_key=api_key,
        embed_batch_size=batch_size,
    )


def embed_chunks(
    chunks: list[Chunk],
    settings: Settings | None = None,
) -> list[EmbeddedChunk]:
    """Embed each chunk's text, in the same order as the input list.

    Empty input returns an empty list without making any API call.
    """
    if not chunks:
        return []

    settings = settings or get_settings()
    embed_model = _get_embed_model(
        settings.embedding_model,
        settings.embedding_dimensions,
        settings.openai_api_key,
        settings.embedding_batch_size,
    )

    vectors = embed_model.get_text_embedding_batch(
        [chunk.text for chunk in chunks], show_progress=True
    )
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Embedding count mismatch: got {len(vectors)} vectors for {len(chunks)} chunks"
        )
    return [EmbeddedChunk(chunk=c, values=v) for c, v in zip(chunks, vectors)]
