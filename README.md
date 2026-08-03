# Consumer Credit Rights Assistant
### Capstone Group 6 — `06_finance_complaints`

A RAG chatbot that explains a consumer's rights under **ECOA (Regulation B)**, the **Fair Housing Act**, and general fair-lending law — grounded strictly in four Federal Reserve Consumer Compliance Handbook chapters and one FRED structured time-series (total US consumer credit outstanding).

> ⚠️ **Instructor sign-off needed before build:**
> 1. **UI stack** — course rule states "Streamlit or FastAPI+Streamlit." This project uses **Angular** as a deliberate substitution. Confirm acceptability before investing frontend time.

---

## Table of Contents

1. [Project Scope](#1-project-scope)
2. [Tech Stack](#2-tech-stack)
3. [Repository Structure](#3-repository-structure)
4. [Grading Weights](#4-grading-weights)
5. [Source Documents](#5-source-documents)
6. [Environment Setup](#6-environment-setup)
7. [Running the Application](#7-running-the-application)
8. [Running Data Ingestion](#8-running-data-ingestion)
9. [Running the 8 Ablation Stages](#9-running-the-8-ablation-stages)
10. [Running the Acceptance Tests](#10-running-the-acceptance-tests)
11. [Evaluation Metrics](#11-evaluation-metrics)
12. [Acceptance Tests](#12-acceptance-tests)
13. [Architecture Overview](#13-architecture-overview)
14. [Open Design Decisions](#14-open-design-decisions)

---

## 1. Project Scope

The assistant answers questions about:

- **ECOA / Regulation B** — credit-decision discrimination (age, race, sex, national origin, religion, marital status, receipt of public assistance)
- **Fair Housing Act** — housing/mortgage-related lending discrimination
- **Fair Lending Overview** — general fair-lending law and framework
- **Consumer Compliance Handbook Intro** — handbook scope and cross-cutting rules

It also answers numeric trend questions using FRED data (total US consumer credit outstanding, 1943–present).

**Core skill under evaluation:** correct law-to-scenario routing — does the answer cite ECOA vs. the Fair Housing Act for the right scenario?

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular (latest stable), SSE-based streaming chat UI |
| API gateway | Python 3.11+, FastAPI |
| Vector store (production) | Pinecone (serverless) |
| Vector store (ablation) | ChromaDB or FAISS (local, Stage 4 comparison only) |
| Sparse retrieval | BM25 via `rank_bm25` |
| Structured data | FRED CSV → SQLite / pandas |
| Persistence | SQLite via SQLAlchemy |
| Guardrails | LangChain Guardrails (FastAPI middleware) |
| Orchestration | LangChain (`Runnable` / chain) |
| Evaluation | RAGAS, DeepEval, custom R@k / MRR / NDCG |

---

## 3. Repository Structure

```
RAG_FINANCE/
├── frontend/
│   └── ui/                          # Angular SPA
│       └── src/app/{chat,session,shared}/
├── backend/
│   ├── data/                        # Place source PDFs + FRED CSV here (not committed)
│   ├── api/                         # FastAPI service
│   │   ├── main.py
│   │   ├── routers/  chat.py · ingest.py · users.py · health.py
│   │   ├── schemas/                 # Pydantic models
│   │   ├── middleware/guardrails.py
│   │   ├── core/config.py
│   │   └── deps.py
│   ├── ingestion/
│   │   ├── parsers/                 # pypdf / pdfplumber / PyMuPDF  (Stage 1)
│   │   ├── chunking/                # fixed / recursive / semantic   (Stage 2)
│   │   ├── embeddings/              # model wrappers                 (Stage 3)
│   │   ├── sparse_index.py          # BM25 index build
│   │   ├── pinecone_upsert.py
│   │   ├── chroma_upsert.py         # Stage 4 ablation
│   │   └── faiss_upsert.py          # Stage 4 ablation
│   ├── structured_data/
│   │   ├── fred_loader.py           # Load FRED CSV into SQLite
│   │   └── trend_tool.py            # Compute delta/trend over date range
│   ├── retrieval/
│   │   ├── embed_query.py
│   │   ├── router.py                # legal / trend / out-of-scope classifier
│   │   ├── dense_retriever.py       # Pinecone             (Stage 5)
│   │   ├── sparse_retriever.py      # BM25                 (Stage 5)
│   │   ├── hybrid_merge.py          # RRF / weighted-α     (Stage 6)
│   │   ├── reranker.py              # cross-encoder         (Stage 7)
│   │   └── context_builder.py
│   ├── memory/
│   │   ├── db.py
│   │   ├── models.py                # SQLAlchemy ORM: users, sessions, messages, summaries
│   │   ├── token_budget.py          # Rolling summarisation trigger
│   │   └── summarizer.py
│   ├── orchestration/
│   │   ├── prompts/                 # Versioned prompt templates
│   │   ├── chains.py                # LangChain RAG chain
│   │   └── llm_client.py            # Multi-provider LLM client (Stage 8)
│   ├── guardrails/
│   │   ├── policy.yaml              # Phrase rules, thresholds, citation config
│   │   └── rules.py                 # check_inbound / check_outbound
│   ├── evaluation/
│   │   ├── golden_dataset.jsonl     # 20+ labeled questions
│   │   ├── retrieval_metrics.py     # R@1, R@3, MRR@10, NDCG@3
│   │   ├── run_ragas.py
│   │   ├── run_deepeval.py
│   │   ├── acceptance_tests.py      # 6 acceptance tests (§2.9)
│   │   ├── evaluation_report.md     # Final Part-D deliverable
│   │   └── ablation/
│   │       ├── stage1_parsing.py
│   │       ├── stage2_chunking.py
│   │       ├── stage3_embedding.py
│   │       ├── stage4_vectordb.py
│   │       ├── stage5_retrieval_mode.py
│   │       ├── stage6_hybrid_merge.py
│   │       ├── stage7_reranking.py
│   │       └── stage8_llm.py
│   └── tests/                       # pytest unit + integration tests
├── .env.example                     # All required env vars (copy → .env)
├── docker-compose.yml
└── README.md
```

---

## 4. Grading Weights

| Component | Weight |
|---|---|
| Evaluation rigor — ablation tables complete, real numbers, justified winner per stage | 40% |
| Correctness on acceptance-test questions | 30% |
| End-to-end RAGAS + DeepEval scores on the final chosen pipeline | 20% |
| Code quality / app usability | 10% |

> A stage with a **placeholder** instead of real numbers scores **zero** for that stage.

---

## 5. Source Documents

Place these files in `backend/data/` before running ingestion. They are not committed to the repo.

| File | Pages | Coverage |
|---|---|---|
| `FedReserve_ECOA_Regulation_B.pdf` | 6 | Credit-decision discrimination law |
| `FedReserve_Fair_Housing_Act.pdf` | 3 | Housing/mortgage lending discrimination |
| `FedReserve_Fair_Lending_Overview.pdf` | 3 | General fair-lending law overview |
| `FedReserve_Consumer_Compliance_Handbook_Intro.pdf` | 6 | Handbook scope / front matter |
| `FRED_Total_Consumer_Credit.csv` | — | Monthly US consumer credit, 1943–present |

---

## 6. Environment Setup

### Prerequisites

- Python 3.11 (tested on 3.11.9)
- Node.js 18+ and npm (for Angular frontend)
- Docker + Docker Compose (optional, for containerised run)

### Step 1 — Clone and create virtual environment

```bash
git clone <repo-url>
cd RAG_FINANCE
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
```

### Step 2 — Copy and fill environment variables

```bash
cp .env.example .env
# Edit .env and fill in the values below
```

### Required Environment Variables

| Variable | Description |
|---|---|
| `PINECONE_API_KEY` | Pinecone serverless API key |
| `PINECONE_ENV` | Pinecone environment / region |
| `PINECONE_INDEX_NAME` | Name of the Pinecone index |
| `OPENAI_API_KEY` | OpenAI API key (embeddings + optional LLM) |
| `GEMINI_API_KEY` | Google Gemini API key (Stage 8 LLM candidate) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (Stage 8 LLM candidate) |
| `EMBEDDING_MODEL` | Active embedding model name (e.g. `all-MiniLM-L6-v2`) |
| `CHUNK_SIZE` | Chunk size in tokens (e.g. `500`) |
| `CHUNK_OVERLAP` | Chunk overlap in tokens (e.g. `50`) |
| `RAG_TOP_K` | Number of chunks to retrieve (e.g. `5`) |
| `GROUNDING_THRESHOLD` | Min similarity score before fallback (e.g. `0.65`) |
| `HYBRID_ALPHA` | Dense weight in hybrid merge (e.g. `0.5`) |
| `TOKEN_BUDGET_T` | Max unsummarised tokens before summarisation trigger (e.g. `3000`) |
| `TOKEN_BUDGET_N` | Raw turns to keep after summarisation (e.g. `5`) |
| `API_HOST` | FastAPI host (e.g. `0.0.0.0`) |
| `API_PORT` | FastAPI port (e.g. `8000`) |
| `SQLITE_DB_PATH` | Path to SQLite database file (e.g. `./backend.db`) |

> **Note:** There is no `API_KEY` variable — this is a combined POC project and does not use API-key-based authentication on the gateway endpoints.

### Step 3 — Install backend dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` lives at the repo root. It covers all layers (API, ingestion, retrieval, orchestration, evaluation, dev tools).

### Step 4 — Install frontend dependencies

```bash
cd frontend
npm install
```

---

## 7. Running the Application

### Option A — Docker Compose (recommended)

```bash
docker-compose up --build
```

- Angular UI → [http://localhost:4200](http://localhost:4200)
- FastAPI backend → [http://localhost:8000](http://localhost:8000)
- API docs → [http://localhost:8000/docs](http://localhost:8000/docs)

### Option B — Local (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
ng serve
```

### API Endpoints (implemented)

The FastAPI gateway layer is fully wired with Pydantic validation, CORS, correlation-ID middleware, and structured error handling. No API-key authentication is applied (POC mode).

| Method | Path | Status | Description |
|---|---|---|---|
| `POST` | `/chat` | ✅ Implemented (stub pipeline) | Accepts `{user_id, session_id, query}`, returns structured `ChatResponse` with answer, citations, guardrail verdict, route, and token usage |
| `GET` | `/chat/history/{session_id}` | ✅ Implemented (stub) | Returns conversation history for a session |
| `POST` | `/ingest` | ✅ Implemented (stub) | Triggers document ingestion pipeline |
| `GET` | `/users/{user_id}/profile` | ✅ Implemented (stub) | Returns user profile / intent store |
| `GET` | `/health` | ✅ Implemented | Liveness probe with uptime |
| `GET` | `/metrics` | ✅ Implemented (stub) | Runtime counters |

#### Request / Response schemas

**`POST /chat` request body:**
```json
{
  "user_id": "u1",
  "session_id": "s1",
  "query": "Can a bank deny me credit because of my age?"
}
```

**`POST /chat` response:**
```json
{
  "user_id": "u1",
  "session_id": "s1",
  "answer": "...",
  "citations": [{"source_doc": "...", "law": "ECOA/RegB", "section": "...", "chunk_id": "..."}],
  "guardrail": {"action": "allow", "reason": null, "citations_present": true, "violations": []},
  "route": "legal",
  "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

#### Quick test

```bash
# Health check
curl http://localhost:8000/health

# Chat (returns stub response until retrieval + LLM layers are wired)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","session_id":"s1","query":"Can a bank deny me credit because of my age?"}'
```

---

## 8. Running Data Ingestion

> Place all five source files in `backend/data/` before running ingestion.

### Full production ingestion (uses winners from ablation stages)

```bash
cd backend
python -m ingestion.ingest_embed
```

### Trigger via API

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"force_reingest": false}'
```

Ingestion is **idempotent** — chunks are deduplicated by `content_hash`. Re-running does not create duplicate vectors.

### Load FRED CSV into SQLite

```bash
cd backend
python -m structured_data.fred_loader
```

---

## 9. Running the 8 Ablation Stages

Each stage script is self-contained. Run stages in order (1 → 8) because later stages depend on the winner of earlier ones.

> All scripts write their results table to stdout and to a `.json` / `.md` results file alongside the script.

### Stage 1 — Parsing

```bash
cd backend
python evaluation/ablation/stage1_parsing.py
```

Compares `pypdf`, `pdfplumber`, and `PyMuPDF`. Reports: clean text %, downstream R@3.

### Stage 2 — Chunking

```bash
python evaluation/ablation/stage2_chunking.py
```

Compares fixed-size, fixed+overlap, and recursive chunking at sizes 300/500/800 tokens and overlaps 0/50/100. Reports: R@1, R@3, MRR@10, NDCG@3.

### Stage 3 — Embedding Model

```bash
python evaluation/ablation/stage3_embedding.py
```

Compares `all-MiniLM-L6-v2`, `bge-small-en-v1.5`, `text-embedding-3-small`. Reports: R@1, R@3, MRR@10, NDCG@3, latency (ms/query).

### Stage 4 — Vector DB

```bash
python evaluation/ablation/stage4_vectordb.py
```

Compares Pinecone vs. ChromaDB (local). Reports: R@3 parity, index build time, metadata filtering support, persistence.

### Stage 5 — Retrieval Mode

```bash
python evaluation/ablation/stage5_retrieval_mode.py
```

Compares dense-only, sparse-only (BM25), and hybrid. Results split by keyword vs. semantic query type. Reports: R@1, R@3 (all + per type), MRR@10, NDCG@3.

### Stage 6 — Hybrid Merge (run only if Stage 5 picks hybrid)

```bash
python evaluation/ablation/stage6_hybrid_merge.py
```

Compares RRF (k=60) vs. weighted linear combination (α = 0.3 / 0.5 / 0.7). Reports: R@3, MRR@10, NDCG@3.

### Stage 7 — Reranking

```bash
python evaluation/ablation/stage7_reranking.py
```

Compares no reranker vs. `cross-encoder/ms-marco-MiniLM-L-6-v2` on top-20 → top-5. Reports: R@3, NDCG@3, added latency (ms).

### Stage 8 — LLM for Generation

```bash
python evaluation/ablation/stage8_llm.py
```

Compares ≥2 LLMs (Gemini 2.0 Flash, GPT-4o-mini, Claude Haiku) with retrieval pipeline held fixed. Reports: RAGAS Faithfulness, Answer Relevancy, Context Precision, DeepEval Hallucination, G-Eval, cost/query, latency.

---

## 10. Running the Acceptance Tests

```bash
cd backend
pytest evaluation/acceptance_tests.py -v
```

| # | Question | Expected outcome |
|---|---|---|
| 1 | "I was denied a mortgage — can a bank consider my age in that decision?" | ECOA / Reg B answer, cited |
| 2 | "What protections exist if I think I was denied housing credit because of my race?" | Fair Housing Act answer, cited |
| 3 | "What's the overall purpose of fair lending law?" | Overview doc answer |
| 4 | "Has total US consumer credit gone up or down over the last year?" | FRED CSV structured-data path |
| 5 | "Was I definitely discriminated against?" | Declines to render a verdict; explains law; suggests regulator complaint |
| 6 | "What's Chase Bank's overdraft fee policy?" | Out-of-scope refusal; redirects to fair-lending scope |

---

## 11. Evaluation Metrics

### Retrieval metrics (implemented in `evaluation/retrieval_metrics.py`)

| Metric | Formula |
|---|---|
| **R@1** | 1 if correct chunk is rank #1, else 0 — averaged over all queries |
| **R@3** | 1 if correct chunk appears in top 3, else 0 — averaged over all queries |
| **MRR@10** | `1 / rank` if correct chunk in top 10, else 0 — averaged over all queries |
| **NDCG@3** | Graded-relevance DCG@3 normalised against ideal ranking (0–1) |

### Generation metrics

| Metric | Tool | What it catches |
|---|---|---|
| Faithfulness | RAGAS | Hallucinated legal claims |
| Answer Relevancy | RAGAS | Off-topic answers |
| Context Precision | RAGAS | Irrelevant chunks retrieved |
| Context Recall | RAGAS | Relevant chunks missed |
| Hallucination | DeepEval | Second-judge hallucination score |
| G-Eval | DeepEval | Overall generation quality |

### Group 6 specific metrics

| Metric | Description |
|---|---|
| Law-routing accuracy | % of answers citing the correct source document (ECOA vs. Fair Housing Act) |
| Legal-verdict-avoidance rate | % of test cases with no verdict language in the answer |
| Citation-presence rate | % of substantive answers containing a source chapter citation |

---

## 12. Acceptance Tests

Run the full suite:

```bash
pytest backend/evaluation/acceptance_tests.py -v
```

Run a single test:

```bash
pytest backend/evaluation/acceptance_tests.py::test_ecoa_age_mortgage -v
```

---

## 13. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        ANGULAR UI (SPA)                       │
│  Chat · Session handling · SSE streaming · Citation display   │
└──────────────────────────┬───────────────────────────────────┘
                            │ REST / SSE
┌──────────────────────────▼───────────────────────────────────┐
│                    FASTAPI GATEWAY LAYER                       │
│  Pydantic validation · CORS · Correlation IDs · Routing       │
└──────────────────────────┬───────────────────────────────────┘
                            │
┌──────────────────────────▼───────────────────────────────────┐
│              GUARDRAIL / MODERATION LAYER (Middleware)         │
│  Inbound:  injection detection · domain-scope check           │
│  Outbound: no-verdict rule · no-invented-law · citation check │
└──────────────────┬───────────────────┬───────────────────────┘
                   │                   │
        ┌──────────▼──────┐   ┌────────▼──────────────┐
        │  DATA INGESTION  │   │  RETRIEVAL / INFERENCE │
        │  (offline batch) │   │  (online, per request) │
        │  Parse→Chunk→    │   │  Route→Retrieve→       │
        │  Embed→Index     │   │  Rerank→Context→LLM    │
        └──────────────────┘   └───────────────────────┘
                            │
┌──────────────────────────▼───────────────────────────────────┐
│            CONVERSATION MEMORY / PERSISTENCE (SQLite)          │
│  users · sessions · messages · summaries · token budget       │
└──────────────────────────┬───────────────────────────────────┘
                            │
┌──────────────────────────▼───────────────────────────────────┐
│                  LLM ORCHESTRATION LAYER                       │
│  PromptTemplate → LLM → OutputParser (LangChain Runnable)     │
└──────────────────────────┬───────────────────────────────────┘
                            │
┌──────────────────────────▼───────────────────────────────────┐
│         EVALUATION LAYER — 8 ablation stages + end-to-end     │
│  Retrieval: R@1 R@3 MRR@10 NDCG@3 · Generation: RAGAS+DeepEval│
└──────────────────────────────────────────────────────────────┘
```

### Data flow (single user turn)

1. Angular sends `{user_id, session_id, query}` to `POST /chat`
2. FastAPI validates payload and loads session context
3. Guardrail middleware scans for injection, domain scope, optional PII flag
4. Router classifies: **legal** → retrieval pipeline · **trend** → FRED tool · **out-of-scope** → refusal
5. Memory layer supplies `[summary + last N turns]`
6. Orchestration builds prompt → calls LLM → receives answer
7. Outbound guardrail checks: no verdict · grounded · citation present
8. Persistence stores turn; triggers summarisation if token budget exceeded
9. Response (answer + citations + guardrail flags) streamed back to Angular

---

## 14. Open Design Decisions

| Decision | Status | Notes |
|---|---|---|
| UI stack (Angular vs. Streamlit) | ⚠️ Needs instructor sign-off | Angular kept per project owner instruction |
| Out-of-scope test scenario (acceptance test #6) | ⚠️ Needs instructor sign-off | Proposed: Chase Bank overdraft policy query |
| Vector DB ablation partner | Decided: ChromaDB | Faster local setup than FAISS; FAISS has no built-in persistence |
| Embedding model shortlist (Stage 3) | Decided: MiniLM + BGE + text-embedding-3-small | Covers fast local vs. quality cloud options |
| LLM shortlist (Stage 8) | Confirm API access | Gemini 2.0 Flash · GPT-4o-mini · Claude Haiku |
| FRED CSV handling | Decided: SQLite tool call | Arithmetic over rows, not vector retrieval |
| Regulator naming | Verify in source PDFs | CFPB / HUD / DOJ — only cite if grounded in ingested text |
| Token budget T / N | Starting point | T ≈ 3000 tokens · N = 5 turns (not graded) |
