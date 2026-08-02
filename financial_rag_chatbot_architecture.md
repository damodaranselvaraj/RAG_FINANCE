# Consumer Credit Rights Assistant (Group 6 — `06_finance_complaints`) — Architecture & Build Prompt

> **Project scope:** A RAG assistant that explains a consumer's rights under **ECOA (Regulation
> B)**, the **Fair Housing Act**, and general fair-lending law when someone believes they were
> denied credit or housing unfairly — grounded strictly in four Federal Reserve Consumer
> Compliance Handbook chapters plus one FRED structured time-series (total US consumer credit
> outstanding). This is one of 9 capstone groups; per `REQUIREMENTS_OVERVIEW.md` the core skill
> being graded for this group specifically is **correct law-to-scenario routing (ECOA vs. Fair
> Housing Act)**, on top of the methodology shared by all 9 groups below.

> **⚠️ Two items to confirm with your instructor before build, surfaced by the newly-provided files:**
> 1. **UI stack conflict.** `REQUIREMENTS_OVERVIEW.md` says the deliverable is "Streamlit or
>    FastAPI+Streamlit, per the course's UI progression rule." Your original tech-stack choice for
>    this doc is **Angular**. Angular is a fine (arguably stronger) app-usability choice for the
>    10%-weighted "code quality / app usability" component, but confirm it's an acceptable
>    substitution for the stated course rule before investing the build time — this doc keeps
>    Angular per your instruction, but flags the risk.

## 1. High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              ANGULAR UI (SPA)                             │
│   Chat window · Session/User handling · Streaming response renderer       │
└───────────────────────────────────┬────────────────────────────────────┘
                                     │ REST / SSE (WebSocket optional)
┌───────────────────────────────────▼────────────────────────────────────┐
│                         FASTAPI GATEWAY LAYER                            │
│  Auth · Rate limiting · Request/Response schemas · Routing               │
└───────────────────────────────────┬────────────────────────────────────┘
                                     │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  GUARDRAIL / MODERATION LAYER (Middleware)               │
│  Input: prompt-injection/toxicity checks · optional PII flagging         │
│  Output: no-legal-verdict enforcement · strict-grounding/no-invented-law │
│  check · mandatory chapter citation · out-of-scope refusal · Implemented │
│  via LangChain Guardrails as request/response middleware                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                        │
┌────────────────▼────────────────┐   ┌───────────────────▼──────────────────┐
│   DATA INGESTION LAYER (offline)  │   │   RETRIEVAL / INFERENCE LAYER (online) │
│  Parse → Chunk → Embed → Index    │   │  Route → Dense/Sparse/Hybrid search →  │
│  (each stage ablation-compared)   │   │  optional rerank → Context assembly →  │
│  → Pinecone (+BM25 index) upsert  │   │  LLM call                              │
└────────────────┬───────────────┘   └───────────────────┬──────────────────┘
                 │                                        │
                 └───────────────────┬────────────────────┘
                                     │
┌───────────────────────────────────▼────────────────────────────────────┐
│                     CONVERSATION MEMORY / PERSISTENCE LAYER              │
│  SQLite: users, sessions, messages, summaries                            │
│  Token-budget manager → rolling summarization of overflow turns          │
│  User profile/intent store (persisted across sessions via user_id)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                     │
┌───────────────────────────────────▼────────────────────────────────────┐
│                          LLM ORCHESTRATION LAYER                         │
│  Prompt templates · Context/history injection · Model client (LangChain) │
└───────────────────────────────────┬────────────────────────────────────┘
                                     │
┌───────────────────────────────────▼────────────────────────────────────┐
│         EVALUATION LAYER — 8 mandatory ablation stages + end-to-end      │
│  Retrieval: R@1, R@3, MRR@10, NDCG@3 · Generation: RAGAS + DeepEval       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer-by-Layer Breakdown

### 2.1 Presentation Layer — Angular
| Concern | Detail |
|---|---|
| Responsibility | Chat UI, session/user identification (generate/store `user_id` client-side or via login), render streamed answers, show citations/source chunks, show guardrail warnings. |
| Key modules | `ChatModule` (message list, input box, streaming), `AuthModule` (if login is added later), `SessionService` (holds `user_id`, `session_id` in local storage / cookie), `ApiService` (HTTP + SSE client to FastAPI). |
| Contracts consumed | `POST /chat`, `GET /chat/history/{session_id}`, `GET /health`. |
| Non-functional | Token-by-token streaming (SSE) for perceived latency, graceful error states when guardrails block a message. |

### 2.2 API Gateway Layer — FastAPI
| Concern | Detail |
|---|---|
| Responsibility | Single entry point; validates payloads via Pydantic; attaches `user_id`/`session_id`; dispatches to guardrail → orchestration pipeline; returns structured response (answer, citations, token usage, guardrail flags). |
| Endpoints | `POST /chat` (main), `POST /ingest` (admin/document upload trigger), `GET /chat/history/{session_id}`, `GET /users/{user_id}/profile`, `GET /health`, `GET /metrics`. |
| Cross-cutting | CORS for Angular origin, request logging/correlation IDs, exception handlers that never leak internal stack traces, API key or JWT auth guard. |

