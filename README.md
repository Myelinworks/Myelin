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

`DATABASE_URL` must be an `asyncpg`-style URL (`postgresql+asyncpg://...`)
pointing at your Supabase Postgres instance -- **use the connection pooler
URL** (Dashboard → Settings → Database → Connection Pooling), not the direct
`db.<ref>.supabase.co` host: that host is IPv6-only and unreachable from
networks without native IPv6. `REDIS_URL` points at an Upstash-compatible
Redis instance.

Tests run against the same Supabase project, but in a dedicated `test`
Postgres schema (via SQLAlchemy `schema_translate_map`), never `public` --
see `tests/conftest.py`. Each test runs inside a rolled-back transaction, so
the schema is always empty between tests.

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
Decision/EvidenceRecord objects, which makes them fully unit-testable without
a live database (`tests/services/`, 27 tests). Routes (`app/routes/`) wire
them to HTTP and own all persistence -- see "API surface" below.

### Known gaps (flagged in code, not guessed)

Most of the ~60 workspace decisions don't have evidence-extraction or
base-impact rules specified yet — `evidence_engine.EVIDENCE_EXTRACTORS` and
`decision_engine.compute_decision_impact` raise `NotImplementedError`/`KeyError`
for anything unregistered rather than inventing a rule. `quarter_engine.run_quarter`
collects these as `skipped_evidence`/`skipped_business_impact` (non-fatal, quarter
level); the single-decision submission route 422s on a missing **business-impact**
rule (the response contract promises a `business_impact` list) but treats a missing
**evidence** rule as non-fatal, logging the gap in `DecisionLog` instead -- the two
pipelines are independent and one being unimplemented for a given decision shouldn't
block the other. Concretely: only Marketing's channel/pricing/brand/team/expansion
decisions (the base-impact-table ones) can currently return 201 with real business
impact; every Finance/Product/Sales/CX decision 422s until `decision_engine` grows a
generic formula-application mechanism for those workspaces.

Other flagged gaps (see inline `TODO(source-doc-gap)` comments): how
`actual_impact_pct` converts into an absolute KPI delta; Finance FIN-008..013
per-dimension weights (inferred, need product-owner confirmation); the
marketing long-term-channel taxonomy and risk-level thresholds beyond the
given >70% cutoff; and the excess-leads-to-KPI-delta magnitude in the
Marketing→Sales handoff.

**Operations and People workspaces have no routes.** Both are named in the
Quarter Flow doc's workspace sequence but neither has a rules doc
(`operations_rules.json` / `people_rules.json` don't exist). Do not scaffold
a router for either until rules exist -- a router whose every decision_key
would 422 isn't a real endpoint, it's dead code dressed as a feature.

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

  schemas/                # pydantic request/response schemas, one file per workspace
    base.py                # ORMBase, QuarterScopedBase -- shared id/created_at/quarter_id
    decision.py             # DecisionSubmitBase (decision_key validated against rules JSON), DecisionLogEntry
    finance.py / marketing.py / product.py / sales.py / cx.py
    quarter.py              # QuarterReportResponse, LeaderboardResponse

  routes/
    deps.py                 # get_quarter, get_open_quarter (the lock guard), get_quarter_modifiers
    _factory.py              # build_workspace_router -- the shared 3-endpoint shape
    finance.py / marketing.py / product.py / sales.py / cx.py  # one-line factory calls
    quarter.py               # lock / report / leaderboard endpoints

  services/
    decision_engine.py          # Business Impact pipeline: modifier chain + marketing impact table
    evidence_engine.py          # Evidence pipeline: decision -> EvidenceRecord rows
    cognitive_scoring_engine.py # EvidenceRecords -> CognitiveScore + QuarterPerformance rollups
    quarter_engine.py           # Run Quarter orchestration: costs, handoffs, full pipeline wiring
    formulas/                   # concrete per-workspace arithmetic (finance/product/sales/cx)

  main.py                 # FastAPI app, CORS middleware, GET /health, router registration

alembic/                  # async-compatible Alembic migrations, applied to Supabase (14 tables)
tests/services/           # unit tests for all four engines (27 tests, no DB required)
tests/routes/             # route-level integration tests against the live Supabase `test` schema
```

## API surface

Per workspace (finance, marketing, product, sales, cx):

- `POST /companies/{company_id}/quarters/{quarter_id}/{workspace}/decisions` —
  validates `decision_key` against that workspace's rules JSON (422 with the
  invalid key named if unknown), persists a `Decision` row, runs
  `decision_engine` + `evidence_engine` for that one decision, writes two
  `DecisionLog` rows (`business_impact`, `evidence`), returns the immediate
  business-impact delta. Rejected with 409 if the quarter is already locked.
- `GET /companies/{company_id}/quarters/{quarter_id}/{workspace}/state` —
  current `*State` row; 404 if no snapshot exists yet.
- `GET /companies/{company_id}/quarters/{quarter_id}/{workspace}/decisions` —
  the workspace's decision log for that quarter (audit trail).

Quarter-level:

- `POST /companies/{company_id}/quarters/{quarter_id}/lock` — runs
  `quarter_engine.run_quarter` over every decision in the quarter, persists
  `EvidenceRecord`/`CognitiveScore`/`QuarterPerformance`, marks the quarter
  `CLOSED`. 409 if already locked.
- `GET /companies/{company_id}/quarters/{quarter_id}/report` — reads back the
  persisted `QuarterPerformance` row; never recomputes. 404 before lock.
- `GET /companies/{company_id}/leaderboard` — `QuarterPerformance` rollups
  for a company across quarters.

**`decision_key` is a real, indexed column on `Decision`** (not a
`payload["decision_key"]` convention) -- it's what `decision_engine` and
`evidence_engine` key their lookups on. `payload` carries the decision's
specific inputs. Two payload shapes are validated at the schema layer because
the source spec actually specifies them: `marketing_budget_allocation`'s
`channel_spend` must sum to `total_budget`, and `SAL-011` (negotiation)
payload keys must be a subset of `sales_rules.json`'s `negotiable_variables`.
Every other decision_key's payload is an unvalidated dict pending further
per-decision specification.

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
