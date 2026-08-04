# Work Split — Finishing the Backend

> Two developers. This document defines who owns what, in what order, and what neither of us is
> allowed to do alone.
> Read `docs/18-backend-kt.md` first — this assumes you know the architecture.

---

## 1. How we're splitting it

**The rule: I own the execution chain. You own everything that reads a finished result.**

`app/engines/quarter.py` is the one file where two people cannot work at the same time. The order
of operations in it is load-bearing, and two documented audit errors already happened there. The
crisis engine injects penalties at three separate points *inside* that chain, so crisis work and
chain work are the same work — that stays with me.

Everything else that's left — scoring, the Q4 endgame, the API surface, deployment — takes a
finished `QuarterResult` as input and never modifies the chain. That's a clean boundary, and it's
yours.

This isn't about difficulty. It's about not stepping on each other.

### File ownership

| Files | Owner |
|---|---|
| `app/engines/quarter.py`, `app/engines/state.py`, `app/engines/lines/**` | **Me** |
| `app/engines/crisis.py` (new) | **Me** |
| `app/engines/scoring.py`, `app/engines/endgame.py` (both new) | **You** |
| `app/routes/**`, `app/schemas/**` | **You** |
| `app/models/**`, `alembic/versions/**` | **You** (tell me before a migration lands) |
| `app/config/schema.py` | **Shared** — different sections, coordinate before editing |
| `app/config/profiles/default.json` | **Shared** — I add `crisis`, you add `scoring`. Different top-level keys, so merges are clean |
| `app/services/quarter_run_service.py` | **You**, but ping me — it's the seam between our halves |
| `docs/**` | Either. Don't edit `docs/00` – `docs/17`; those are the client's spec, not ours |

---

## 2. Ground rules — these are not negotiable

These aren't style preferences. The entire value of this codebase to the client is that it's
auditable. Breaking these makes the work worthless even if the numbers look right.

1. **Never invent a coefficient.** If a number isn't in `docs/`, it does not exist. Raise
   `NotImplementedError` with the specific reason for why it can't be computed. A visible gap
   beats a silently wrong number, every time. If you find yourself thinking "this is probably
   around 0.15" — stop, and put it in the questions list instead.

2. **`app/engines/` stays pure.** No database, no clock, no randomness, no filesystem, no network.
   Pure functions in, dataclasses out. This is what makes the whole thing testable and provably
   deterministic. If your engine code needs data, the *caller* loads it and passes it in.

3. **`Decimal` everywhere, never `float`.** Round only at persistence and display. A float will
   silently break the Q1 regression tests.

4. **Numbers you're unsure about go in config with a `status` flag, not in code.** Look at how
   `BrandMultiplierConfig` carries `formula`, `status: "fitted_not_confirmed"` and `note`. Anyone
   reading the JSON can see which numbers are sourced and which are inferred. Copy that pattern.

5. **Don't touch the 308 existing tests to make your code pass.** If one breaks, your change is
   wrong until proven otherwise. Come talk to me.

6. **Commit messages must accurately describe the diff.** `docs:` only if the diff is docs-only.
   No padding commits, no cosmetic edits.

### Read this before you read the spec docs

**`docs/11-crisis-system.md` and `docs/16-quarter-4-endgame.md` contain stale "blocked" markers.**

Both were written before the designer answered our questions. `docs/17-designer-resolutions.md`
is newer and supersedes them:

- `docs/16` lines 159–164 list six Q4 items as *"blocked — not specified"*. **All six now have
  answers** in `docs/17` — tier assignment, term-sheet menus, the covenant formula, continuation
  value and the Exit & Growth sub-criteria are fully resolved, and Momentum Score is resolved *for
  a narrower 2-input formula* than `docs/16` describes (the 7-input weighted composite is still
  unspecified and stays unbuilt). Don't stop when you hit that checklist.
- `docs/11` line 320 flags the Choice D offset as an open gap. **`docs/17` resolved it** —
  Choice A carries +0.50.

**When two docs disagree, `docs/17` wins.** When `docs/17` says something is still open, it is
genuinely open and you must not fill it in.

---

## 3. Your tasks, in order

### T1 · Scoring config — transcribe the rubric into JSON  *(~2 days)*

**This is your onboarding task. Do it first, and stop for review before writing any Python.**

I've already written the Pydantic schema for this — `ScoringConfig`, `ScoringCriterion`,
`ScoringModifier`, `ScoringBand`, `ScoringThresholds` in `app/config/schema.py`. It's currently
orphaned: `SimulationProfile` doesn't reference it and `default.json` has no `scoring` block.
Your job is to fill it in.