### 2.3 Guardrail / Moderation Layer (Middleware)
| Concern | Detail |
|---|---|
| Responsibility | Sits between API layer and the RAG/LLM pipeline — inspects **inbound** user query and **outbound** LLM response. The primary guardrail risk for this domain is *legal overreach and hallucinated law*, not PII exfiltration (PII flagging is kept as a secondary control). |
| Inbound checks | Prompt-injection/jailbreak pattern detection; domain-scope check (is this a fair-lending/credit-denial question, or an out-of-scope request — see §2.9 #6); optional PII flag-and-warn (case facts are kept, not redacted, since routing depends on them). |
| Outbound checks (primary) | **No-legal-verdict rule**: block/rewrite any answer asserting discrimination occurred — must instead explain the applicable law and, where facts plausibly match a protected basis, suggest filing a complaint with the appropriate regulator. **No-invented-law rule**: every legal claim must trace to a retrieved chunk; below-threshold retrieval confidence → "insufficient information in these documents" fallback. **Mandatory citation rule**: every substantive answer must cite the source chapter it drew from — this is also a cross-cutting rule for all 9 capstone groups per `REQUIREMENTS_OVERVIEW.md`. **Out-of-scope refusal**: politely decline requests outside fair-lending/credit-rights scope. |
| Implementation | LangChain `Guardrails`/`Runnable` wrapped as FastAPI middleware or a dependency injected before/after the orchestration call. Configurable policy file (YAML/JSON) defining verdict-avoidance phrase patterns, grounding-confidence threshold, and citation-enforcement rules. |
| Output to caller | Structured guardrail verdict object: `{action: "allow"|"rewrite"|"block", reason, citations_present: bool, violations: [...]}`. |

### 2.4 Data Ingestion Layer (offline / batch pipeline)

Per `EVALUATION_METHODOLOGY.md` Part C, ingestion is not "pick one library and go" — Stages 1–3
below are each a **required ablation experiment** (≥2 real alternatives, measured, winner justified
in writing with numbers) before any choice is locked in for the production pipeline.

| Concern | Detail |
|---|---|
| Responsibility | Convert the four Federal Reserve PDF chapters into a vector (and sparse/BM25) index; handle the FRED CSV via a separate structured-data path. |
| Sources (text/PDF) | `FedReserve_ECOA_Regulation_B.pdf` (6p), `FedReserve_Fair_Housing_Act.pdf` (3p), `FedReserve_Fair_Lending_Overview.pdf` (3p), `FedReserve_Consumer_Compliance_Handbook_Intro.pdf` (6p) — 18 pages total, short and dense with legal terminology. |
| **Stage 1 — Parsing (ablation-required)** | Compare ≥2 of `pypdf` / `pdfplumber` / `PyMuPDF (fitz)`. Metrics: % pages with clean extracted text, table-extraction success (if any tables appear in these chapters), and downstream **R@3** when each parser's output flows through the same chunking/embedding pipeline. |
| **Stage 2 — Chunking (ablation-required)** | Compare ≥2 of: fixed-size (no overlap) / fixed-size+overlap / recursive-sentence-aware / semantic chunking, at 2+ sizes (e.g. 300/500/800 tokens) and overlaps (e.g. 0/50/100) — bias toward the smaller end given these chapters are 3–6 pages each. Metrics: R@1, R@3, MRR@10, NDCG@3. |
| **Stage 3 — Embedding model (ablation-required)** | Compare ≥2 of `all-MiniLM-L6-v2`, `bge-small-en-v1.5`, `text-embedding-3-small`, `multi-qa-mpnet-base-dot-v1`, or similar. Metrics: R@1, R@3, MRR@10, NDCG@3, latency (ms/query). Explicit project callout: legal terminology can behave differently across general-purpose embedding models, so weight this stage carefully. |
| Metadata tagging | `source_doc` (filename), `law` (`ECOA/RegB`, `FairHousingAct`, `Overview`, `HandbookIntro`), `section`, `content_hash` (idempotency). |
| **Stage 4 — Vector DB (ablation-required, production-constrained)** | Your fixed tech stack is Pinecone. Satisfy the ablation requirement by comparing **Pinecone vs. one of ChromaDB/FAISS** run locally against the same eval set — methodology explicitly says "R@3 usually won't change much between vector DBs for the same embeddings," so justify the Pinecone choice on the operational axes (managed persistence, metadata filtering, no self-hosted index ops) rather than expecting a retrieval-quality win. Report R@3 parity + index build time + metadata-filter support + persistence. |
| Structured data (CSV) | `FRED_Total_Consumer_Credit.csv` does **not** go through chunking — trend questions need arithmetic over rows, not nearest-neighbor text retrieval. Load into SQLite/pandas and expose a callable tool (delta/trend over a date range) rather than pre-embedding summaries; this decision is also worth a short ablation note. |
| Sparse index | Build a BM25 index over the same chunks (needed for Stage 5 below) alongside the Pinecone dense index. |
| Operational needs | Idempotent re-ingestion (dedupe by content_hash), index versioning so retrieval/ingestion embedding models never drift apart, a CLI/admin endpoint to trigger re-ingestion. |

### 2.5 Retrieval / Inference Layer (online, per request)

Stages 5–7 (retrieval mode, hybrid merge, reranking) are also mandatory ablation experiments per
`EVALUATION_METHODOLOGY.md` Part C — implement all real alternatives even if the production default
ends up simpler, because the graded deliverable is the comparison table, not just the final choice.

| Concern | Detail |
|---|---|
| Responsibility | Turn a (guardrail-cleared) user query into an answer grounded in retrieved chunks, correctly routed to the law that actually applies (credit denial → ECOA, housing/mortgage discrimination → Fair Housing Act). |
| Query router | Classify: (a) legal/rights question → retrieval path below, (b) numeric/trend question → FRED structured-data tool call, (c) out-of-scope → guardrail refusal. |
| **Stage 5 — Retrieval mode (ablation-required)** | Compare all 3: dense-only (Pinecone embeddings), sparse-only (BM25), hybrid. **Must break results out by query type** — exact-term/keyword queries (e.g., "what is Regulation B") vs. paraphrased/semantic queries (e.g., "can they turn me down because of my age") — this breakdown is the actual justification for whether hybrid earns its complexity. Metrics: R@1, R@3, MRR@10, NDCG@3, all reported both overall and per query-type. |
| **Stage 6 — Hybrid merge (ablation-required, only if Stage 5 picks hybrid)** | Compare Reciprocal Rank Fusion (`score = Σ 1/(k + rank)`, k≈60) vs. weighted linear combination (`score = α·dense_norm + (1-α)·sparse_norm`, sweep ≥3 α values). State explicitly what α (or RRF) won and why, citing the table. |
| **Stage 7 — Reranking (ablation-required)** | Compare no-reranker vs. cross-encoder reranker (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) applied to top-20 → reranked to top-3/5. Metrics: R@3, NDCG@3, added latency (ms). Justify whether the accuracy gain is worth the latency cost for a support-hotline bot (users expect a fast reply). |
| Law-metadata filtering | Once intent is classified, optionally hard-filter or boost by `law` metadata — ablate this too (a hard filter can mis-route a borderline question); this is specific to this group's core-skill test (routing), not part of the shared 8-stage methodology. |
| Steps | 1) Route query → 2) retrieve (dense/sparse/hybrid per Stage 5/6 winner, optionally reranked per Stage 7 winner) or call FRED tool → 3) assemble context: system prompt + retrieved chunks (citations) or structured result + condensed history + query → 4) call LLM → 5) post-process (citations, formatting) → 6) outbound guardrail check → 7) persist turn. |
| Tunables | `top_k`, similarity/BM25 score threshold below which the system responds "insufficient information in these documents" instead of hallucinating. |

