# Backend KT — Myelin

> Handover session notes. Read top to bottom once; after that use it as a lookup.
> Every claim here was checked against the code on 2026-08-03. Test suite: **308 passing**.

---

## 1. What this backend actually does

A student plays CEO of a company for 4 quarters. Each quarter they decide **how much money to put
into 22 spending lines** (Google Ads, Sales Reps, Manufacturing, Training, …). They hit "Lock".
The backend computes what happened — how many leads came in, how many units sold, what the cash
balance is now — and carries that forward into the next quarter.

Two things matter about how we do it:

1. **It is deterministic.** No randomness anywhere. Same inputs → byte-identical output, every
   time, on any machine. This is a teaching tool: a student must be able to ask "why did I get
   this number?" and get one answer.
2. **We never invent a number.** The client gave us specification documents (`docs/00` to
   `docs/17`). If a formula or coefficient is in those docs, we implement it. If it isn't, we
   raise an error that says exactly what's missing. We do not guess and we do not approximate.
   A visible gap is better than a silently wrong number.

Rule of thumb for the team: **if a coefficient is not in `docs/`, it does not exist.**

---

## 2. Folder structure and why it's shaped this way

```
app/
├── config/          The numbers. JSON files + their validation schema.
│   ├── profiles/    Curve shapes — how a rupee converts into leads. NO company numbers.
│   ├── seeds/       One company's opening state. NO curve shapes.
│   ├── scenarios/   Which seed + which profile + how many quarters.
│   ├── rules/       Legacy per-decision rule tables (older model, see §9).
│   ├── schema.py    Pydantic classes that validate all of the above.
│   └── loader.py    Cached readers for the JSON.
│
├── engines/         The maths. Pure Python. No database, no clock, no randomness.
│   ├── lines/       One file per department — the 22 spend lines.
│   ├── state.py     What goes IN (opening state + allocations).
│   ├── quarter.py   The main chain — this is the heart of the system.
│   ├── survival.py  Is the run alive / distressed / dead?
│   ├── gaps.py      Formulas the docs mention but don't specify. They raise on purpose.
│   └── legacy_matrix/  The older percentage-based model, kept but not wired in.
│
├── models/          SQLAlchemy tables. One file per table.
├── schemas/         Pydantic request/response shapes for the API.
├── routes/          FastAPI endpoints. Thin — they load, call, save, return.
├── services/        The glue between routes/DB and the pure engines.
└── core/            DB connection, Redis, settings.
```

### The one rule that explains the whole layout

**`engines/` must never import a database.** It is pure functions in, pure data out.

Why we care:

- We can test the entire simulation with zero database. That's why the suite runs in 34 seconds.
- We can prove determinism, because a pure function has nothing else to depend on.
- If a number is wrong, it's wrong in exactly one place, and that place has no I/O in it.

`services/` is the only layer allowed to touch both the database and the engines. Routes talk to
services. Services talk to engines. Engines talk to nobody.

### The second rule: company-agnostic

No company's number appears in engine code. Ever.

- `config/profiles/default.json` — "Google Ads gives `375 × x^0.68` leads". That's a curve shape.
  It's true for any company in this simulation.
- `config/seeds/nadi_wear.json` — "opening cash ₹1.5 Cr, selling price ₹9,999, 4,000 customers".
  That's company data.
- `config/scenarios/nadi_wear_standard.json` — "run the `nadi_wear` seed on the `default` profile
  for 4 quarters, crisis in Q3".

**Adding a second company should be one new JSON file and zero code changes.** Same for adding a
scenario. If someone ever has to edit Python to onboard a company, we broke the design.

---

## 3. The units convention (this trips everyone up)

Inside a formula, `x` = **spend on that line in ₹ lakhs**.

₹4,00,000 → `x = 4.00`.

Any field ending in `_inr` is rupees. Conversion happens once, at the config/input boundary —
never inside a formula. There is exactly one documented exception: the Referral line, because its
cost-per-lead (₹300) is naturally rupee-denominated.

And: **`Decimal` everywhere, never `float`.** We round only when saving or displaying. If you use
a float, `0.02 × 8.7` stops being exactly `1.174` and the Q1 regression tests fail. That's also
why `loader.py` parses JSON with `parse_float=Decimal`.

---

## 4. The 22 lines

| Department | Lines |
|---|---|
| Marketing (8) | google_ads, meta_ads, social_influencer, content_seo, events_pr, email_marketing, referral, prelaunch_buzz |
| Sales (3) | reps, crm_tools, onboarding |
| R&D (2 + choice) | quality_qa, innovation, **warranty_years** (0/1/2 — a choice, not a spend) |
| Operations (3) | manufacturing, supplier_qc, logistics |
| HR (3) | culture_benefits, training_development, cx_team |
| Finance/Admin (3) | compliance_legal, financial_planning, audit_prep |

Almost every line has the same shape: **`output = constant × x^exponent`**, where the exponent is
below 1. That's diminishing returns — your first lakh reaches the cheapest, most responsive
audience; the tenth lakh reaches a much less responsive one.

Two deliberate exceptions:

- **Sales Reps capacity is linear** (`500 × x`). Hiring twice as many reps really does roughly
  double the phone-answering bandwidth.
