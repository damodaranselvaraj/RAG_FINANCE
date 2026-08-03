"""
POST /chat  — main RAG endpoint.
GET  /chat/history/{session_id}  — conversation history.

Pipeline (each step is a stub until the downstream service is wired in):
    1. Validate & attach user_id / session_id          ← done here
    2. Guardrail inbound check                         ← stub
    3. Route query (legal / trend / out_of_scope)      ← stub
    4. Retrieve context or call FRED tool              ← stub
    5. Assemble prompt + call LLM                      ← stub
    6. Guardrail outbound check                        ← stub
    7. Persist turn to SQLite                          ← stub
    8. Return ChatResponse (SSE streaming optional)    ← returns JSON for now
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api.core.config import Settings, get_settings
from api.schemas.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    Citation,
    GuardrailVerdict,
    MessageRecord,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Helper — build a correlation / request ID
# ---------------------------------------------------------------------------

def _request_id(request: Request) -> str:
    """Return X-Request-ID header if present, else generate one."""
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ChatResponse,
    summary="Submit a user query and receive a grounded RAG answer",
    status_code=status.HTTP_200_OK,
)
async def chat(
    body: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """
    Accepts a user query together with user_id and session_id.
    Returns a structured response that includes the answer, source citations,
    guardrail verdict, query route, and token usage.

    Downstream services (guardrails, retrieval, LLM, memory) are stubbed and
    will be replaced incrementally as each layer is built.
    """
    req_id = _request_id(request)
    logger.info("chat request user=%s session=%s req_id=%s query=%r",
                body.user_id, body.session_id, req_id, body.query[:120])

    # ------------------------------------------------------------------
    # Step 1 — basic validation already done by Pydantic.
    # Attach correlation ID to response headers (done in middleware).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Step 2 — INBOUND guardrail check (stub)
    # Replace with: from guardrails.rules import check_inbound
    # result = check_inbound(body.query)
    # ------------------------------------------------------------------
    inbound_verdict = GuardrailVerdict(action="allow")

    if inbound_verdict.action == "block":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"guardrail": inbound_verdict.model_dump()},
        )

    # ------------------------------------------------------------------
    # Step 3 — Route query (stub)
    # Replace with: from retrieval.router import classify_query
    # route = classify_query(body.query)
    # ------------------------------------------------------------------
    route: str = "legal"   # placeholder — will be "legal" | "trend" | "out_of_scope"

    if route == "out_of_scope":
        # Return a polite refusal without calling the LLM.
        return ChatResponse(
            user_id=body.user_id,
            session_id=body.session_id,
            answer=(
                "I'm designed to help with fair-lending and consumer credit-rights "
                "questions only. Please consult an appropriate resource for your request."
            ),
            citations=[],
            guardrail=GuardrailVerdict(
                action="block",
                reason="out_of_scope",
                citations_present=False,
            ),
            route="out_of_scope",
            token_usage={},
        )

    # ------------------------------------------------------------------
    # Step 4 — Retrieve context / call FRED tool (stub)
    # ------------------------------------------------------------------
    retrieved_chunks: list[dict] = []   # will be populated by retrieval layer
    citations: list[Citation] = []

    # ------------------------------------------------------------------
    # Step 5 — LLM call (stub)
    # Replace with: from orchestration.chains import build_rag_chain
    # chain = build_rag_chain(); answer = await chain.ainvoke(...)
    # ------------------------------------------------------------------
    answer = (
        "[ LLM response stub — retrieval and orchestration layers not yet wired. "
        f"Query received: {body.query!r} ]"
    )
    token_usage: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Step 6 — OUTBOUND guardrail check (stub)
    # Replace with: from guardrails.rules import check_outbound
    # outbound_verdict = check_outbound(answer)
    # ------------------------------------------------------------------
    outbound_verdict = GuardrailVerdict(action="allow", citations_present=False)

    # ------------------------------------------------------------------
    # Step 7 — Persist turn to SQLite (stub)
    # Replace with memory.db session + message inserts.
    # ------------------------------------------------------------------
    logger.info("chat response user=%s session=%s req_id=%s route=%s",
                body.user_id, body.session_id, req_id, route)

    return ChatResponse(
        user_id=body.user_id,
        session_id=body.session_id,
        answer=answer,
        citations=citations,
        guardrail=outbound_verdict,
        route=route,   # type: ignore[arg-type]
        token_usage=token_usage,
    )


# ---------------------------------------------------------------------------
# GET /chat/history/{session_id}
# ---------------------------------------------------------------------------

@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Retrieve conversation history for a session",
)
async def chat_history(
    session_id: str,
    settings: Settings = Depends(get_settings),
) -> ChatHistoryResponse:
    """
    Returns all messages for the given session_id in chronological order.
    Stub — will query the SQLite messages table once the memory layer is built.
    """
    logger.info("history request session=%s", session_id)

    # Stub: replace with:
    #   from memory.db import get_db
    #   messages = get_messages_for_session(session_id, db=next(get_db()))
    return ChatHistoryResponse(session_id=session_id, messages=[])
