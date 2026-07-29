# CLAUDE.md

## Project

Myelin — deterministic CEO decision-simulation engine. FastAPI + async SQLAlchemy + asyncpg on Supabase, Alembic, Redis, `uv`.

## Specification of record

`backend/docs/` is authoritative. Read before implementing anything:

- `00-formula-index.md` — every formula, grouped by engine, with status flags
- `12-quarter-1-reference.md` — the worked Q1 example all formulas validate against
- `10-implementation-gaps.md` — what must not be guessed
- `10-scoring-methodology.md` — scoring rubric
- `11-crisis-system.md` — crisis constants

If a coefficient is not in `docs/`, it does not exist. Raise `NotImplementedError` with the specific reason.

## Engineering discipline

- Every change is a deliberate value addition with a one-sentence justification.
- No cosmetic edits. No padding commits.
- No guessed formulas presented as authoritative.
- Visible gaps preferred over silently wrong numbers.
- Commit messages must accurately describe their diff. `docs:` only if the diff is docs-only.

## Architecture rules

**Company-agnostic.** No company number and no market-calibration constant appears in engine code.
- `config/profiles/*.json` — curve shapes, coefficients, exponents, baselines, floors
- `config/seeds/*.json` — opening company state

Adding a company must require zero code changes.

**Units.** `x` = spend in ₹ lakhs. ₹4,00,000 → `x = 4.00`. Convert once at the config/input boundary, never inside a formula.

**Money.** `Decimal` everywhere. Round at persistence and display only, never mid-chain.

**No within-quarter compounding.** All allocations evaluate against the opening snapshot. Submitting a spend line never mutates `*State`. Only `run_quarter()` writes closing state. This is the design, not a bug — do not add write-back to `routes/_factory.py`.

**Determinism.** No RNG. Do not implement the variance model proposed in `09-calibration-engine.md` — it is an unresolved design question logged in `10-implementation-gaps.md`.

**Two pipelines stay independent.** Business Impact and Evidence are separate. Cognitive scoring reads only `EvidenceRecord`, aggregated by cognitive-dimension category, never by workspace.

## The model

22 department spend lines, not the ~72-key decision taxonomy. Marketing 8 · Sales 3 · R&D 2 (+warranty choice) · Operations 3 · HR 3 · Finance/Admin 3.

The legacy percentage-influence matrix lives in `app/engines/legacy_matrix/`, is not wired into `run_quarter()`, and keeps its `6.48%` validation test.

## Commands

```
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
uv run pytest
```

`DATABASE_URL` must be the Supabase connection-pooler URL (port 6543), not `db.<ref>.supabase.co` — that host is IPv6-only. Prepared-statement cache is disabled in `core/db.py` because PgBouncer transaction pooling breaks it.