- **Referral has no curve at all.** It's a hard cap: `0.20 × your existing customers`, at a flat
  ₹300/lead. You can't refer more people than your customers can refer. Money spent past the cap
  is returned as `wasted_spend_inr` rather than silently absorbed — the student should be able to
  see they overspent.

---

## 5. `engines/lines/` — one file per department

Every function here is pure: spend in lakhs, whatever prior-quarter state it needs, and the
profile. Nothing else.

### `_shared.py` — the arithmetic everything reuses

| Function | What it does |
|---|---|
| `diminishing(c, x, e)` | `c × x^e`. The shape of nearly every line. Rejects negative spend. |
| `linear(c, x)` | `c × x`. Only Sales Reps capacity uses this. |
| `require(value, field, company)` | The gap guard. Seed values are `None` when `docs/` never states them for that company. This raises `NotImplementedError` naming the exact missing field instead of borrowing another company's constant. |

`require()` is the discipline rule made executable. It's why PulseWear (the second seed) can exist
in config but can't run a quarter — nine constants it needs are never stated in the docs, and
we'd rather fail loudly than substitute Nadi Wear's numbers.

### `marketing.py` — 8 lines, plus 2 deferred payouts and the brand multiplier

| Function | Formula / role |
|---|---|
| `google_ads` | `375 × x^0.68` leads. Highest exponent of any paid channel — search intent renews daily rather than exhausting a pool. |
| `meta_ads` | `200 × x^0.65` leads · `40,000 × x` impressions · Brand `+1.2 × x` |
| `social_influencer` | `225 × x^0.72` leads · Brand `+2.5 × x`. Best exponent **and** best brand rate — third-party endorsement carries more trust per rupee. |
| `content_seo` | `75 × x^0.62` leads (deliberately the weakest today) · SEO Asset `+3.5 × x` |
| `seo_asset_payout` | **Next quarter**, that asset pays `× 25` free leads. Reads prior-quarter state, never this quarter's spend. |
| `events_pr` | `90 × x^0.62` leads · Brand `+1.5 × x` |
| `email_marketing` | `80 × x^0.55` leads · Repeat Purchase Rate `+3 × x^0.5` pts. The only marketing channel that feeds retention. |
| `referral` | Hard cap, described above. Returns leads, cap, cost and wasted spend. |
| `prelaunch_buzz` | Buzz Score `4 × x^0.5` and **zero leads this quarter**. That's the mechanic, not a bug. |
| `buzz_payout` | Q+1: `Buzz × 15` leads. Q+2: `Buzz × 25` leads plus a one-time `Buzz × 0.3` pt conversion bonus. Any other offset pays nothing. |
| `brand_multiplier` | `1 + 0.02 × Brand Score`, applied **from Q2 onward**. Brand built this quarter pays next quarter. |

Note on `brand_multiplier`: the docs give three data points, not a function. We fitted a straight
line through them and flagged it `fitted_not_confirmed` in the profile JSON. It reproduces the
docs' numbers exactly, but the designer never confirmed the formula. That flag is the honest
label, and it must survive into any handover conversation with the client.

### `sales.py`

| Function | Formula / role |
|---|---|
| `reps` | Capacity `500 × x` (linear) · Conversion bonus `2 × x^0.5` pts. **The only line that buys hard capacity.** |
| `crm_tools` | Conversion bonus `1.5 × x^0.4` pts. Lower exponent than reps — software hits its ceiling faster than human skill does. |
| `onboarding` | Satisfaction `+3 × x^0.5` · Repeat Rate `+3 × x^0.4` pts. Entire payoff is next quarter — the customer already bought. |
| `effective_capacity` | `capacity × (1 − prior attrition)`. Attrition erodes capacity built in a *previous* quarter, so it's zero in Q1. |

The Reps-vs-CRM split is a real trade-off precisely because only Reps buys bandwidth.

### `rnd.py` — where the game gets interesting

