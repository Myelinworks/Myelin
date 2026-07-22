# Myelin Backend

Backend MVP for **Myelin** — a deterministic CEO decision-simulation platform for
business education. Students run a simulated company through quarters, making
decisions across six workspaces (Finance, Marketing, Product, Sales, Operations,
Customer Experience). Each decision is deterministic, auditable, and drives two
parallel pipelines: a **Business Impact** pipeline (cash/revenue/KPI effects) and
an **Evidence** pipeline (behavioral signals feeding a Cognitive Scoring Engine).

## Tooling

All commands go through `uv` — never `pip`/`poetry`/raw `venv`.

```bash
uv sync                          # install dependencies
uv run fastapi dev app/main.py   # run the dev server
uv add <package>                 # add a dependency
uv run pytest                    # run the test suite
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

Copy `.env.example` to `.env` and fill in real values before running anything
that touches the database or Redis:

```bash
cp .env.example .env
```

`DATABASE_URL` must be an `asyncpg`-style URL
(`postgresql+asyncpg://...`) pointing at your Supabase Postgres instance.
`REDIS_URL` points at an Upstash-compatible Redis instance.

## Architecture: the dual pipeline

Every decision a student submits runs through two independent pipelines that
never read from each other:

- **Business Impact pipeline** (`app/services/decision_engine.py`) — reads a
  `Decision.payload`, computes effects on cash, revenue, and workspace KPIs. For
  Marketing's base-impact-table decisions this is the generic modifier-chain
  pattern: `Actual Impact % = Base Impact % x Brand Strength x Market Saturation
  x Inventory Availability x Competitor Activity` (see `app/config/rules/`).
  Finance/Product/Sales/CX's concrete formulas live in `app/services/formulas/`.
- **Evidence pipeline** (`app/services/evidence_engine.py`) — turns a decision
  into structured behavioral evidence (boolean/enum/amount flags, e.g.
  `diversified_investment = YES`), never a score and never a raw KPI. Writes
  `EvidenceRecord` rows tagged with cognitive-dimension categories.
- **Cognitive Scoring Engine** (`app/services/cognitive_scoring_engine.py`) —
  reads only `EvidenceRecord` rows, aggregated purely by category tag (never
  by workspace), and computes 0-100 `CognitiveScore` rows from a Hidden Engine
  State baseline (50 for most dimensions, 60 Investor Confidence, 10 Employee
  Burnout) plus per-evidence-key weights.
- **`quarter_engine.py`** — orchestrates a full Run Quarter: Recurring Cost
  Engine (three cost categories from `finance_rules.json`), then Business
  Impact + Evidence per decision, then generic cross-department handoffs
  (`HANDOFFS` registry — e.g. Marketing Leads vs Sales Capacity), then rolls
  evidence up into `CognitiveScore` + `QuarterPerformance` (the leaderboard row).

We never score a decision directly — we score the evidence it produces. Evidence
and KPI data are kept in separate tables on purpose: the Cognitive Scoring Engine
must never read raw KPI/business-impact data, and the Business Impact pipeline
must never read evidence. `Decision` + `DecisionLog` sit between both pipelines
as the audit trail — every pipeline run against a decision writes an immutable
`DecisionLog` row (`stage`, `input_snapshot`, `output_snapshot`), so any quarter
can be replayed from its logs.

