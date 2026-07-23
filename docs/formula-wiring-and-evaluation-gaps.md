# Formula Wiring & Evaluation Gap Audit

Everything in this document was verified against the current code at the time of
writing (branch `main`, commit `e24fc04`) — every claim below has a `file:line`
pointer next to it. Nothing here is inferred or guessed; where the source docs
don't specify a value, that's called out explicitly instead of assuming one
(see `CLAUDE.md`'s standing rule against fabricating formulas/thresholds).

Legend:

- ✅ wired, tested, and — as far as a single decision submission goes — correct
- ⚠️ wired but has a real correctness gap under specific conditions (see the
  scenario)
- ❌ not wired — raises `NotImplementedError`/422 today, on purpose

---

## 1. The one architectural gap that blocks *everything*: no write-back to `*State`

This is the most important finding in this audit and applies even to the
decisions marked "working" in the README.

`app/routes/_factory.py:72-94` computes `impacts` via `compute_decision_impact`
and logs them to `DecisionLog`, but **never writes the computed value back onto
the `*State` row it read from**. Look at the full `submit_decision` body —
there is no `session.add`/attribute-set on `current_state` anywhere, and
`current_state` itself is only ever read (`_factory.py:65-67`), never mutated.

Concretely, for Finance:

1. `FinanceState.cash_balance = 1,000,000`.
2. Submit `FIN-003` (Capital Expenditure) with `capex_amount=30000` →
   response says `remaining_cash: 970000`. Correct value, correctly computed.
3. **Nothing writes `970000` back to `FinanceState.cash_balance`.**
4. Submit `FIN-002` (Emergency Cash Reserve) in the same quarter → it reads
   `cash_balance` from the (unchanged) `FinanceState` row and computes
   `reserve_ratio` against the *original* `1,000,000`, not `970,000`.

Two Finance decisions in the same quarter that both depend on cash never
compound — every decision in a quarter evaluates against the same stale
opening snapshot. This isn't a hypothetical: `tests/routes/test_finance_product_sales_decisions.py`
only ever submits one decision per test against a freshly seeded state, so
this never gets exercised.

This is also why nothing currently *can* write a `FinanceState`/`MarketingState`/etc.
row from a decision result — see §2, the `actual_value → absolute delta`
TODO is a prerequisite for fixing this, not an independent gap.

Related, smaller version of the same problem: there is currently no
`POST /companies` route (main.py only registers `finance`, `marketing`,
`product`, `sales`, `cx`, `quarter` — no `company` router exists at all).
Nothing in the running app ever creates a `Company`, `Quarter`, `*State`, or
`Modifier` row. Every test that exercises a decision route constructs these
directly via the ORM in a fixture (`tests/routes/conftest.py:7-23`,
`tests/routes/test_finance_product_sales_decisions.py:17-33`) — bypassing the
API entirely. On the real deployed app today, `GET /.../state` 404s forever
and `POST /.../decisions` 422s forever for any decision needing state, because
nothing ever seeds one. (This is the seeding work already flagged in the prior
turn — company/quarter creation — and is a separate, tracked gap; noted here
because it compounds with the write-back gap above.)

---

## 2. Marketing: silent wrong-looking-right values when Modifier rows are missing

`decision_engine.apply_modifier_chain` (`app/services/decision_engine.py:58-63`):

```python
def apply_modifier_chain(base_value, modifiers):
    actual = base_value
    for value in modifiers.values():
        actual *= value
    return actual
```

If `modifiers == {}` (no `Modifier` rows exist for the quarter — which, per §1,
is the *default* state of every quarter today since nothing seeds them), this
returns `actual == base_value` with **no error**. Compare this to how Finance
handles the same "prerequisite data missing" situation —
`_require_state_field` (`decision_engine.py:88-95`) raises a `ValueError` that
surfaces as a 422 with an explicit "none exists yet" message.

So today: submit a Marketing decision with no `Modifier` rows seeded (the
normal case, since nothing seeds them) → **201 success**, with
`business_impact` showing `actual_value == base_value` for every field. That
response is indistinguishable from a legitimate "all modifiers are 1.0"
result. A frontend or a report built on this data cannot tell "modifiers were
genuinely neutral" apart from "modifiers were never configured." Finance fails
loud for the equivalent situation; Marketing fails silent. One of these two
behaviors needs to change once real modifier seeding exists — flagging the
inconsistency rather than picking one, since which is "correct" depends on
whether Modifier rows are meant to always exist by the time decisions are
submitted (which is a company/quarter-creation design decision, not a
decision_engine one).

---

## 3. `marketing_budget_allocation` payload validation: float equality bug

`app/schemas/marketing.py:27-29`:

```python
spent = sum(channel_spend.values())
if spent != total_budget:
    raise ValueError(...)
```

Floats compared with `!=`. A perfectly valid split like
`{"increase_google_ads_budget": 33333.33, "increase_seo_budget": 33333.33, "sustainability_campaign": 33333.34}`
against `total_budget: 100000.0` can fail this check due to binary
floating-point rounding even when the numbers "add up" to a human. This is a
**false-422 risk on correct input**, not a false-accept — the failure mode is
the API rejecting a legitimate submission, which is worse for a student-facing
product than being slightly permissive. Needs either a tolerance (e.g.
`abs(spent - total_budget) < 0.01`) or a switch to `Decimal` for money fields
(the rest of the codebase already uses `Decimal` for currency —
`FinanceState.cash_balance`, `MarketingState.marketing_spend`, etc. — this
schema is the one place still using bare floats for money).

---

## 4. SAL-011 negotiation: unbounded/unclamped output

`app/services/formulas/sales.py:44-56`:

```python
def negotiation_score(price_competitiveness, relationship_score, inventory_availability,
                       brand_strength, delivery_capability, risk):
    return price_competitiveness + relationship_score + inventory_availability + brand_strength + delivery_capability - risk

def acceptance_probability(negotiation_score_value, buyer_flexibility, market_demand):
    return negotiation_score_value * buyer_flexibility * market_demand
```

This is verbatim from `sales_rules.json`'s `negotiation_engine`, so the
formula itself isn't in question. But unlike every percentage formula
elsewhere in `app/services/formulas/*.py` (csat, churn_rate, conversion_rate,
etc. — none of which clamp either, but all of which are inherently bounded by
their `x/y*100` shape when x≤y), this one has no bound at all and is called
"probability." Nothing in `SalesDecisionSubmit` or `handle_sal_011_negotiation`
constrains `buyer_flexibility`/`market_demand` to `[0, 1]` or `risk` to a
sane range.

**Concrete failure scenario:** `negotiation_inputs` with large
`price_competitiveness`/`relationship_score`/etc. and `buyer_flexibility=5,
market_demand=5` (nothing rejects these) produces an `acceptance_probability`
in the hundreds or thousands — a "probability" over 100%, silently accepted
and returned as a 201. Also reachable in the other direction: a large `risk`
value makes `negotiation_score` negative, and a negative score times two
positive flexibility/demand numbers gives a negative "probability." Neither
is caught, because the doc never specifies valid ranges for the 8
`negotiation_inputs` fields (this is itself a source-doc gap, not something
I'm inventing bounds for — see §6).

---

## 5. CXState vs. `cx_rules.json`'s `variables`: model only captures 3 of 16

`cx_rules.json` (`app/config/rules/cx_rules.json:17-34`) defines 16 named
variables with `initial` values (`customer_satisfaction: 78`,
`net_promoter_score: 32`, `customer_loyalty: 55`, `brand_trust: 55`,
`brand_reputation: 58`, `churn_rate: 0.06`, `repeat_purchase_rate: 0.18`,
`referral_rate: 0.09`, `community_members: 1200`, `product_adoption: 62`,
`average_resolution_time_hrs: 24`, `first_contact_resolution: 0.72`,
`return_rate: 0.021`, `warranty_claims: 0.018`, `customer_lifetime_value: null`,
`social_sentiment: 62`).

`CXState` (`app/models/cx.py:12-22`) only has `csat_score`, `churn_rate`,
`support_tickets_resolved` — and `support_tickets_resolved` isn't even one of
the 16 documented variables. 13 of the 16 documented CX variables have no
column anywhere to be persisted into, even once CX decisions get formulas.
This isn't blocking anything today (0 of 12 CX decisions are wired — see §6),
but it means wiring a CX decision later will hit a second wall even after a
formula is confirmed: the model doesn't have anywhere to put most of the
outputs.

---

## 6. Formula-by-formula status (why each gap breaks, exactly)

### Finance (4 of 13 wired)

| decision_key | status | breaks at | reason |
|---|---|---|---|
| FIN-002 Emergency Cash Reserve | ✅ | — | needs `FinanceState.cash_balance` (§1 caveat applies) |
| FIN-003 Capital Expenditure | ✅ | — | needs `FinanceState.cash_balance` (§1 caveat applies) |
| FIN-004 Cost Optimisation | ❌ | `decision_engine.py:346-348` → `GAP_REASONS[("finance","FIN-004")]` | `reduction_pct` per level (none/mild/moderate/aggressive) never given a number in `finance_rules.json:26-30` |
| FIN-005 Debt Utilisation | ✅ | — | needs `FinanceState.cash_balance`; loan validated against `{0, 1_000_000, 2_500_000, 5_000_000}` (`decision_engine.py:115-122`) |
| FIN-006 Hiring Budget Approval | ✅ | — | payload-only, no state dependency |
| FIN-001 Dept Budget Allocation | ❌ | same | formula field (`finance_rules.json:13`) is `"budget <= available_cash"` — a validation constraint, not a value |
| FIN-007 Growth Investment Allocation | ❌ | same | formula field is `"investment_distribution"` — not a concrete expression |
| FIN-008..013 | ❌ | same | no `formula` field in the source doc at all — only `weights_inferred` placeholders explicitly marked `"UNSPECIFIED_IN_SOURCE_DOC_INFERRED_DEFAULT"` (`finance_rules.json:49-77`) |

### Product (1 of 10 wired)

| decision_key | status | breaks at | reason |
|---|---|---|---|
| PRO-003 Prioritize Features | ✅ | — | payload-only |
| PRO-001 | ❌ | `decision_engine.py:346-348` | `"opportunity_x_market_demand"` doesn't match any `core_formulas` entry |
| PRO-002 | ❌ | same | `"creates_new_product"` is a state-transition label |
| PRO-004 R&D Investment | ❌ | same | doc formula is `previous_innovation_score + rnd_investment`; `core_formulas.innovation_score` is `rnd_investment + new_features + technology_adoption` — genuinely different terms, ambiguous which governs |
| PRO-005 Quality Strategy | ❌ | same | doc formula `base_quality + qa_investment` is a strict subset of `core_formulas.product_quality`'s 4 terms — unclear if the other 2 default to zero |
| PRO-006 | ❌ | same | `"development_status_eq_100"` — boolean gate |
| PRO-007 | ❌ | same | `"feedback_collected"` — not value-producing |
| PRO-008 | ❌ | same | `"readiness_gte_threshold"` — threshold check, threshold value unspecified |
| PRO-011 | ❌ | same | `"roadmap_priority_score"` — not defined anywhere |
| PRO-012 | ❌ | same | `"product_lifecycle"` — not defined anywhere |

Also: `product_rules.json:3` explicitly notes **PRO-009 and PRO-010 don't
exist** in the source spec (only 10 of 12 IDs were given) — not a bug, just
worth knowing `valid_decision_keys("product")` will reject those two by
design, not by omission.

### Sales (1 of 12 wired)

| decision_key | status | breaks at | reason |
|---|---|---|---|
| SAL-011 Negotiation | ✅ (see §4 for the unbounded-output caveat) | — | own handler, not the generic formula shape |
| SAL-001..010, SAL-012 | ❌ | `decision_engine.py:346-348` | `sales_rules.json`'s `decisions` block (lines 4-15) has no `formula` key on any entry — only `score_weight`/`affects`. The `formulas` block (lines 17-32) is general sales-metric math (revenue, conversion_rate, CLV, etc.), never mapped to a specific `decision_key` |

### CX (0 of 12 wired)

All 12 (`CX-001`..`CX-012`) raise `NotImplementedError` at
`decision_engine.py:346-348` — same shape as Sales: `cx_rules.json`'s
`decisions` block has no `formula` field on any entry; the `formulas` block
(customer_satisfaction, churn_rate, nps, etc.) is workspace-wide math never
tied to a `decision_key`.

### Marketing (25 of 25 wired, subject to §2's silent-degradation risk)

All marketing decisions with a `base_impact` array in `marketing_rules.json`
work via the generic modifier-chain path
(`decision_engine._compute_marketing_table_impact`, `decision_engine.py:66-78`).
An unrecognized `decision_key` raises `KeyError` there (not caught by the
factory's `except (NotImplementedError, KeyError, ValueError)` — it is
caught, this is correct — verified at `_factory.py:80`).

### Operations & People — no router at all

`OperationsState` model exists (`app/models/operations.py`) but there is no
`operations_rules.json`, no `app/routes/operations.py`, and no router
registered in `main.py`. People has neither a model nor a rules file. This is
intentional per `README.md:136-140` (not scaffolding dead endpoints) — noted
here for completeness, not as a new finding.

---

## 7. Evidence pipeline: 1 of ~64 decision_keys registered

`EVIDENCE_EXTRACTORS` (`app/services/evidence_engine.py:127-129`) has exactly
one entry: `(Workspace.MARKETING, "marketing_budget_allocation")`. Every
other decision — including all 24 other working Marketing decisions and all 6
working Finance/Product/Sales decisions — raises `NotImplementedError` inside
`generate_evidence` (`evidence_engine.py:145-151`). This is non-fatal by
design (`_factory.py:96-112` catches it and reports
`evidence_generated: 0`), but it means the Evidence/Cognitive-Scoring half of
the product is functionally inert for every decision except one.

Two inferred (not sourced) constants inside that one extractor, flagged
in-code already but worth surfacing here since they directly affect
`risk_level`/evidence-flag *values*, not just whether evidence exists:

- `LONG_TERM_MARKETING_CHANNELS = {"increase_seo_budget", "increase_content_marketing", "sustainability_campaign"}`
  (`evidence_engine.py:38`) — the doc says "SEO/Community/Brand, not just
  performance/paid" but never gives the literal channel-key taxonomy; this
  mapping is inferred.
- `MEDIUM_RISK_THRESHOLD = 0.4` (`evidence_engine.py:43`) — only the `>70%`
  "High Channel Dependency" cutoff is in the doc; the Medium/Low split at 40%
  is inferred, not sourced.

## 8. Cognitive scoring: 4 of the evidence keys the pipeline *can* emit actually move a score

`EVIDENCE_WEIGHTS` (`app/services/cognitive_scoring_engine.py:33-38`) has
weights for exactly `balanced_budget`, `diversified_investment`,
`long_term_investment`, `consistent_objective` — the four from the spec's one
worked example. But `extract_marketing_budget_allocation_evidence`
(`evidence_engine.py:46-90`) itself emits **six** evidence keys:
`diversified_investment`, `long_term_investment`, `high_channel_dependency`,
`balanced_budget`, `risk_level`, `unused_budget`. Three of its own six outputs
(`high_channel_dependency`, `risk_level`, `unused_budget`) have no registered
weight and are silently no-ops in scoring — they get written to
`EvidenceRecord` correctly, but `score_dimension` (`cognitive_scoring_engine.py:50-56`)
never adds anything for them because `EVIDENCE_WEIGHTS.get(record.evidence_key, {})`
returns `{}`. `consistent_objective` — one of the four *weighted* keys — is
never emitted by any extractor at all, so its weight is dead code today.
`extract_adaptability_evidence`'s four dynamic keys
(`pivoted_quickly_<channel>`/`ignored_feedback_<channel>`,
`evidence_engine.py:118-123`) are also unweighted.

Net effect: submitting `marketing_budget_allocation` today can move the
`strategic_thinking` score, but the `risk_management` signal it *also*
generates (`high_channel_dependency`, `risk_level`) never reaches any
cognitive dimension, even though `risk_level` clearly ought to feed
`risk_management`. This is a real gap, not a design choice — flagged rather
than guessed at, since the actual weight for e.g. `high_channel_dependency → risk_management`
isn't in the spec's worked example.

---

## 9. Scenarios with no code path at all today

- Any Operations or People workspace decision (no router — §6).
- Any Sales decision except SAL-011 (11 of 12 gapped).
- Any CX decision (12 of 12 gapped).
- Any Finance decision except FIN-002/003/005/006 (9 of 13 gapped).
- Any Product decision except PRO-003 (9 of 10 gapped, +2 IDs that don't exist).
- Cross-department handoffs beyond Marketing Leads → Sales Capacity — `HANDOFFS`
  (`quarter_engine.py:73-75`) registers exactly one pair; Product
  Readiness→Sales Launch timing and Operations Inventory→Sales fulfillment
  (both named in the Quarter Flow doc per `quarter_engine.py`'s own comment)
  have no handler.
- Company/Quarter creation, and quarter-advance carry-forward — no route
  exists yet (tracked separately, this is the work discussed earlier in this
  conversation; blocked on real PulseWear/Company-Load-State starting values,
  which I still don't have).
- Sequential decisions compounding within one quarter (§1 — nothing writes
  computed impact back to `*State`, so this literally cannot happen yet even
  for the "working" decisions).
- `Decision.status` ever reaching `DecisionStatus.PROCESSED` — the enum value
  exists (`models/decision.py:27`) but nothing ever sets it; every submitted
  decision stays `SUBMITTED` forever (`_factory.py:59`). Minor, but it means
  the audit trail can't currently distinguish "submitted" from "successfully
  processed" by status alone — you have to check for the presence of
  `DecisionLog` rows instead.

## 10. Scenarios where valid-looking input silently produces a wrong or misleading value

(As opposed to §6/§9's decisions that fail loud with 422/`NotImplementedError`.)

1. **Marketing decision with no `Modifier` rows seeded** → 201, `actual_value == base_value`
   for every field, indistinguishable from genuinely-neutral modifiers. (§2)
2. **`marketing_budget_allocation` with a channel split that sums correctly
   to a human but not in binary float** → false 422 on valid input. (§3)
3. **SAL-011 with `buyer_flexibility`/`market_demand` outside a sane `[0,1]`
   range, or a large `risk` value** → `acceptance_probability` outside `[0,100]`,
   or negative — returned as a normal 201 with no warning. (§4)
4. **Two decisions in the same quarter that both depend on the same `*State`
   field** (e.g. FIN-002 then FIN-003, both reading `cash_balance`) →
   both compute against the same stale opening value; the second decision's
   result silently ignores the first decision's effect. (§1)
5. **`high_channel_dependency`/`risk_level`/`unused_budget` evidence from
   `marketing_budget_allocation`** → recorded correctly in `EvidenceRecord`,
   but contributes nothing to any `CognitiveScore` dimension — a report that
   reads cognitive scores would never reflect a student's risky
   over-concentration in one channel, only their diversification. (§8)

---

## 11. What I still need before more of this can be wired (no invented values)

- **Numeric `reduction_pct` per FIN-004 option** (none/mild/moderate/aggressive).
- **`investment_distribution` formula for FIN-007** as a concrete expression.
- **Any formula field for FIN-008 through FIN-013** (currently only inferred
  scoring weights, explicitly marked as such in the JSON).
- **PRO-001/002/004-008/011/012**: either the correct formula (where two
  candidates conflict, e.g. PRO-004/PRO-005) or confirmation of which term
  set governs.
- **Per-decision formulas for all 11 remaining Sales decisions** and **all 12
  CX decisions** — right now only workspace-wide metric formulas exist, never
  tied to a `decision_key`.
- **`operations_rules.json` and `people_rules.json`** — neither exists, so
  neither workspace can be wired at all.
- **How a Marketing `actual_value` percentage converts into an absolute delta
  on a `*State` row**, and the equivalent for Finance/Product/Sales absolute
  values that also never get written back (§1) — this is the single highest-
  leverage gap to close, since it blocks write-back for every decision,
  wired or not.
- **Valid ranges for `SAL-011`'s 8 `negotiation_inputs` fields** (§4).
- **The exact CX variable list Elin actually wants persisted per quarter**,
  reconciled against `CXState`'s current 3 columns vs. `cx_rules.json`'s 16 (§5).
- **PulseWear / Company Load State starting values** for every `*State` field
  and the 4 `Modifier` rows — asked for at the end of the prior turn, still
  outstanding, and now also a prerequisite for closing §1's write-back gap
  end-to-end (you need a real opening snapshot to prove the write-back is
  correct against).