| Function | Formula / role |
|---|---|
| `quality_qa` | Quality Score `+6 × x^0.5` (cumulative, never resets — it's accumulated engineering knowledge) · Defect Rate `max(2%, 8% − 1.2 × x^0.5)`. The 2% floor exists because even world-class manufacturing fails sometimes. |
| `innovation` | Feature Completeness `+8 × x^0.5`, **resets to 0 at 100** (the feature ships, next round starts fresh) · Innovation Score `+5 × x^0.5`, never decays. |
| `conversion_ceiling` | `15% + (Quality + 0.5 × Innovation) × 0.3%` |
| `warranty_conversion_bonus` | 1yr `+1.5` pts, 2yr `+3.0` pts |
| `warranty_cost` | `Units Sold × Defect Rate × ₹1,500`, `× 1.8` for a 2-year term |

**The Conversion Ceiling is the single most important mechanic in the model.** It is what stops
Marketing from winning the game alone. No amount of ad spend or sales training can convert leads
above the rate your product's build quality allows. If a student pours everything into Marketing
and nothing into R&D, they generate huge lead volume and convert almost none of it.

The warranty bonus is added **after** the ceiling and is not capped by it. The ceiling is a
build-quality limit; a warranty is a trust signal — a different kind of persuasion, so it layers
on top. Getting this wrong was one of the two audit errors in the source docs, and there's a
regression test guarding it.

Warranty is also the cleanest strategic decision in the game: offering it costs nothing up front,
and the cost materialises later, in proportion to how many units actually fail. Cheap if your
quality is good, expensive if it isn't.

### `operations.py`

| Function | Formula / role |
|---|---|
| `manufacturing` | Production Capacity `400 × x^0.7` · Unit Cost `max(floor, base − 90 × x^0.5)`. One spend, two outputs — investing in production lines both builds capacity and lowers cost. |
| `supplier_qc` | Supplier Reliability `+4 × x^0.5`. A *risk multiplier*, not an output — it doesn't build anything, it protects what you already built from shortages and late shipments. |
| `logistics` | Efficiency `+5 × x^0.5` · Satisfaction `+0.05 × Efficiency`. Satisfaction is driven by the resulting efficiency level, not by spend directly — delivery speed is what the customer actually experiences. |
| `available_to_sell` | `(Capacity × (1 − Attrition) × Reliability/100) + carried inventory` |

`available_to_sell` is the most literal constraint in the model. However many leads you have and
however good your conversion rate, **you cannot sell units you haven't built.**

### `hr.py`

| Function | Formula / role |
|---|---|
| `culture_benefits` | Satisfaction `+5 × x^0.5` · Productivity Multiplier `1 + (Satisfaction − 50) × 0.004`. Centred on 50 — a neutral, adequate baseline. Below 50 it actively hurts. |
| `training_development` | Engagement `+6 × x^0.5` · Attrition `max(3%, 15% − 0.12 × Engagement)`. The 3% floor is unavoidable turnover. |
| `cx_team` | Satisfaction `+4 × x^0.5` · Repeat Rate `+2 × x^0.4` pts |
| `total_employees` | `core team + Σ(department spend / cost per hire)`. A derived read-out, not a decision — hiring is decentralised, each department funds its own headcount. |

Satisfaction and Engagement deliberately drive *different* mechanics rather than both being
generic morale. Satisfaction feeds the company-wide productivity multiplier **now**; Engagement
feeds attrition, which protects capacity **later**.

### `finance_admin.py`

| Function | Formula / role |
|---|---|
| `compliance_legal` | Compliance Score `+5 × x^0.5` |
| `financial_planning` | Forecast Accuracy `+6 × x^0.5` · Cash Efficiency Bonus `(Accuracy − 50) × 0.1%` |
| `audit_prep` | Audit Readiness `+5 × x^0.5` |
| `penalty_risk` | `max(5%, 40% − 0.25 × Compliance − 0.10 × Audit)` |

This department is fundamentally different from the other five: its spend affects almost nothing
about *this* quarter's sales. Its entire value is reducing future risk and future cost. The Cash
Efficiency Bonus discounts **next** quarter's fixed costs — better forecasting doesn't sell more
units, it makes existing money go further.

Compliance is weighted more heavily than Audit in penalty risk because compliance failures are the
direct trigger for a penalty; audit prep mainly reduces severity once something has already gone
wrong.

---

## 6. `engines/quarter.py` — the chain

This is the file to understand. Everything else supports it.

`compute_quarter(opening_state, allocations, profile, seed, crisis_event=None) -> QuarterResult`

**The order of operations is load-bearing.** Each department produces a number that feeds another
department's formula. Computing them out of order is exactly how the two audit errors in the
source docs happened.

```
1.  Sum all 8 marketing channels                          → Raw Leads
2.  + SEO asset payout (from LAST quarter's asset)
3.  + Buzz payout (from LAST quarter's investment)
4.  × Brand multiplier          [Q2+ only — Q1 runs at exactly 1.0]
5.  × HR productivity multiplier
                                                          → Effective Leads

6.  MIN(Effective Leads, Sales Capacity × (1 − attrition))
                                                          → GATE 1 · Leads Used

7.  raw conversion = base + reps + CRM + CX + buzz bonus
8.  conversion = MIN(raw, R&D ceiling) + warranty bonus
                                                          → GATE 2 · Conversion Rate

9.  units from funnel = Leads Used × conversion
10. + free repeat units (prior repeat rate × prior units sold)
11. MIN(total demand, Available to Sell)
                                                          → GATE 3 · UNITS SOLD

12. Revenue = Units Sold × selling price
13. − COGS, − warranty cost, − holding cost               → Adjusted Gross Profit
14. − fixed costs, − total discretionary spend            → NET CASH FLOW
15. closing cash = opening cash + net cash flow
```

### The three gates, in one line each

- **Gate 1 — Sales capacity.** A productivity multiplier makes each lead *easier to convert*; it
  cannot make Sales' phones ring longer. So capacity is re-checked **after** all multipliers.
  Skipping that re-check was audit Error 2.
- **Gate 2 — Conversion ceiling.** Product quality caps how well you can convert. Warranty adds
  on top of the cap. Skipping the warranty add was audit Error 1.
- **Gate 3 — Supply.** You cannot sell what you haven't built.

Each gate also reports whether it *bound* (`capacity_bound`, `ceiling_bound`, `supply_bound`), so
the UI can tell a student "you wasted 216 leads' worth of demand because Sales couldn't handle it"
rather than just showing a smaller number.

### Other things this file owns

- **`Valuation`** — `0.70 × RevenueMultiple + 0.20 × AssetBased + IntangiblePremium`. The
  intangible premium is added in full, not weighted, because it captures goodwill the other two
  methods miss. If the seed doesn't state the balance-sheet constants, `blended_inr` comes back
  `None` with a `gap_reason` string instead of a guessed number.
- **`_total_assets_inr`** — `closing cash + inventory value + equipment NBV + product IP + AR`.
  Not stated as a formula anywhere; derived from two balance sheets in the docs, and it reproduces
  both exactly.
- **`_next_buzz_offset`** — the two-quarter buzz payout clock. Fresh investment restarts it.
- **Budget discipline** — spending into the working capital buffer is *allowed* but flagged
  (`spent_into_buffer`, `buffer_overspend_inr`). It's a scoring penalty, not a hard block.
- **Crisis stub** — `crisis_event` is accepted so the signature never has to change. Passing a
  non-`None` value **raises**, rather than quietly running a quarter with the crisis ignored.

### `QuarterResult`

Every intermediate step is a field on the result, not just the totals. `raw_leads`,
`effective_leads`, `leads_used`, `raw_conversion_pct`, `conversion_ceiling_pct`,
`units_from_funnel`, `available_to_sell` … ~60 fields in all.

That's deliberate: it lets tests assert the **ordering** rather than infer it from the final
total, and it lets the UI show a student the full chain. Two wrong steps can cancel out into a
right-looking total — that literally happened in the source docs.

---

## 7. `engines/state.py` — what goes in

Three frozen dataclasses, no I/O:

- **`QuarterAllocations`** — the 22 spend lines + `warranty_years`. Has `.marketing_total`,
  `.sales_total`, … and `.total_discretionary` as properties.
- **`CompanyState`** — opening state for one quarter. About 20 fields: cash, fixed costs,
  inventory, customers, the seven baselines (supplier reliability, logistics, satisfaction,
  engagement, compliance, forecast accuracy, audit readiness), and the five cumulative scores
  (brand, SEO asset, buzz, quality, innovation) plus feature completeness.
  - `.opening(seed)` builds Q1 state and **requires** all 13 opening scores — none can be
    defaulted, because a missing baseline would silently skew the productivity multiplier or move
    the conversion ceiling.
  - `.advance(**changes)` returns next quarter's opening state with the quarter number bumped.
- **`CrisisEvent`** — placeholder for Phase 10.

The cumulative scores are what make Q2 onward compound. That's the whole game: Q1 investments
show up as Q2 advantages.

---

## 8. `engines/survival.py` — is the run alive?

Three conditions, each returning **the specific reason it fired**, never a bare boolean. "This run
failed" isn't actionable without "because cash hit zero in Q3".

| Condition | Meaning | Outcome |
|---|---|---|
| `cash_exhausted` | Closing cash ≤ 0 in any quarter | **FAILED** — run is over |
| `buffer_breached` | Closing cash fell below the working-capital buffer at any point | DISTRESSED |
| `sustained_decline` | Negative NCF at the tier-assignment quarter, with cash falling 2+ consecutive quarters ending there | DISTRESSED |

Two things worth knowing:

**DISTRESSED is not game over.** It's the designer's warning tier — it changes the Q4 term-sheet
menu and nothing else. Only `cash_exhausted` ends a run. `is_terminal()` returns true only for
FAILED and COMPLETED.

**`sustained_decline` is anchored to one specific quarter**, not evaluated every quarter. It's a
Tier Assignment input, evaluated once at `total_quarters − 1` (Q3 in the standard 4-quarter run).
Read as a running health check it would flag a normal cash-burning startup as distressed by
construction — the canonical run that the source scores 82/100 would be DISTRESSED at Q2 while
holding 11× its buffer. An 82/100 company is not distressed, so that reading is wrong.

Conditions are declared in the **profile JSON** (`survival.conditions`), and each `id` maps to a
predicate in this file. A configured condition with no matching predicate is a hard error — a
check that silently does nothing is worse than one that's absent. Rule strings in JSON are
documentation; they are never evaluated.

---

## 9. `engines/gaps.py` and the two-pipeline situation

### `gaps.py`

Four functions that only raise `NotImplementedError` with a specific reason:
`negotiation_score`, `acceptance_probability`, `cx_decision_impact`, `momentum_score`.

Example: Negotiation Score sums six differently-scaled quantities with no weights, then multiplies
by two more unscaled factors. That cannot produce a 0–1 probability no matter what you feed it.
Clamping the output would mean inventing bounds the source never specifies. So it raises.

These live outside `engines/lines/` so that folder keeps one simple invariant: **everything under
`lines/` is a spend line that works.**

### The two pipelines — read this so you're not confused by the codebase

There are **two different simulation models** in this repo, and only one is live.

| | **22-line power-law engine** (LIVE) | **Legacy percentage matrix** (parked) |
|---|---|---|
| Model | `Leads = 375 × x^0.68` — spend is a continuous input | `Actual Impact % = Base % × Brand × Saturation × Inventory × Competitor` — a decision is a discrete event with a % effect |
| Code | `engines/quarter.py` + `engines/lines/` | `engines/legacy_matrix/` + `services/decision_engine.py` |
| Input | 22 spend lines | ~72-key decision taxonomy |
| Wired to `POST /lock`? | **Yes** | No |

The legacy model is genuinely incompatible with the live one — it's logged as a P0 conflict in
`docs/10-implementation-gaps.md`. We kept it, tested (including its `15% × 0.9 × 0.6 × 1.0 × 0.8
= 6.48%` validation case), in case the designer picks it for Marketing. **It is not dead code and
it is not the live path.** Don't wire it in without a decision from the client.

Separately, and permanently: **Business Impact and Evidence are independent pipelines.** Cognitive
scoring reads only `EvidenceRecord` rows, aggregated by cognitive dimension, never by workspace,
and never touches KPI data. That separation is architectural, not incidental.

---

## 10. `config/` — where every number lives

### `schema.py`
Pydantic models for all three config layers. `extra="forbid"` and `frozen=True` — a typo'd JSON
key becomes a load error instead of a silently ignored setting. Every numeric is `Decimal`.

Three top-level types:
- **`SimulationProfile`** — curve shapes for all 22 lines + valuation + survival + scoring. No
  company numbers.
- **`CompanySeed`** — one company's opening state. No curve shapes. Optional fields are `None`
  when the docs never state them; `None` is never a default, it's a declared gap.
- **`Scenario`** — which seed, which profile, how many quarters, when a crisis fires, plus the
  opening values for state the 22-line chain doesn't own (the four legacy modifiers, the six
  `*State` rows).