**What to do:**
1. Add `scoring: ScoringConfig` to `SimulationProfile` in `app/config/schema.py`.
2. Add a `scoring` block to `app/config/profiles/default.json` from
   `docs/10-scoring-methodology.md`:
   - 7 traits and their weights (must sum to exactly 100 — assert this in a test)
   - all 21 sub-criteria, each with a stable `id`, its `trait`, and a `kind`
   - the 8 standard modifiers under `modifier_sets.standard`
   - the 5 score bands
   - the thresholds

**The hard part, and the reason this needs review before you code:** each of the 21 sub-criteria
must be classified `MECHANICAL` or `JUDGMENT`.

- **MECHANICAL** = decidable from the quarter's numbers alone. Example: Systems Thinking #3 ("no
  single department left as an unaddressed bottleneck") — `QuarterResult` already reports
  `capacity_bound`, `ceiling_bound` and `supply_bound`, so that's checkable.
- **JUDGMENT** = the criterion asks about something no input carries. Example: Strategic Thinking
  #1 ("a **stated**, coherent thesis exists") — we have the spend numbers, not the student's
  stated reasoning. Leadership's three criteria are all like this ("without excessive hedging",
  "proactive", "owns the trade-offs"). Risk Management #3 explicitly says "at the time of the
  decision", which we can't reconstruct.

A `JUDGMENT` criterion gets a `reason` string saying exactly what's missing, and at scoring time
it is returned **UNSCORED and held out of the denominator**. It is never inferred from spend. A
plausible-looking proxy for "did they own the trade-off" is exactly the invented number we refuse
to ship.

My rough read is that most of Leadership, Adaptability and Strategic Thinking are JUDGMENT, and
most of Capital Allocation, Systems Thinking and Long-Term Thinking are MECHANICAL — but make
your own call, write the `reason` for each, and we'll go through all 21 together.

**Also flag, don't solve:** the "Debt taken without justification (−2)" modifier has no trigger in
our live engine — there's no debt mechanic in the 22-line chain at all (FIN-005 lives in the
parked legacy pipeline). Give it a `status` flag saying it can never fire today.

**Done when:** the profile loads, `traits` sums to 100, every criterion has an `id`/`kind`, every
`JUDGMENT` has a `reason`, every unsourced threshold has a `status`, and I've signed off on the
classification.

---

### T2 · `engines/scoring.py` — the CEO score  *(~1 week)*

Pure module, same discipline as `engines/survival.py` — which is your reference implementation for
this whole task. Read it first; the pattern is deliberate.

```
score_quarter(result: QuarterResult,
              prior: QuarterResult | None,
              config: ScoringConfig,
              modifier_sets: list[str]) -> ScoreResult
```

**The pattern to copy from `survival.py`:**
- Config declares *which* checks are active. The predicate is code, keyed by `id`.
- A configured `id` with no registered predicate is a **hard error**, not a silent skip. A check
  that quietly does nothing is worse than one that's absent.
- Rule strings in JSON are documentation. They are never evaluated.
- Never return a bare number — return *what fired and why*, the way `SurvivalOutcome` carries
  `triggered_by` and `detail`. "You scored 71" is useless without "because capacity waste cost you
  2 points".

**`ScoreResult` should carry:** per-trait points, the list of criteria that were UNSCORED (with
reasons), every modifier that fired with its points and the numbers that triggered it, the final
total, and the band.

**Start with the modifiers, not the traits.** All 8 standard modifiers are cleanly checkable from
a `QuarterResult`, so you'll get working code and real tests fast:

| Modifier | Where the answer already is |
|---|---|
| Profitability achieved (+3) | `net_cash_flow_inr > 0` |
| Perfect channel match (+2) | `referral_wasted_spend_inr == 0` **and** the cap was actually hit — that's why `referral_lead_cap` is on `QuarterResult`. Zero waste alone only proves it wasn't *over*-funded |
| Zero capacity waste (+2) | `leads_used` vs `effective_leads` |
| Zero supply waste (+2) | `available_to_sell − units_sold`, against the configured threshold |
| Compounding asset cut (−2) | needs `prior` — compare brand/SEO/buzz/innovation spend |
| Ceiling under-shot (−2) | `raw_conversion_pct` vs `conversion_ceiling_pct` (this one's threshold *is* sourced: ~3 points) |
| Cash buffer breached (−3) | `spent_into_buffer` |
| Debt without justification (−2) | no trigger exists — see T1 |

Then do the MECHANICAL traits. `JUDGMENT` traits return UNSCORED — that's the finished behaviour,
not a stub.

**Scoring math:** clearly met = 1/3 of trait weight, partially met = 1/6, not met = 0. Traits sum
to 100; modifiers are additive and uncapped in both directions, so the final score is *not* capped
at 100 by formula.

**Done when:** `uv run pytest` passes, the canonical Q1 run produces a score you can explain line
by line, and every UNSCORED criterion states why.

---

### T3 · Persist the score  *(~2 days)*

Where the CEO score gets stored is a real design decision — get it signed off before writing the
migration.

**Do not reuse `quarter_performances.overall_score` / `dimension_scores`.** Those belong to the
legacy cognitive pipeline (`services/cognitive_scoring_engine.py`) and mean something different.
Two different scoring systems sharing one column is exactly the ambiguity this codebase avoids.

**My recommendation:** new nullable columns on `quarter_performances` — `ceo_score`,
`score_band`, `trait_points` (JSONB), `modifiers_applied` (JSONB), `unscored_criteria` (JSONB).
That matches how `result_hash`/`engine_result` were added alongside the legacy columns, and the
model's docstring already explains why both live on one row.

Wire it into `services/quarter_run_service.py::run_quarter()`, inside the **existing transaction**
— the result, the survival status and the score all commit together or not at all. Note that
`result_hash` currently hashes the result plus the run status; decide with me whether the score
joins the hash (I think not — the score is derived from the result, so hashing it adds nothing).

**Done when:** locking a quarter persists a score, locking twice is still idempotent, and the
migration runs clean on a fresh DB.

---

### T4 · Q4 endgame  *(~1 week)*

New pure module `app/engines/endgame.py`. Everything below is **specified** in
`docs/17-designer-resolutions.md` — ignore `docs/16`'s stale "blocked" checklist.

```
Momentum Score           = (Q3 Units Sold / Q1 Units Sold)^(1/2) − 1
Path A covenant          = Prior Units × (1 + 1.3 × Momentum Score)
Path B continuation value = Current Valuation × (1 + Momentum Score)
```

**Tier assignment** (`docs/17`, and note the naming — the designer says
Thriving/Stable/Distressed, not the Strong/Flat/Weak in `docs/16`):

- `Q3 NCF > 0` **and** valuation grew in both Q2 and Q3 → **Thriving**
- buffer breached at any point **or** Q3 NCF < 0 with cash declining 2+ consecutive quarters →
  **Distressed**
- everything else → **Stable**

The Distressed half of that is **already implemented** in `engines/survival.py` — `buffer_breached`
and `sustained_decline` are exactly those two conditions, and `tier_assignment_quarter()` already
computes which quarter to evaluate at. Reuse it. Don't reimplement it.

**Term-sheet menus** — three per tier, named in `docs/17` line 63. These go in **config**, not
code, same as everything else.

**Then:** an `EndgameDecision` model + migration, and routes to fetch the offered menu and record
the chosen path. Register the 6 Q4 modifiers as `modifier_sets.q4` — the config schema was built
for exactly this, so it should need no schema change.

**The trap to avoid:** the Exit & Growth Judgment trait's three sub-criteria are *all* JUDGMENT —
they're about the student's **stated reasoning** ("references the actual Q1–Q3 trend", "owns the
consequences rather than attributing them to luck"). Same for the Path B modifiers, which turn on
"rejected **with correct reasoning**". These come back UNSCORED. Do not infer them from numbers.

**Done when:** momentum and tier are computed from real history, the right menu is returned per
tier, a path can be recorded, and the Q4 modifiers fire correctly.

---

### T5 · API surface for the frontend  *(~3 days)*

`GET /quarters/{id}/report` currently returns **5 numbers** — units sold, revenue, NCF, closing
cash, hash. The stored `engine_result` has ~60 fields and the frontend is chart-heavy
(`docs/01-technical-architecture.md`: "fast dashboard rendering across many chart-heavy
workspaces"). Right now the frontend can't build a single chart of the funnel.

Expose the full chain as typed responses: per-channel lead breakdown, all three gates with their
`*_bound` flags, the P&L waterfall, the valuation split, and the score breakdown from T2.

**Read from the persisted `engine_result`. Never recompute.** The lock is the only place anything
is computed; every read route is a read-through. Keep it that way.

Agree the response shapes with whoever's building the frontend before you write them.

---

### T6 · Hardening and deploy  *(~3 days)*

- **Fix the lock race.** `run_quarter()` does `session.get(Quarter)` → checks status → computes →
  writes. Two concurrent `POST /lock` calls can both pass the CLOSED check. The unique constraints
  on `quarter_id` mean one commit fails rather than duplicating — so it's a 500, not corruption,
  but it's still wrong. Fix with `SELECT … FOR UPDATE` on the quarter row.
- **Structured logging + a request id.** There is none today.
- **Deploy to Railway** per `docs/01`. Remember `DATABASE_URL` must be the Supabase pooler URL
  (port 6543) — `db.<ref>.supabase.co` is IPv6-only and will not connect.
- **Redis is configured but completely unused** (`app/core/redis.py` exists, `get_redis` is never
  called). Don't wire it in for its own sake. Only add caching if a read endpoint is measurably
  slow — and if you do, it caches read-throughs only, never anything on the lock path.

---

## 4. What I'm doing in parallel

So you know what's moving under you:

- **Crisis engine (Phase 10)** — 4 scenarios, the response budget lines, Choice A–D, the capacity
  multiplier. Fully specified in `docs/11` + `docs/17`.
- Extending `QuarterAllocations` and `QuarterResult` with the crisis fields.
- Registering `modifier_sets.crisis` into your scoring config once T1 lands.
- The Q3 regression test against `docs/14` and `docs/15`.

**What this means for you:** `QuarterResult` will gain fields. It won't lose any, and nothing
existing will change meaning. Your scoring predicates read fields by name, so additive changes are
safe. I'll tell you when the crisis fields land so you can wire `modifier_sets.crisis`.

---

## 5. Sequencing

```
T1 (config)  ──►  T2 (scoring)  ──►  T3 (persist)  ──►  T5 (API)
                                          │
T4 (endgame) ─────────────────────────────┘
T6 (hardening) — anytime, independent
```

- **T1 gates T2.** Don't write predicates against a classification I haven't reviewed.
- **T4 can start any time** — it only needs `survival.py` and quarter history, both of which are done.
- **T5 needs T2/T3** for the score fields, but the engine-result half can start immediately.
- **T6 is independent** — good filler when you're blocked on a review.

---

## 6. Things you must not change without asking me

| Thing | Why |
|---|---|
| `QuarterResult` / `CompanyState` field **names or meanings** | Adding is fine. Renaming or repurposing breaks `_from_jsonable`, which reads persisted JSON by field name — every quarter already locked in the DB would fail to deserialise |
| The `_to_jsonable` / `_from_jsonable` round-trip | It's generic on purpose. Special-casing a field there is how it goes stale |
| Anything under `app/engines/lines/` | Mine, and every number in there is validated against the Q1 reference |
| `routes/_factory.py::_state_to_dict` | Read-only by design. **Never add a write-back.** No within-quarter compounding — if submitting spend mutated state, the order a student clicked "submit" would change their results |
| The 4 existing Alembic migrations | Add new ones; never edit a landed one |

---

## 7. Not in scope for either of us

Blocked on the client or the designer — **do not fill these in**, even if the pattern seems obvious:

| Item | Blocked on |
|---|---|
| CX workspace (CX-001…012) | No formulas exist for any of the 9 named "engines". `docs/17` explicitly recommends keeping the `NotImplementedError` |
| Negotiation engine (SAL-011) | Mathematically cannot produce a 0–1 probability as written |
| FIN-004/009/010/011/012/013, PRO-008/009/010 | No coefficients stated anywhere |
| PulseWear as a runnable company | 9 required constants never stated. Would 500 on first lock |
| Calibration table conflicts (3 tables) | Designer must pick one of each pair |
| Operations / People decision catalogs | The formulas exist; the decision-spec *documents* don't. `docs/17` line 159 — the designer offered to write them |
| Most cognitive evidence weights | Only 4 are confirmed. The rest contribute 0 until the product owner supplies them |
| Auth / user accounts | **There is none today.** Genuinely absent, and I don't think it's in the ₹50k pilot scope — needs a scope decision from the client before either of us builds it |

`docs/10-implementation-gaps.md` is the full register with P0–P3 priorities. If you hit something
that isn't in it, that's a finding — add it, don't work around it.

---

## 8. If you're stuck

- **A number you need isn't in `docs/`** → don't guess, add it to the questions list, raise
  `NotImplementedError` with the specific reason, keep moving.
- **Two docs disagree** → `docs/17` wins. If `docs/17` is silent, ask.
- **An existing test fails** → your change is wrong until proven otherwise. Come find me.
- **Not sure whether something is MECHANICAL or JUDGMENT** → default to JUDGMENT and flag it.
  UNSCORED is honest; an invented proxy is not.
