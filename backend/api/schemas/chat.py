"""
Pydantic request / response schemas for POST /chat and GET /chat/history.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# POST /sessions
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    title: str = Field(default="New Chat", description="Human-readable session title")


class SessionCreateResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime



# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Client-generated user identifier")
    session_id: str = Field(..., description="Session identifier returned by POST /sessions")
    role: Literal["user", "assistant", "system"] = Field(default="user", description="Role of the message sender")
    query: str = Field(..., min_length=1, max_length=4096, description="User query text")


# ---------------------------------------------------------------------------
# Response building blocks
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    source_doc: str = Field(..., description="Source filename, e.g. FedReserve_ECOA_Regulation_B.pdf")
    law: str = Field(..., description="Law tag: ECOA/RegB | FairHousingAct | Overview | HandbookIntro")
    section: str = Field(default="", description="Section heading within the document, if available")
    chunk_id: str = Field(default="", description="Vector-DB chunk identifier")


class GuardrailVerdict(BaseModel):
    action: Literal["allow", "rewrite", "block"]
    reason: str | None = None
    citations_present: bool = False
    violations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class ChatResponse(BaseModel):
    user_id: str
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    guardrail: GuardrailVerdict
    route: Literal["legal", "trend", "out_of_scope"]
    token_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Keys: prompt_tokens, completion_tokens, total_tokens",
    )


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

class MessageRecord(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageRecord]