Config carries **provenance**, not just values. `BrandMultiplierConfig` has `formula`, `status`
and `note` alongside its coefficients. `EquipmentDepreciationConfig` says outright that it's a
straight-line fit through two data points, not a designer-confirmed rule. Anyone reading the JSON
can see which numbers are sourced and which are inferred, without reading Python.

### `loader.py`
`load_profile()`, `load_seed()`, `load_scenario()`, `available_scenario_ids()`. All
`lru_cache`d. Parses with `parse_float=Decimal` so coefficients stay exact.

The caches sit on inner functions so a default argument can't split one config across two cache
entries. `available_scenario_ids()` returns a **sorted tuple** because scenario assignment indexes
into it — an unstable order would make the same company resolve to a different scenario between
processes, which would break replay.

### `rules/`
`load_rules(workspace)`, `valid_decision_keys(workspace)`. The legacy per-decision rule tables
(`marketing_rules.json`, `finance_rules.json`, …). Only Marketing has a `base_impact` table.

---

## 11. `models/` — the database

| Table | Holds |
|---|---|
| `companies` | One simulation run. `scenario_id`, `seed_name`, `profile_name`, `run_status`, `survival_condition`, `survival_detail` |
| `quarters` | One quarter. `number`, `status` (in_progress/closed), denormalised `cash_balance`/`revenue` |
| `quarter_allocations` | **The 22 spend lines + warranty.** One row per quarter, built up by 6 department POSTs |
| `company_state_snapshots` | Serialised `CompanyState` at quarter close — **the carry-forward mechanism** |
| `quarter_performances` | The results and the scores (see §12) |
| `decisions` / `decision_logs` | Legacy pipeline: what was decided, and an immutable audit trail of each pipeline run |
| `evidence_records` | Behavioural signals — "Diversified Investment = YES" |
| `cognitive_scores` | One row per cognitive dimension per quarter |
| `modifiers` | The four legacy quarter modifiers, as rows so new types need no migration |
| `finance_states`, `marketing_states`, `product_states`, `sales_states`, `operations_states`, `cx_states` | Legacy per-workspace KPI snapshots |

