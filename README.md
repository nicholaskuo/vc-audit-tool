# VC Portfolio Valuation Engine

Nicholas Kuo
AI-assisted company valuations with deterministic math. Built with FastAPI, React, and OpenAI API.

## Problem & Approach

VC portfolio valuation requires combining multiple methodologies — comparable company analysis, DCF, and last-round adjustments — with subjective research that's traditionally manual and inconsistent. This engine automates the process with a core principle: **LLM at the edges, determinism in the core**. OpenAI handles research (web search for financials/comps), data enrichment, and narrative generation, while all valuation math runs as pure functions with no external dependencies. A 7-step pipeline (Validate → Research → Enrich → Fetch → Valuate → Narrate → Persist) processes each request, with graceful degradation at every step — if one valuation method fails, the remaining methods are blended automatically.

## Key Design Decisions

### LLM at the Edges, Determinism in the Core

The pipeline uses LLMs for three tasks: web-search research, structuring/enrichment, and narrative generation. All valuation math (comp scoring, DCF, last-round adjustment, blending) is pure functions with no randomness or external dependencies. The enrichment step uses `temperature=0` and structured JSON output to minimize LLM variance, plus deterministic Python guards that override the LLM's method selection (e.g., force-adding `comps` if revenue exists, removing `dcf` if no projections were estimated). This means the LLM can suggest which tools to run, but the system has the final say — preventing hallucinated methods from reaching the valuation engine.

### Ensemble Valuation with Confidence-Aware Weighting

Three methodologies (comps, DCF, last-round) run independently and are blended via weighted average. Default weights are heuristic-based on data quality signals: comp count (>=3 → 0.40, <3 → 0.25), whether DCF inputs are user-provided vs LLM-estimated (0.35 vs 0.15), last-round staleness (>18 months → 0.15). Weights normalize to 1.0. The `/reweight` endpoint re-runs only the pure blender — no LLM calls, no data re-fetching — so analysts can adjust weights instantly and see how the valuation changes. Tradeoff: heuristic weights are transparent and auditable, but don't capture cross-methodology correlation (listed as a potential improvement).

### LLM-Driven Method Selection with Deterministic Guards

The enrichment LLM decides which valuation methods are applicable based on what data it found via web search. After the LLM responds, Python post-processing enforces invariants: comps is force-added if any revenue source exists, dcf is removed if no growth projections were estimated, last_round is added if funding data was found. All LLM-estimated projections and last-round data have confidence forced to `"low"` regardless of what the LLM claimed. This avoids both over-reliance on LLM judgment and rigid user-must-specify-everything UX.

### Graceful Degradation at Every Step

Each pipeline step (research, enrich, fetch, valuate, narrate) is wrapped in error handling that captures failures but continues execution. If enrichment fails, raw user inputs are used. If one valuation method fails, the remaining methods are blended. If narration fails, a fallback template is used. Market data fetching degrades per-ticker: a batch of 5 comps can have 3 live and 2 mock, tracked via `data_source` metadata on each comparable. The pipeline always persists results — even partial failures — so no work is lost.

### Full Audit Trail and Observability

Every LLM call stores the full prompt (including injected JSON schema), raw response, token count, and latency in both an in-memory log and the database. The `GET /{id}/audit-log` endpoint returns the complete chain of reasoning for any valuation. Pipeline steps record status (completed/failed/skipped), timing, and error messages. All steps also log to `logs.txt` for debugging. Tradeoff: storing full prompts/responses increases storage but makes every valuation fully reproducible and reviewable.

### Testing Strategy: Unit Tests + LLM Eval Suite

37 unit tests cover all pure valuation functions and the pipeline (with mocked LLM/market services). These run fast, are deterministic, and gate CI. A separate `eval_integration_test/` suite hits the live OpenAI API to validate that the research → enrichment pipeline can find and structure real financial data for well-known companies (SpaceX, Stripe, Databricks). These are prompt evals — they verify the LLM returns structurally correct data with order-of-magnitude accurate revenue, not exact numbers. Tradeoff: eval tests are slow (~30s each), cost API tokens, and are non-deterministic. They're skipped automatically when `OPENAI_API_KEY` is unset, keeping CI fast while enabling manual prompt regression testing.

## Setup & Usage

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY={API-KEY}         # if you have a specific API key
cp backend/.env.example backend/.env   # add your OPENAI_API_KEY
uvicorn backend.main:app --reload      # http://localhost:8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173

# Tests
source .venv/bin/activate
python -m pytest backend/tests/ -v     # 37 unit tests

# Eval tests (live OpenAI API — requires OPENAI_API_KEY)
python -m pytest eval_integration_test/ -v -s
```

Set `MOCK_MARKET_DATA=true` in your `.env` to skip real yfinance calls and use hardcoded data for development.

## Potential Improvements

- **Semantic caching for research** — The pipeline currently runs a fresh web search per valuation, even for the same company minutes apart. A TTL-based cache keyed on `(company_name, data_type)` would cut latency and token cost for repeated/reweighted valuations without serving stale data. Could use embeddings similarity for fuzzy cache hits (e.g., "Stripe" vs "Stripe Inc").
- **Multi-model routing** — All three LLM tasks (research, enrichment, narration) use the same model. Research requires tool use and reasoning; narration is mostly templated prose. Routing narration to a cheaper/faster model and reserving the expensive model for structured extraction would reduce cost per pipeline run with minimal quality loss.
- **Cross-methodology correlation in blending** — The blender treats comps, DCF, and last-round as independent signals, but they're correlated (both comps and DCF depend on sector multiples; last-round and comps both reflect market sentiment). A covariance-aware blend would produce tighter, more honest confidence intervals instead of the current fixed blend.
- **Prompt versioning and regression tracking** — The eval suite validates current prompt quality but doesn't track changes over time. Storing prompt hashes alongside eval results would enable A/B comparison across prompt iterations and catch regressions before they reach production.
- **LLM-as-judge validation layer** — The enrichment step uses deterministic guards to override bad LLM outputs, but these are binary (force-add/remove methods). A lightweight second LLM pass could score the *quality* of extracted financials (e.g., "is $8B revenue plausible for a Series C company?") and flag suspicious data before it enters the valuation engine.
- **RAG over financial documents** — Web search finds public information but misses detail from pitch decks, board memos, and internal financials that VC firms already have. An ingestion pipeline that chunks and embeds uploaded documents would let the research step retrieve firm-specific data, significantly improving accuracy for portfolio companies with limited public coverage.
- **Ensemble of LLMs** — Could use multiple LLMs (Gemini, Claude, OpenAI, etc) for the research stage of the pipeline and weight the final values for metrics like revenue based on LLM outputs weighted by their confidence scores
- **Improve uploaded DCF value extraction** - Very basic regex / exact value based matching to obtain the DCF values. Could use LLMs for value extraction or more robust value extraction
