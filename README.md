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

- **Business Impact pipeline** — reads a `Decision.payload`, computes effects on
  cash, revenue, and workspace KPIs, and writes the results into that
  workspace's quarterly state snapshot (`FinanceState`, `MarketingState`, etc.)
  and the aggregate `Quarter` row. Implemented in `app/services/decision_engine.py`
  and `app/services/quarter_engine.py` (not yet built).
- **Evidence pipeline** — reads behavioral signals around how the decision was
  made (time-to-decide, revisions, information requested before deciding, etc.),
  writes them as `EvidenceRecord` rows, and periodically rolls them up into
  `CognitiveScore` rows (Strategic Thinking, Adaptability, Leadership, ...) via
  the Cognitive Scoring Engine. Implemented in `app/services/evidence_engine.py`
  and `app/services/cognitive_scoring_engine.py` (not yet built).

Evidence and KPI data are kept in separate tables on purpose: the Cognitive
Scoring Engine must never read raw KPI/business-impact data, and the Business
Impact pipeline must never read evidence. `Decision` + `DecisionLog` sit between
both pipelines as the audit trail — every pipeline run against a decision writes
an immutable `DecisionLog` row (`stage`, `input_snapshot`, `output_snapshot`),
so any quarter can be replayed from its logs.

## Directory structure

```
app/
  core/                   # cross-cutting infrastructure, no business logic
    config.py             # pydantic-settings Settings (.env-backed)
    db.py                 # async SQLAlchemy engine, session factory, Base
    redis.py              # async Redis client (Upstash-compatible)

  models/                 # SQLAlchemy ORM models
    mixins.py             # UUIDPkMixin, TimestampMixin shared by all models
    company.py            # Company — root entity for one simulation run
    quarter.py            # Quarter — aggregate cash/revenue state snapshot
    decision.py           # Decision, DecisionLog — the audit/replay backbone
    evidence.py           # EvidenceRecord — behavioral signals (Evidence pipeline input)
    cognitive.py          # CognitiveScore — Cognitive Scoring Engine output
    finance.py            # FinanceState   — Finance workspace KPI snapshot
    marketing.py          # MarketingState — Marketing workspace KPI snapshot
    product.py            # ProductState   — Product workspace KPI snapshot
    sales.py              # SalesState     — Sales workspace KPI snapshot
    operations.py         # OperationsState — Operations workspace KPI snapshot
    cx.py                 # CXState        — Customer Experience workspace KPI snapshot

  schemas/                # pydantic request/response schemas, mirrored per domain (planned)
    finance.py / marketing.py / product.py / sales.py / operations.py / cx.py
    decision.py / quarter.py

  routes/                 # one thin router per workspace, no business logic (planned)
    finance.py / marketing.py / product.py / sales.py / operations.py / cx.py
    quarter.py            # quarter lifecycle / simulation control endpoints

  services/               # all business logic lives here, routes stay thin (planned)
    decision_engine.py         # Business Impact pipeline: decision -> KPI/cash deltas
    evidence_engine.py         # Evidence pipeline: decision -> EvidenceRecord rows
    cognitive_scoring_engine.py # EvidenceRecords -> CognitiveScore rollups
    quarter_engine.py          # quarter lifecycle: open, close, snapshot, advance

  main.py                 # FastAPI app, CORS middleware, GET /health

alembic/                  # async-compatible Alembic migrations, wired to app models
```

`schemas/`, `routes/`, and `services/` currently exist as empty packages —
they're intentionally left unimplemented until the actual pipeline rules
(what a decision does to cash/KPIs, what counts as a behavioral signal, how
cognitive dimensions are scored) are defined, rather than scaffolding routers
and services with no real logic behind them.

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

## Auth

Not yet implemented in this pass — out of scope for the current MVP slice per
project constraints. Planned approach: a custom FastAPI auth layer (not
Supabase Auth passthrough), to be added once the workspace endpoints exist.