### Two design calls worth explaining

**Why `company_state_snapshots` stores JSON instead of 20 columns.** `CompanyState` has ~20
cumulative fields with no other DB representation, and it changes as the engine grows. Twenty
parallel columns would drift out of sync with the dataclass every time a field is added.
`services/quarter_run_service.py` owns the serialisation, so `engines/` stays DB-free.

**Why `company.seed_name`/`profile_name` are copied at creation, not read through `scenario_id`.**
A company that has already played three quarters must keep running against the config it started
on, even if someone edits the scenario file tomorrow.

---

## 12. Where the scores are stored ← *the question everyone asks*

There are **two separate score systems**. They live in different columns of the same table and
are written by different pipelines that don't run at the same time.

### A. Business results — the live 22-line engine

**`quarter_performances.engine_result`** (JSONB) — the entire `QuarterResult`, all ~60 fields:
every lead count, every gate, revenue, COGS, net cash flow, closing cash, valuation, and the full
closing state. Decimals are serialised as **strings**, not floats, so they round-trip exactly.

**`quarter_performances.result_hash`** — SHA-256 over the canonically-sorted serialised result
*plus* the run status. Not Python's `hash()`, which is salted per process and would never compare
equal across two runs. This is our determinism proof: same inputs → same hash, always, on any
machine.