### 2.6 Conversation Memory / Persistence Layer — SQLite
> Note: acceptance tests (§2.9) and seed evaluation questions are all single-turn. This layer
> remains part of the architecture for a usable chat UI and contributes to the 10%-weighted
> "code quality / app usability" component, but it is not the primary graded surface — prioritize
> §2.3–2.5 and §2.8 first.

| Concern | Detail |
|---|---|
| Responsibility | Durable store for users, sessions, turns, and rolling summaries; drives multi-turn coherence and token-budget management. |
| Suggested schema | `users(user_id PK, created_at, profile_json)` · `sessions(session_id PK, user_id FK, created_at, last_active_at)` · `messages(message_id PK, session_id FK, role, content, token_count, created_at)` · `summaries(summary_id PK, session_id FK, summary_text, covers_up_to_message_id, created_at)`. |
| Token-budget manager | On each turn: compute running token count of unsummarized messages; if it exceeds threshold `T`, summarize all-but-last-`N` messages into/append to `summaries`, then prune those raw messages from the active context window (raw rows remain in SQLite for audit only). |
| Context assembly rule | Prompt history = `[latest summary (if any)] + [last N raw turns]`. |
| User profile/intent | `profile_json` on `users` stores durable facts/preferences over time so intent persists across sessions, independent of the rolling conversation summary. |

### 2.7 LLM Orchestration Layer
| Concern | Detail |
|---|---|
| Responsibility | Compose the final prompt (system + grounded context + history/summary + query), call the LLM client, handle streaming, retries/timeouts, and per-call token tracking. |
| Implementation | LangChain `Runnable`/chain: `PromptTemplate → LLM → OutputParser`, with the guardrail runnables wrapped around it. |
| **Stage 8 — LLM for generation (ablation-required)** | Compare ≥2 real LLMs (e.g. Gemini 2.5/2.0 Flash, GPT-4o-mini, Claude Haiku, a local Ollama model). **Fix retrieval — vary only the generator** so the comparison isolates the LLM's contribution. Metrics: RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall), DeepEval (Hallucination, G-Eval), cost/query, latency. |
| Config | Model name (from Stage 8 winner), temperature (low, for factual legal answers), max_tokens, system prompt (including the no-legal-verdict instruction) versioned in a prompts registry/file. |

