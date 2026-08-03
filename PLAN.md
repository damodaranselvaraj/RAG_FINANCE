# Plan — Consumer Credit Rights Assistant (RAG Capstone, Group 6)

Source requirement: `data/REQUIREMENT.md` (+ `data/GROUP_README.md`).
Shared grading methodology: `EVALUATION_METHODOLOGY.md` (copied from
`10_RAG/student_group_datasets/EVALUATION_METHODOLOGY.md`).

## 1. Mission
A chatbot for a consumer credit-rights helpline that explains rights under
**ECOA (Regulation B)** and the **Fair Housing Act**, grounded strictly in
4 Federal Reserve Consumer Compliance Handbook chapters + 1 FRED CSV time
series. Must cite sources, route the right law to the right scenario
(credit denial → ECOA, housing/mortgage → FHAct), and refuse to render legal
verdicts — explain the law, suggest filing a complaint instead.

## 2. Why the methodology drives every decision
Grading is 40% evaluation rigor, 30% correctness on the 5 acceptance
questions, 20% end-to-end RAGAS/DeepEval, 10% code quality. So the eval
harness (`eval/`) is not an afterthought bolted onto a finished chatbot —
it is built first, against real ground truth, and every pipeline choice
in `src/` is picked because an ablation table said so.

## 3. Data handling decisions
- **4 PDFs** → parsed per-page, chunked, embedded, indexed — standard path.
- **CSV (`FRED_Total_Consumer_Credit.csv`, 1943–2026, monthly)** → NOT put
  through a SQL/pandas agent (out of scope per requirement — it just says
  "chunk and index... plus the CSV"). Instead: `src/parsing.py` converts it
  into a handful of narrative text chunks (recent 12-month trend, all-time
  high/low, decade-over-decade growth) tagged
  `source="FRED_Total_Consumer_Credit.csv"`, so it flows through the exact
  same chunk → embed → retrieve → cite pipeline as the PDFs. This is the
  simplest approach that still lets acceptance question #4 ("has consumer
  credit gone up or down over the last year") be answered with a citation.

## 4. Ablation plan (`eval/ablation_runner.py`, Stages 1–7 — no LLM calls, no cost)
1. **Parsing**: `pypdf` vs `pdfplumber` vs `PyMuPDF(fitz)` — clean-text %,
   downstream R@3.
2. **Chunking**: fixed/no-overlap vs fixed+overlap vs recursive — sizes
   300/500/800, overlaps 0/50/100.
3. **Embeddings**: `all-MiniLM-L6-v2` vs `bge-small-en-v1.5` vs
   `multi-qa-mpnet-base-dot-v1` — legal-domain terms called out in the
   requirement as the reason this stage matters most for this group.
4. **Vector DB**: ChromaDB vs FAISS — parity + operational axes.
5. **Retrieval mode**: dense vs sparse (BM25) vs hybrid, broken out by
   keyword vs semantic query type (tagged per-question in
   `eval_questions.json`).
6. **Hybrid fusion**: RRF vs weighted linear (α sweep) — only if hybrid wins.
7. **Reranking**: none vs cross-encoder `ms-marco-MiniLM-L-6-v2`.

All of Stages 1–7 run entirely on local models (`sentence-transformers`,
`bm25s`, `chromadb`/`faiss`, a local cross-encoder) — **zero API cost**.

## 5. Generation + end-to-end eval (`eval/generation_eval.py`, needs `OPENAI_API_KEY`)
8. **LLM comparison**: fix the Stage-1–7 winning retrieval config, vary only
   the generator — `gpt-4o-mini` vs `gpt-4o` (both via `langchain-openai`,
   matching the reference `production_rag_chatbot` stack) — score with
   RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context
   Recall) and DeepEval (Hallucination, G-Eval, Answer Relevancy,
   Faithfulness).
9. Final end-to-end RAGAS + DeepEval run on the fully assembled pipeline —
   the headline number for `EVALUATION_REPORT.md`.

## 6. Final pipeline (`src/pipeline.py`)
Adapted from the reference `10_RAG/notebooks/production_rag_chatbot/rag_pipeline.py`
(parse → chunk → hybrid index → RRF fuse → cross-encoder rerank → cited
generation → groundedness guardrail → memory), with two additions specific
to this group's requirement:
- **Law router / citation discipline**: prompt explicitly instructs the LLM
  to name which law (ECOA/Reg B vs FHAct) it is answering from, since
  requirement #3 grades "correct law-to-scenario routing."
- **No-legal-verdict guardrail**: a second guardrail (separate from the
  groundedness one) that rewrites/refuses "was I discriminated against"
  style questions into "here's what the law says, consider filing a
  complaint with [regulator]" — this is graded at 30% weight alongside
  routing correctness.

## 7. Deliverables checklist (maps 1:1 to `REQUIREMENT.md` §8–9)
- [ ] Working chatbot — `app.py` (Streamlit, mirrors reference app UX)
- [ ] 8 ablation tables, real numbers — `EVALUATION_REPORT.md`
- [ ] Acceptance test results (5 questions) — `EVALUATION_REPORT.md`
- [ ] End-to-end RAGAS + DeepEval on final pipeline — `EVALUATION_REPORT.md`

## 8. Run order
```
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY
python eval/ablation_runner.py        # Stages 1-7, writes eval/results/*.csv, no cost
python eval/generation_eval.py        # Stage 8 + end-to-end RAGAS/DeepEval, costs a few $ in API calls
streamlit run app.py                  # final chatbot
```
Fill `EVALUATION_REPORT.md` tables from `eval/results/*.csv` once both
scripts have run.