**`company_state_snapshots.state`** (JSONB) — the closing `CompanyState`, which becomes next
quarter's opening state. This is the carry-forward.

Written by: `services/quarter_run_service.py::run_quarter()`.

### B. Cognitive scores — the behavioural pipeline

**`cognitive_scores`** — one row per dimension per quarter. Today that's exactly three
dimensions: `strategic_thinking`, `investor_confidence`, `employee_burnout`. Evidence records
carry more categories than that (`adaptability`, `risk_management`, `capital_allocation`,
`long_term_thinking`), but a category only becomes a scored dimension once it has a baseline
override or a registered weight — see below.

**`quarter_performances.dimension_scores`** (JSONB) + **`quarter_performances.overall_score`** —
the rollup the leaderboard reads. `GET /leaderboard` reads these rollups; it never live-aggregates
`cognitive_scores`.

Written by: `services/cognitive_scoring_engine.py`, via `services/quarter_engine.py`.

Both column groups are nullable, because neither pipeline requires the other to have run first.

### How a cognitive score is computed

Every dimension starts at a baseline of 50 (`investor_confidence` 60, `employee_burnout` 10).
Then evidence adds weight:

```python
EVIDENCE_WEIGHTS = {
    "balanced_budget":        {"strategic_thinking": 3.0},
    "diversified_investment": {"strategic_thinking": 2.0},
    "long_term_investment":   {"strategic_thinking": 3.0},
    "consistent_objective":   {"strategic_thinking": 2.0},
}
```

**Only these four weights are confirmed by the spec's worked example.** Every other evidence key
the evidence engine can emit contributes **0** until the product owner gives us a weight. It is
never guessed. Scores clamp to 0–100.

That's also why only three dimensions get scored: `score_quarter()` scores exactly the dimensions
that have a baseline override (`investor_confidence`, `employee_burnout`) or appear in
`EVIDENCE_WEIGHTS` (`strategic_thinking`). The moment the product owner supplies weights for
`adaptability` and the rest, they start being scored — no other code change needed.

---

## 13. `services/` — the glue

### `quarter_run_service.py` — the important one

`run_quarter(session, quarter_id)`. This is what `POST /lock` calls. It is a **thin persistence
wrapper** — no business logic. Every number in the result comes from `compute_quarter()`.

Sequence:
1. Load the quarter. If already CLOSED, return the persisted result unchanged (**idempotent** —
   calling lock twice never recomputes, never rewrites, never duplicates a row).
