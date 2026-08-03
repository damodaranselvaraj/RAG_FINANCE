"""
Application configuration — loaded from environment variables via pydantic-settings.
Copy .env.example → .env and fill in values before running.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ----- API -----
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ----- CORS -----
    cors_origins: list[str] = ["http://localhost:4200"]

    # ----- Pinecone -----
    pinecone_api_key: str = ""
    pinecone_env: str = ""
    pinecone_index_name: str = "rag-finance"

    # ----- OpenAI / embeddings -----
    openai_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"

    # ----- LLM -----
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    # ----- RAG tunables -----
    rag_top_k: int = 5
    grounding_threshold: float = 0.65
    hybrid_alpha: float = 0.5             # weight of dense in hybrid merge

    # ----- Chunking -----
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ----- Memory / token budget -----
    sqlite_db_path: str = "./backend.db"
    token_budget_t: int = 3000            # unsummarised token limit
    token_budget_n: int = 5              # raw turns to keep after summarisation

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()