All four engines are pure, DB-session-agnostic functions over plain
Decision/EvidenceRecord objects (no route wiring yet — that's the next pass),
which makes them fully unit-testable without a live database. See `tests/services/`
— 27 tests cover the worked examples from the source docs (e.g. the marketing
modifier-chain example resolves to exactly 6.48%).

### Known gaps (flagged in code, not guessed)

Most of the ~60 workspace decisions don't have evidence-extraction or
base-impact rules specified yet — `evidence_engine.EVIDENCE_EXTRACTORS` and
`decision_engine.compute_decision_impact` raise `NotImplementedError`/`KeyError`
for anything unregistered rather than inventing a rule, and `quarter_engine.run_quarter`
collects these as `skipped_evidence`/`skipped_business_impact` instead of
failing the whole quarter. Other flagged gaps (see inline `TODO(source-doc-gap)`
comments): how `actual_impact_pct` converts into an absolute KPI delta;
Finance FIN-008..013 per-dimension weights (inferred, need product-owner
confirmation); the marketing long-term-channel taxonomy and risk-level
thresholds beyond the given >70% cutoff; and the excess-leads-to-KPI-delta
magnitude in the Marketing→Sales handoff.

## Directory structure

```
app/
  core/                   # cross-cutting infrastructure, no business logic
    config.py             # pydantic-settings Settings (.env-backed)
    db.py                 # async SQLAlchemy engine, session factory, Base
    redis.py              # async Redis client (Upstash-compatible)

  config/
    rules/                 # curriculum constants: base-impact tables, formulas, scoring weights
      __init__.py          # load_rules(workspace) -- cached JSON loader
      marketing_rules.json / product_rules.json / sales_rules.json
      cx_rules.json / finance_rules.json

  models/                 # SQLAlchemy ORM models
    mixins.py             # UUIDPkMixin, TimestampMixin shared by all models
    company.py            # Company — root entity for one simulation run
    quarter.py            # Quarter — aggregate cash/revenue state snapshot
    decision.py           # Decision, DecisionLog, Workspace enum — the audit/replay backbone
    evidence.py           # EvidenceRecord — behavioral signals (Evidence pipeline input)
    cognitive.py          # CognitiveScore — Cognitive Scoring Engine output
    modifier.py           # Modifier — quarter-level modifiers (brand strength, etc.)
    quarter_performance.py # QuarterPerformance — leaderboard rollup, written by quarter_engine
    finance.py             # FinanceState   — Finance workspace KPI snapshot
    marketing.py           # MarketingState — Marketing workspace KPI snapshot
    product.py             # ProductState   — Product workspace KPI snapshot
    sales.py               # SalesState     — Sales workspace KPI snapshot
    operations.py          # OperationsState — Operations workspace KPI snapshot
    cx.py                  # CXState        — Customer Experience workspace KPI snapshot

  schemas/                # pydantic request/response schemas, mirrored per domain (planned)
    finance.py / marketing.py / product.py / sales.py / operations.py / cx.py
    decision.py / quarter.py

  routes/                 # one thin router per workspace, no business logic (planned)
    finance.py / marketing.py / product.py / sales.py / operations.py / cx.py
    quarter.py            # quarter lifecycle / simulation control endpoints

  services/
    decision_engine.py          # Business Impact pipeline: modifier chain + marketing impact table
    evidence_engine.py          # Evidence pipeline: decision -> EvidenceRecord rows
    cognitive_scoring_engine.py # EvidenceRecords -> CognitiveScore + QuarterPerformance rollups
    quarter_engine.py           # Run Quarter orchestration: costs, handoffs, full pipeline wiring
    formulas/                   # concrete per-workspace arithmetic (finance/product/sales/cx)

  main.py                 # FastAPI app, CORS middleware, GET /health

alembic/                  # async-compatible Alembic migrations, wired to app models
tests/services/           # unit tests for all four engines (27 tests, no DB required)
```

`schemas/` and `routes/` currently exist as empty packages — they're
intentionally left unimplemented until routes are wired up (the next pass),
rather than scaffolding routers with no real logic behind them.

## Data model notes

- **Quarterly state snapshots**: `Quarter` holds the aggregate cash/revenue
  position; each workspace has its own `*State` table (one row per quarter,
  unique on `quarter_id`) holding that workspace's KPIs. This keeps fast
  dashboard queries simple (`SELECT ... WHERE quarter_id = ...`) instead of
  requiring recomputation from decision history.
- **Auditability**: `Decision` stores what was submitted; `DecisionLog` stores
  one immutable row per pipeline run against that decision (`stage` +
  `input_snapshot` + `output_snapshot`), enabling full replay of how a
  quarter's state was derived.
- **Evidence is separate from KPIs**: `EvidenceRecord` and `CognitiveScore`
  are distinct tables from the `*State` KPI snapshots — evidence feeds
  cognitive scoring, never the other way around.
- **Modifiers are rows, not columns**: `Modifier` (company_id, quarter_id,
  modifier_key, value) holds Brand Strength/Market Saturation/Inventory
  Availability/Competitor Activity per quarter. New modifier types can be
  introduced without a schema migration.
- **Leaderboard rollup**: `QuarterPerformance` (one row per quarter) is written
  by `quarter_engine` after cognitive scoring, so leaderboard reads don't need
  to aggregate `cognitive_scores` on every request.

## Auth

Not yet implemented in this pass — out of scope for the current MVP slice per
project constraints. Planned approach: a custom FastAPI auth layer (not
Supabase Auth passthrough), to be added once the workspace endpoints exist.