2. Load seed + profile from the company's stored names.
3. Load the `QuarterAllocation` row → convert to `QuarterAllocations` dataclass.
4. Load opening state: Q1 → `CompanyState.opening(seed)`; Q2+ → the prior quarter's snapshot.
5. **Call `compute_quarter()`.**
6. Evaluate survival over the whole run history (not just this quarter — `buffer_breached` is "at
   any point" and `sustained_decline` counts a streak).
7. Write company run status, `QuarterPerformance`, `CompanyStateSnapshot`; flip the quarter to
   CLOSED. **All in one transaction.**

Two helpers worth knowing:

- `_to_jsonable` / `_from_jsonable` — generic dataclass↔JSON round-trip that walks
  `dataclasses.fields()`. `QuarterResult` + `Valuation` + `CompanyState` are 60+ fields. A
  hand-written per-field converter would go stale the next time someone adds a field to the
  engine. This one can't.
- `_run_status` — FAILED wins outright (a run that ran out of cash on its last quarter did not
  "complete"). Otherwise reaching `total_quarters` means COMPLETED, which shadows DISTRESSED. The
  distress signal isn't lost, though — `survival_condition` records what fired regardless of the
  status it ends up under, which is what Q4 tiering will read.

### `company_service.py`

- `create_company()` — materialises the company row from a scenario.
- `assign_scenario_id()` — picks a scenario **deterministically** from a SHA-256 of the company's
  own UUID, seeded into `random.Random`. Not `random.choice()` on the global RNG, and not Python's
  `hash()` (salted per process). Replaying a run with the same company id must land on the same
  scenario, in this process and any other.
- `create_quarter()` — opens the next quarter. Refuses if the run is terminal, refuses past
  `total_quarters`, and reads opening cash from the **prior snapshot** so the quarter's
  denormalised `cash_balance` can't drift from what the engine will actually run against.
- `_opening_state_rows()` — one `*State` row per workspace from scenario config.
  `finance.cash_balance` is the one value overlaid from the seed, so a company number is never
  duplicated into scenario config.

### The rest

| File | Role |
|---|---|
| `decision_engine.py` | Legacy Business Impact. Marketing → the percentage matrix; a handful of Finance/Product handlers; and `GAP_REASONS` — **one specific reason per uncovered decision key**, catalogued during an audit, not a blanket "not implemented". |
| `evidence_engine.py` | Turns a decision into behavioural evidence flags. Only the two extractors the spec fully worked through are implemented; anything else raises rather than guessing. |
| `cognitive_scoring_engine.py` | Evidence → dimension scores. Workspace-agnostic by design: it aggregates only by category and never branches on `record.workspace`, so adding a workspace never touches this file. |
| `quarter_engine.py` | Legacy orchestrator: recurring costs → per-decision impact + evidence → cross-department handoffs → cognitive scores. DB-session-agnostic; returns ORM rows for the caller to persist. |
| `formulas/` | Small per-decision formulas transcribed verbatim from the rules JSON. |

---

## 14. `routes/` — the API

Routes are thin. Load, call a service, return.

| Endpoint | Does |
|---|---|
| `POST /companies` | Create a company (assigns a scenario if none given) |
| `GET /companies/{id}` | Read-through. Computes nothing. |
| `POST /companies/{id}/quarters` | Open the next quarter |
| `GET /companies/{id}/quarters/{qid}` | Quarter detail incl. current allocations |
| `POST /.../allocations/{department}` | **Submit spend for one department** (6 routes) |
| `POST /.../quarters/{qid}/lock` | **Run the engine.** Idempotent. |
| `GET /.../quarters/{qid}/report` | Read the persisted result. Recomputes nothing. |
| `GET /companies/{id}/leaderboard` | Read the performance rollups |
| `POST /.../{workspace}/decisions` | Legacy per-decision submission (6 workspaces) |
| `GET /health` | Liveness |

### Things to notice

**`_factory.py`** builds the identical 3-endpoint router for all 6 workspaces. They were
byte-for-byte identical except the enum, the model and two schema types. Six hand-rolled files
would each need the same guard-rail fix applied separately.

**`allocations.py`** uses `_add_department_route()` — a function call per department, not a loop.
Each closure binds its own `department`/`schema` as function arguments, sidestepping the classic
Python late-binding bug where every route would get the loop's last value.

**`deps.py::get_open_quarter`** is the single place the immutability rule lives: once a quarter is
locked, decisions are rejected with a 409. Every submission route depends on it rather than
duplicating the check.

### The rule nobody may break

> **No within-quarter compounding.** All allocations evaluate against the **opening** snapshot.
> Submitting a spend line never mutates a `*State` row. Only `run_quarter()` writes closing state,
> once, at lock.

`_factory.py::_state_to_dict` is read-only on purpose, and carries a comment saying don't add a
write-back. This is the design, not an oversight — if submitting spend mutated state, the order in
which a student clicked "submit" would change their results.

---

## 15. Worked example — one quarter of a real company

Nadi Wear, an activewear D2C brand. Quarter 1.

**Opening:** ₹1.5 Cr cash · ₹23.5 L quarterly fixed costs · 600 units in inventory · 4,000
customers · shirt sells at ₹9,999, costs ₹3,250 to make · base conversion 19% · working capital
buffer ₹10 L.

**The CEO allocates ₹45 L** across the 22 lines — ₹16 L marketing, ₹8 L sales, ₹5 L R&D, ₹6 L
operations, ₹3 L HR, ₹7 L finance/admin — and chooses a **1-year warranty**.

Now watch the chain:

**Leads.** Eight channels produce **2,719 raw leads**. Pre-Launch Buzz contributes *zero* — its
₹1.92 L buys a Buzz Score of 5.5 that pays out over Q2 and Q3. Content/SEO's ₹1.28 L produces only
a trickle now but builds a 4.5-point SEO asset that pays 112 free leads next quarter. No brand
multiplier applies (Q1 always runs at 1.0 — brand built now pays from Q2). HR's ₹1.2 L on culture
lifts satisfaction to ~70, giving a **1.082× productivity multiplier**: 2,719 → **2,941 effective
leads**.

**Gate 1 fires.** Sales reps at ₹5.45 L bought `500 × 5.45 = 2,725` capacity. Attrition is 0 in
Q1. `MIN(2,941, 2,725) = 2,725 leads used.` **216 leads' worth of demand is thrown away** — HR
made the team more effective, but the phones still only ring so long. The result flags
`capacity_bound = True` so the student sees this.

**Gate 2 fires.** Raw conversion adds up to 27.25% (19% base + reps + CRM + CX). But R&D only got
₹5 L, so quality is 9.95 and innovation 7.5, giving a ceiling of `15% + (9.95 + 0.5×7.5) × 0.3%`
= **19.11%**. The raw rate is capped. Then the warranty adds **1.5 pts on top of the cap** →
**20.6%**. The company just lost 8 percentage points of conversion because the product isn't good
enough yet. *That is the lesson the ceiling exists to teach.*

**Gate 3 doesn't fire.** Manufacturing's ₹3.3 L bought 923 capacity, discounted by 74.9% supplier
reliability, plus 600 carried inventory = **1,291 available**. Demand is only 562 units, so supply
isn't the constraint this quarter — but 729 units sit unsold and cost ₹1.09 L in holding.

**Units sold: 562.** (`2,725 × 20.6%`. No repeat units — Q1 has no prior quarter.)

```
Revenue          562 × ₹9,999          =  ₹56,15,653
COGS             562 × ₹3,087          = −₹17,33,449
                                          ───────────
Gross profit                           =  ₹38,82,205
Warranty cost    562 × 6% × ₹1,500     =    −₹50,630
Holding cost     729 × ₹150            =  −₹1,09,411
                                          ───────────
Adjusted gross profit                  =  ₹37,22,163
Fixed costs                            = −₹23,50,000
Discretionary spend                    = −₹45,00,000
                                          ───────────
NET CASH FLOW                          = −₹31,27,837
Closing cash    ₹1,50,00,000 − ₹31,27,837 = ₹1,18,72,163
```

**Was that a bad quarter?** No — and this is the point. The discretionary ceiling was ₹1.16 Cr
(cash − fixed costs − buffer); ₹45 L is well inside it, so `spent_into_buffer = False`. Closing
cash is 11× the buffer, so survival stays ACTIVE. The ₹31 L burn bought durable assets: Brand 8.7,
SEO 4.5, Buzz 5.5, Quality 9.95, Innovation 7.5. Company valuation went from ~₹4 Cr raised to
~₹5.25 Cr.

**And Q2 inherits all of it.** Brand 8.7 becomes a **1.174× lead multiplier**. The SEO asset pays
112 free leads. Buzz pays ~83 free leads. Repeat purchase rate is now 19%, so ~107 units sell with
no lead cost at all. Fixed costs drop slightly from the cash efficiency bonus. **That compounding
is the game.** A student who spends everything on Google Ads in Q1 gets a better Q1 and a much
worse Q2, Q3 and Q4.

---

## 16. What's done, and what isn't

### Done

| Area | Status |
|---|---|
| Config layer (profile / seed / scenario + loaders + validation) | ✅ |
| All 22 spend lines | ✅ |
| `compute_quarter` — full chain, three gates, valuation, carry-forward | ✅ |
| Q1 validated against the reference doc to ±1 unit / ±₹1 | ✅ |
| Q2 carry-forward and compounding | ✅ |
| Survival engine (3 conditions) + run-status gating on quarter creation | ✅ |
| Persistence: snapshots, result JSON, determinism hash, idempotent lock | ✅ |
| REST API: company, quarter, 6 allocation routes, lock, report, leaderboard | ✅ |
| Legacy pipeline: decision engine, evidence, cognitive scoring, matrix | ✅ (parked, tested) |
| Alembic migrations (4) | ✅ |
| **308 tests passing** | ✅ |

### Not done (deliberately)

| Area | Why |
|---|---|
| **Crisis system (Phase 10)** | Constants exist in `docs/11`, not wired. `compute_quarter` **raises** on a non-`None` crisis rather than ignoring it. |
| **Scoring engine (Phase 11)** | `ScoringConfig` schema exists; `engines/scoring.py` doesn't yet. 21 sub-criteria across 7 traits, with `MECHANICAL` vs `JUDGMENT` already classified — a JUDGMENT criterion comes back UNSCORED and is held out of the denominator, never inferred from spend. |
| **Momentum Score / tier assignment** | Names seven inputs, gives no weights, no normalisation, no tier cut-offs. `gaps.py` raises. |
| **CX engine formulas** | All 12 CX decisions name an engine (Retention, Loyalty, Trust…) — none is defined anywhere. `gaps.py` raises. |
| **Negotiation / acceptance probability** | Mathematically cannot produce a 0–1 probability as specified. Raises. |
| **PulseWear as a runnable company** | 9 required constants never stated in the docs. Shipping it would 500 on the first lock. |
| **Marketing % → absolute KPI delta** | Docs give "Sales: 6.48%" but never say what baseline that percentage applies to. |
| **Most evidence weights** | Only 4 confirmed. The rest contribute 0 until the product owner supplies them. |
| **Operations / People rules JSON** | Don't exist, so those routers aren't wired — better than shipping a router that can never accept a real decision. |

Every one of these is tracked in `docs/10-implementation-gaps.md` with a P0/P1/P2 priority, and
several now have designer answers in `docs/17-designer-resolutions.md`.

---

## 17. Working on this codebase

```bash
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
uv run pytest
```

`DATABASE_URL` must be the Supabase **connection-pooler** URL (port 6543), not
`db.<ref>.supabase.co` — that host is IPv6-only. The prepared-statement cache is disabled in
`core/db.py` because PgBouncer transaction pooling breaks it.

### Rules to follow

1. **Never invent a coefficient.** Not in `docs/` → raise `NotImplementedError` with the specific
   reason.
2. **`engines/` stays pure.** No DB, no clock, no RNG, no filesystem.
3. **No company number in engine code.** It goes in a seed. No curve shape in a seed — that goes
   in a profile.
4. **`Decimal` everywhere.** Round at persistence and display only.
5. **Don't add write-back in `routes/_factory.py`.** No within-quarter compounding.
6. **Commit messages must match their diff.** `docs:` only if the diff is docs-only.
7. **Every change is a deliberate value addition** with a one-sentence justification. No cosmetic
   edits, no padding commits.

### Where to look first

| Task | File |
|---|---|
| A number is wrong | `engines/quarter.py`, then the relevant `engines/lines/*.py` |
| A coefficient needs changing | `config/profiles/default.json` — never the code |
| Adding a company | `config/seeds/<name>.json` + a scenario JSON. Zero code. |
| Something isn't persisting | `services/quarter_run_service.py` |
| Understanding intended behaviour | `docs/00-formula-index.md`, then `docs/12-quarter-1-reference.md` |
| What's knowingly missing | `docs/10-implementation-gaps.md` |