### 2.8 Evaluation Layer — the graded core of this project

Per `EVALUATION_METHODOLOGY.md`: **no design decision may be justified by "it seemed to work
better."** Every stage above must be backed by a number, in a table, with a winner picked in
writing citing the actual numbers. A pipeline that "just works" with no evaluation evidence caps
at 30% (the correctness-only line) — it cannot pass on functionality alone.

**Metrics glossary (know these before measuring):**

| Metric | What it measures |
|---|---|
| R@1 (Recall@1) | Did the correct chunk rank #1? (0/1 per query, averaged) |
| R@3 (Recall@3) | Did the correct chunk appear in the top 3? (0/1 per query, averaged) |
| MRR@10 (Mean Reciprocal Rank) | How high was the correct chunk ranked within top 10? `1/rank`, 0 if absent, averaged |
| DCG@3 / NDCG@3 | Graded-relevance-aware version of Recall; NDCG normalizes 0–1 against the ideal ranking |
| RAGAS: Faithfulness | Is the answer actually supported by retrieved text? (catches hallucination) |
| RAGAS: Answer Relevancy | Does the answer address what was asked? |
| RAGAS: Context Precision/Recall | Did retrieval fetch the right stuff, and only the right stuff? |
| DeepEval: Hallucination, G-Eval, Answer Relevancy, Faithfulness | Second-judge scores; investigate (don't cherry-pick) if RAGAS and DeepEval disagree sharply |

**Step 1 — build the evaluation set before touching any design decision:** ≥20 labeled questions
(question text, ground-truth source document/chunk, short ideal answer), expanded from this
group's 5 seed questions against the actual 4 PDFs + CSV.

**The 8 required ablation tables** (templates — fill with real measured numbers):

*Stage 1 — Parsing*
| Parser | Clean text % | R@3 (downstream) |
|---|---|---|
| pypdf | | |
| pdfplumber | | |
| PyMuPDF | | |

*Stage 2 — Chunking*
| Strategy | Chunk size | Overlap | R@1 | R@3 | MRR@10 | NDCG@3 |
|---|---|---|---|---|---|---|

*Stage 3 — Embedding model*
| Embedding model | Dimensions | R@1 | R@3 | MRR@10 | NDCG@3 | Latency (ms/query) |
|---|---|---|---|---|---|---|

*Stage 4 — Vector DB*
| Vector DB | R@3 (parity check) | Index build time | Metadata filtering? | Persistence? |
|---|---|---|---|---|

*Stage 5 — Retrieval mode*
| Mode | R@1 (all) | R@3 (all) | R@3 (keyword queries) | R@3 (semantic queries) | MRR@10 | NDCG@3 |
|---|---|---|---|---|---|---|
| Dense only | | | | | | |
| Sparse (BM25) only | | | | | | |
| Hybrid | | | | | | |

*Stage 6 — Hybrid merge (if applicable)*
| Merge method | α (if weighted) | R@3 | MRR@10 | NDCG@3 |
|---|---|---|---|---|

*Stage 7 — Reranking*
| Config | R@3 | NDCG@3 | Added latency (ms) |
|---|---|---|---|
| No reranker | | | 0 |
| + Cross-encoder rerank | | | |

*Stage 8 — LLM for generation*
| LLM | Faithfulness (RAGAS) | Answer Relevancy (RAGAS) | Context Precision (RAGAS) | Hallucination (DeepEval) | G-Eval score (DeepEval) | Cost/query | Latency |
|---|---|---|---|---|---|---|---|

**Final deliverable (Part D of the methodology):**
1. All 8 tables above, filled with real numbers — a placeholder scores zero for that stage.
2. A synthesis paragraph citing numbers from every table, e.g. *"We chose recursive chunking at
   500 tokens/50 overlap (R@3 = 0.81 vs. 0.68 for fixed-size no-overlap); hybrid retrieval merged
   via RRF (R@3 = 0.84 vs. 0.79 dense-only, 0.62 sparse-only); and [LLM] for generation
   (Faithfulness = 0.91, highest of N candidates)."*
3. End-to-end RAGAS + DeepEval scores on the final pipeline (the headline number).
4. A short "what we'd try next" section (tie to failure-mode analysis).
5. This group's own metrics on top of the shared set: law-routing accuracy (did the answer cite
   the correct source doc per §2.9's acceptance table), legal-verdict-avoidance rate, citation-
   presence rate.

**Grading weights (confirmed, all 9 groups):**

| Component | Weight |
|---|---|
| Evaluation rigor — ablation tables complete, real numbers, justified winner per stage | 40% |
| Correctness on this group's acceptance-test questions | 30% |
| End-to-end RAGAS + DeepEval scores on the final chosen pipeline | 20% |
| Code quality / app usability | 10% |

### 2.9 Acceptance Tests

| # | Question | Expected behavior |
|---|---|---|
| 1 | "I was denied a mortgage — can a bank consider my age in that decision?" | Answer from ECOA/Reg B, cited |
| 2 | "What protections exist if I think I was denied housing credit because of my race?" | Answer from Fair Housing Act, cited |
| 3 | "What's the overall purpose of fair lending law?" | Answer from overview doc |
| 4 | "Has total US consumer credit gone up or down over the last year?" | Uses the CSV time series (structured-data path) |
| 5 | "Was I definitely discriminated against?" | Explains the law, **declines to render a legal verdict**, suggests filing a complaint with the appropriate regulator |
| 6 *(proposed — add to satisfy `REQUIREMENTS_OVERVIEW.md`'s mandatory out-of-scope test)* | e.g. "What's Chase Bank's overdraft fee policy?" (competitor/out-of-scope) or "Can you help me file my tax return?" (different domain) | Bot declines and redirects to fair-lending/credit-rights scope, does not guess |

Test #5 is the direct trigger for the no-legal-verdict outbound guardrail (§2.3) and should be the
first guardrail unit test written. Test #6 should be finalized and confirmed with the instructor
per the flag at the top of this document.

---

## 3. Data Flow Summary (single user turn)

1. Angular sends `{user_id, session_id, query}` to `POST /chat`.
2. FastAPI validates payload, loads session context.
3. Guardrail middleware scans `query` for injection attempts, domain scope (including out-of-scope refusal), and optionally flags PII for the user's awareness (facts of their case are kept, not redacted).
4. Router classifies the query: legal/rights question → retrieval pipeline (dense/sparse/hybrid per the Stage 5/6 winner, optionally reranked per Stage 7); numeric/trend question → FRED structured-data tool call; out-of-scope → refusal.
5. Conversation Memory layer supplies `[summary + last N turns]` and updates token accounting (secondary feature, §2.6).
6. Orchestration layer builds the final prompt (including the no-legal-verdict instruction) → calls the Stage-8-winning LLM → gets answer.
7. Guardrail middleware scans the answer for legal-verdict language, ungrounded claims, and missing citations before it leaves the system — rewrites/blocks as needed.
8. Persistence layer stores the new user turn + assistant turn; triggers summarization if the token threshold is crossed.
9. Response (answer + citations + guardrail flags) streamed back to Angular.
10. (Offline, mandatory) Ablation runs during pipeline selection produce the 8 required tables; a regression suite re-runs the golden set on every subsequent change; RAGAS/DeepEval scores and acceptance-test results are compiled into the final evaluation report.

---

## 4. Suggested Repository Structure

```
RAG_FINANCE/
├── frontend/
│   └── ui/                          # Angular app
│       └── src/app/{chat,session,shared}/
├── backend/
│   ├── data/
│   │   ├── FedReserve_ECOA_Regulation_B.pdf
│   │   ├── FedReserve_Fair_Housing_Act.pdf
│   │   ├── FedReserve_Fair_Lending_Overview.pdf
│   │   ├── FedReserve_Consumer_Compliance_Handbook_Intro.pdf
│   │   └── FRED_Total_Consumer_Credit.csv
│   ├── api/                          # FastAPI service
│   │   ├── main.py
│   │   ├── routers/{chat.py,ingest.py,users.py,health.py}
│   │   ├── schemas/                  # Pydantic models
│   │   ├── middleware/guardrails.py
│   │   ├── core/config.py
│   │   └── deps.py
│   ├── ingestion/
│   │   ├── parsers/                  # pypdf / pdfplumber / PyMuPDF — Stage 1
│   │   ├── chunking/                 # fixed / recursive / semantic — Stage 2
│   │   ├── embeddings/                # multiple model wrappers — Stage 3
│   │   ├── sparse_index.py            # BM25 index build
│   │   └── pinecone_upsert.py         # + chroma_upsert.py / faiss_upsert.py for Stage 4 comparison
│   ├── structured_data/              # FRED CSV path — kept separate from semantic retrieval
│   │   ├── fred_loader.py
│   │   └── trend_tool.py             # callable tool: compute deltas/trend over a date range
│   ├── retrieval/
│   │   ├── embed_query.py
│   │   ├── router.py                  # legal vs. trend vs. out-of-scope classification
│   │   ├── dense_retriever.py         # Pinecone
│   │   ├── sparse_retriever.py        # BM25 — Stage 5
│   │   ├── hybrid_merge.py            # RRF / weighted-α — Stage 6
│   │   ├── reranker.py                # cross-encoder — Stage 7
│   │   └── context_builder.py
│   ├── memory/                        # secondary feature — see architecture doc §2.6
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── token_budget.py
│   │   └── summarizer.py
│   ├── orchestration/
│   │   ├── prompts/                   # includes the no-legal-verdict system instruction
│   │   ├── chains.py
│   │   └── llm_client.py              # multi-provider — Stage 8
│   ├── guardrails/
│   │   ├── policy.yaml                 # no-verdict phrase rules, grounding threshold, citation rule
│   │   └── rules.py
│   ├── evaluation/
│   │   ├── golden_dataset.jsonl        # 20+ questions
│   │   ├── ablation/                   # one script + one output table per of the 8 stages
│   │   │   ├── stage1_parsing.py
│   │   │   ├── stage2_chunking.py
│   │   │   ├── stage3_embedding.py
│   │   │   ├── stage4_vectordb.py
│   │   │   ├── stage5_retrieval_mode.py
│   │   │   ├── stage6_hybrid_merge.py
│   │   │   ├── stage7_reranking.py
│   │   │   └── stage8_llm.py
│   │   ├── retrieval_metrics.py        # R@1, R@3, MRR@10, NDCG@3
│   │   ├── run_ragas.py
│   │   ├── run_deepeval.py
│   │   ├── acceptance_tests.py         # the 6 tests from §2.9
│   │   └── evaluation_report.md        # final Part-D deliverable
│   └── tests/
├── .env.example
└── docker-compose.yml
```

---

## 5. Refined Prompt to Hand Off to a Build Agent

Copy everything in the block below as the instruction to your coding agent (e.g., Claude Code).

```
You are building the "Consumer Credit Rights Assistant" (capstone group 06_finance_complaints) —
a RAG chatbot that explains a consumer's rights under ECOA (Regulation B), the Fair Housing Act,
and general fair-lending law, grounded strictly in four named Federal Reserve Consumer Compliance
Handbook chapters plus one FRED structured time-series. This capstone is graded primarily on
EVIDENCE, not on "does the chatbot work": 40% of the grade is ablation-table rigor, 20% is final
RAGAS/DeepEval scores — 60% total requires you to implement and measure real alternatives at every
pipeline stage, not just pick reasonable defaults. A stage with a placeholder instead of real
numbers scores zero for that stage. Work stage by stage; for every ablation stage, implement at
least 2 real alternatives, run the full 20+ question eval set through each holding everything else
constant, produce the metrics table, and state a winner in writing citing the actual numbers before
moving on.

SOURCE DOCUMENTS (already provided, do not substitute or invent additional sources):
- FedReserve_ECOA_Regulation_B.pdf (6 pages) — credit-decision discrimination law
- FedReserve_Fair_Housing_Act.pdf (3 pages) — housing/mortgage-related lending discrimination
- FedReserve_Fair_Lending_Overview.pdf (3 pages) — general fair lending law overview
- FedReserve_Consumer_Compliance_Handbook_Intro.pdf (6 pages) — handbook scope/front matter
- FRED_Total_Consumer_Credit.csv — monthly US consumer credit outstanding, 1943–present

TECH STACK:
- Frontend: Angular (latest stable), standalone components, SSE-based streaming chat UI.
  (Confirm with instructor: course rule states "Streamlit or FastAPI+Streamlit" — Angular is a
  deliberate substitution per the project owner's instruction; flag if this needs sign-off.)
- Backend APIs & RAG logic: Python 3.11+, FastAPI.
- Vector store: Pinecone (serverless), production default — but Stage 4 below requires you to
  also stand up ChromaDB or FAISS locally purely for the ablation comparison table.
- Sparse retrieval: BM25 index (e.g., `rank_bm25` or Elasticsearch-lite equivalent) built over the
  same chunks as the dense index, required for Stage 5.
- Structured data: the FRED CSV is NOT put through the vector pipeline — load it into SQLite or an
  in-memory table and expose a callable tool that computes trend/delta answers over a date range.
- Persistence: SQLite (via SQLAlchemy) for users, sessions, messages, rolling summaries, and the
  FRED table.
- Guardrails: LangChain Guardrails, as FastAPI middleware/dependency wrapping both the inbound
  query and outbound response. Primary purpose: legal-verdict avoidance, strict grounding,
  mandatory citation, out-of-scope refusal — NOT PII redaction (PII flagging is secondary/
  non-blocking; a user's own case facts must not be stripped, since they drive routing).
- Evaluation: RAGAS and DeepEval for generation quality; implement retrieval metrics (R@1, R@3,
  MRR@10, NDCG@3) yourself per the standard formulas — do not skip these because a framework
  doesn't provide them out of the box.
- Orchestration: LangChain for prompt assembly, chaining, and LLM invocation.

BUILD IN THIS ORDER:

0. EVALUATION SET FIRST (per methodology Part B — build this before any pipeline code)
   - Expand the 5 seed questions into 20+ labeled questions: question text, ground-truth source
     document (and section if possible), short ideal answer. Cover each of the 4 PDFs
     individually, cross-document boundary cases (does the model correctly NOT answer an ECOA
     question from the Fair Housing Act chapter), the CSV trend question, the no-verdict refusal
     case, and the out-of-scope case. Save as evaluation/golden_dataset.jsonl.
   - Implement retrieval_metrics.py: R@1, R@3, MRR@10, NDCG@3 per the standard formulas (see
     architecture doc §2.8 for the plain-English definitions and formulas).

1. DATA INGESTION LAYER — Stages 1–4 (each a required ablation experiment)
   - Stage 1 (Parsing): implement pypdf AND pdfplumber (add PyMuPDF if time allows) loaders for
     the four PDFs. Measure % pages with clean extracted text and downstream R@3 through the same
     chunk/embed pipeline. Produce the Stage 1 table, pick a winner in writing.
   - Stage 2 (Chunking): implement fixed-size, fixed-size+overlap, and recursive/sentence-aware
     chunking at 2+ sizes (e.g. 300/500/800 tokens) and overlaps (e.g. 0/50/100) — bias smaller
     given these are 3-6 page chapters. Metadata per chunk: source_doc, law, section, content_hash.
     Measure R@1/R@3/MRR@10/NDCG@3 for each combination. Produce the Stage 2 table, pick a winner.
   - Stage 3 (Embedding model): implement at least 2 of all-MiniLM-L6-v2 / bge-small-en-v1.5 /
     text-embedding-3-small / multi-qa-mpnet-base-dot-v1. Measure R@1/R@3/MRR@10/NDCG@3/latency.
     Produce the Stage 3 table, pick a winner — pay extra attention here since legal terminology
     can behave differently across general-purpose embedding models.
   - Stage 4 (Vector DB): upsert the winning chunking+embedding pipeline's output into BOTH
     Pinecone and (ChromaDB or FAISS). Measure R@3 parity, index build time, metadata-filter
     support, persistence. Justify the Pinecone production choice on the operational axes even if
     R@3 is roughly equal (expected, per methodology).
   - Also build the BM25 sparse index over the winning chunks (needed for Stage 5), and the FRED
     CSV loader + trend-computation tool (SQLite/pandas), and a POST /ingest admin endpoint.

2. RETRIEVAL / INFERENCE LAYER — Stages 5–7 (each a required ablation experiment)
   - Query router: legal/rights question → retrieval path; numeric/trend question → FRED tool
     call; out-of-scope → guardrail refusal path.
   - Stage 5 (Retrieval mode): implement dense-only (Pinecone), sparse-only (BM25), and hybrid.
     Split your 20+ eval questions into keyword-style vs. paraphrased/semantic style, and report
     R@1/R@3/MRR@10/NDCG@3 both overall AND per query-type split. Produce the Stage 5 table.
   - Stage 6 (Hybrid merge — only if Stage 5 picks hybrid): implement RRF (k≈60) and weighted
     linear combination swept across ≥3 α values. Produce the Stage 6 table; state the winning α
     (or RRF) and why, citing the numbers.
   - Stage 7 (Reranking): implement no-reranker vs. cross-encoder (e.g.
     cross-encoder/ms-marco-MiniLM-L-6-v2) on top-20 → top-3/5. Measure R@3, NDCG@3, added
     latency. Produce the Stage 7 table; justify whether the accuracy gain is worth the latency
     for a support-hotline bot.
   - Also implement optional law-metadata filtering/boosting once intent is classified — this is
     this group's specific core-skill test (routing accuracy), separate from the shared 8 stages.
   - Below-threshold retrieval confidence on any path → "insufficient information in these
     documents" fallback, never a guess.

3. CONVERSATION MEMORY / PERSISTENCE LAYER (SQLite) — lower priority, build after 1/2/4/5/8 work
   - Schema: users(user_id, created_at, profile_json), sessions(session_id, user_id, created_at,
     last_active_at), messages(message_id, session_id, role, content, token_count, created_at),
     summaries(summary_id, session_id, summary_text, covers_up_to_message_id, created_at).
   - Token-budget manager: when cumulative unsummarized tokens cross threshold T, summarize all
     turns except the most recent N into `summaries`; prompt-history assembly = [latest summary if
     present] + [last N raw turns]. Acceptance tests are single-turn, so keep this functional but
     simple — it is not the graded surface.

4. GUARDRAIL / MODERATION MIDDLEWARE (LangChain Guardrails) — critical, test-first priority
   - Inbound: prompt-injection/jailbreak detection; domain-scope check (fair-lending/credit-rights
     only, refuse the out-of-scope test case — confirm the exact scenario with the instructor,
     candidates: a competitor bank's policy question, or an unrelated tax-filing request); optional
     PII flag-for-user-awareness (do not silently alter the user's stated facts).
   - Outbound (primary, must pass acceptance test #5): detect/block/rewrite any answer rendering a
     legal verdict — correct behavior is explaining the applicable law and suggesting a complaint
     to the appropriate regulator if facts plausibly match. Detect/block any legal claim not
     traceable to a retrieved chunk. Enforce that every substantive answer names its source
     chapter (cross-cutting requirement for all 9 capstone groups).
   - Implement as FastAPI middleware/dependency wrapping the chat endpoint, returning:
     {action: allow|rewrite|block, reason, citations_present, violations[]}.
   - All thresholds/phrase-rules live in an external policy config file, not hardcoded.
   - Write acceptance test #5 as the first guardrail unit test; write the out-of-scope test (#6)
     as the second.

5. LLM ORCHESTRATION LAYER — Stage 8 (required ablation experiment)
   - Compose: system prompt (including the no-legal-verdict instruction) + retrieved context with
     citations (or FRED tool result) + assembled history/summary + user query → LLM call → parsed,
     cited answer.
   - Stage 8: compare ≥2 real LLMs (e.g. Gemini 2.5/2.0 Flash, GPT-4o-mini, Claude Haiku, a local
     Ollama model), retrieval pipeline held fixed at the Stage 1-7 winners so only the generator
     varies. Measure RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall),
     DeepEval (Hallucination, G-Eval), cost/query, latency. Produce the Stage 8 table, pick a
     winner citing the numbers.
   - Support streaming responses back through FastAPI (SSE) to the Angular client.
   - Centralize and version all prompt templates in a prompts/ directory.

6. API GATEWAY LAYER (FastAPI)
   - Endpoints: POST /chat (guardrail → route → retrieve/tool-call → memory → orchestration →
     guardrail → persistence → response), GET /chat/history/{session_id}, GET /users/{user_id}/
     profile, POST /ingest (admin), GET /health.
   - Pydantic schemas, structured error handling, request correlation IDs, CORS for the Angular
     origin.

7. ANGULAR UI
   - Chat interface with streaming answer rendering, mandatory citation display (source chapter
     name), guardrail notices when an answer was rewritten/blocked, session/user id handling,
     conversation history view.

8. FINAL EVALUATION REPORT (the headline deliverable)
   - Assemble all 8 ablation tables (Stages 1-8) with real measured numbers — no placeholders.
   - Synthesis paragraph citing numbers from every table (see architecture doc §2.8 for the exact
     example format expected).
   - End-to-end RAGAS + DeepEval scores on the FINAL chosen pipeline (all winners combined).
   - Run and report the 6 acceptance tests (§2.9 of the architecture doc) with actual answer text
     for each, pass/fail.
   - This group's own metrics: law-routing accuracy, legal-verdict-avoidance rate, citation-
     presence rate.
   - A short "what we'd try next" section.
   - Save as evaluation/evaluation_report.md.

NON-FUNCTIONAL REQUIREMENTS:
- All layers independently testable (unit tests per layer, integration test for the full /chat
  flow, and the 6-test acceptance file).
- Configuration (Pinecone/Chroma keys, embedding model name, chunk size, token thresholds N/T,
  guardrail policy, grounding threshold, hybrid α) environment-variable/config-file driven, never
  hardcoded.
- Log every turn (query, route taken, retrieved chunk ids or tool call, answer, guardrail verdict)
  for observability and to feed the evaluation layer.
- Provide a docker-compose setup to run the Angular UI, FastAPI service, and SQLite volume together.
- Include a README documenting environment variables, how to run ingestion, how to run each of the
  8 ablation stages, how to run the app, and how to run the acceptance tests.

DELIVERABLE FORMAT: For each build step above, provide the code files, the ablation table(s) for
that step where applicable with real numbers and a written winner justification, and the commands
to run/test that layer, before proceeding to the next step. The final message of the build should
assemble the complete evaluation report (all 8 ablation tables + end-to-end scores + acceptance-
test results + synthesis paragraph) as evaluation/evaluation_report.md.
```

---

## 6. Open Design Decisions Worth Confirming Before Build

- **UI stack sign-off.** Course rule states Streamlit/FastAPI+Streamlit; this doc keeps Angular per
  your explicit instruction. Confirm this substitution is acceptable before investing frontend time.
- **Out-of-scope test scenario.** Not explicitly named in this group's `REQUIREMENT.md` but
  required by `REQUIREMENTS_OVERVIEW.md`. Candidates: a competitor bank's policy question, or an
  unrelated request (tax filing, live account access). Pick one and add it as acceptance test #6.
- **Vector-DB ablation partner.** Chroma vs. FAISS for the Stage 4 comparison against Pinecone —
  Chroma is usually faster to stand up locally for a one-off comparison; FAISS has no persistence
  layer out of the box, which itself is a data point for the "persistence?" column.
- **Embedding model shortlist for Stage 3** — the requirement explicitly flags legal terminology as
  a place general-purpose embedding models can diverge; consider including at least one model with
  stronger domain-general performance (e.g. `text-embedding-3-small`) alongside a smaller/faster
  local option (e.g. `bge-small-en-v1.5`) to make the latency/quality trade-off visible in the table.
- **LLM shortlist for Stage 8** — confirm API access/budget for at least 2 of Gemini Flash /
  GPT-4o-mini / Claude Haiku / a local Ollama model before committing to the comparison.
- **FRED CSV handling** — tool-call-over-SQLite (recommended) vs. pre-computed rolling-window text
  summaries embedded alongside the PDF chunks; this affects acceptance test #4 directly.
- **Complaint-routing detail** — confirm the source PDFs actually name specific regulators (CFPB,
  HUD, the Fed) per law, since the no-invented-law rule means the bot can only name a regulator if
  it's grounded in the ingested text.
- **Token thresholds** `T`/`N` for the (lower-priority) conversation memory layer — reasonable
  starting point: `T ≈ 3000 tokens`, `N = 4–6` turns; not part of the graded evaluation.
