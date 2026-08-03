"""
FastAPI dependency injection helpers.

Usage in a router:
    from api.deps import get_settings
    @router.post("/ingest")
    async def ingest(settings: Settings = Depends(get_settings)):
        ...
"""
from api.core.config import Settings, get_settings  # noqa: F401 — re-export for convenience
