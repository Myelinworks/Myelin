# Implementation Gaps Register

> Derived. **Every item here must raise `NotImplementedError` with the stated reason, or be
> resolved by the simulation designer before implementation.**

Standing discipline for this project: *no guessed formulas presented as authoritative; visible
gaps preferred over silently wrong numbers.*

---

## P0 — Blocking: two conflicting company baselines

> ✅ **RESOLVED** by `docs/17-designer-resolutions.md` — **Nadi Wear is canonical**; PulseWear is
> deprecated. The entry below is kept for the reasoning that led to the question. PulseWear's
> seed stays in the repo, still unable to run a quarter, as the guard-rail proving the engine
> reads company numbers from config rather than code
> (`tests/engines/test_quarter_company_agnostic.py`).

The source set describes **two different companies** with incompatible economics.

| | PulseWear (`03`) | Nadi Wear (`12`–`16`) |
|---|---|---|
| Capital raised | ₹2.00 Cr | ₹4.00 Cr |
| Cash at Q1 start | ₹1.56 Cr | ₹1.50 Cr |
| Selling price | ₹10,000 | ₹9,999 |
| Manufacturing cost | ₹4,500 | ₹3,250 |
| Gross margin | 55% | 67.5% |
| Fixed cost/quarter | ₹78 L | ₹23.50 L |
| Starting inventory | 1,920 units | 600 units |
| Starting customers | 530 active / 920 registered | 4,000 |
| Base conversion | — | 19% |

**Impact:** every formula in `12`–`16` was calibrated against Nadi Wear. Running them against
PulseWear's seed state will not reproduce any documented result, and the Q1 validation case
cannot be checked.

**Action required:** designer must confirm which company is canonical. If PulseWear, the entire
Q1–Q4 worked-example set must be recalculated.

---

## P0 — Blocking: two incompatible marketing models

> ✅ **RESOLVED** by `docs/17-designer-resolutions.md` — the **power-law model is canonical**;
> the percentage-influence matrix is deprecated. It is kept, not deleted, in
> `app/engines/legacy_matrix/`: it is a genuine second model with its own validation case
> (`15% × 0.9 × 0.6 × 1.0 × 0.8 = 6.48%`), it is not wired into `run_quarter()`, and its module
> docstring says so.

| Model | Source | Shape |
|---|---|---|
| **Percentage-influence matrix** | `05-marketing-workspace.md` | `Decision → +15% Sales`, then × 4 modifiers |
| **Power-law lead formulas** | `12-quarter-1-reference.md` | `Leads = 375 × x^0.68` etc., per channel |

These are not two views of the same thing. The matrix treats a decision as a discrete event with a
percentage effect; the Q1 model treats spend as a continuous input to a lead-count function.
The channel sets also differ (matrix has LinkedIn Ads, event sponsorship, market expansion;
Q1 has Referral cap and Pre-Launch Buzz, which the matrix doesn't).

**Action required:** designer must confirm which model the engine implements. The Q1–Q4 reports
validate only the power-law model.

---

## P1 — Brand Score → multiplier function not stated

> ✅ **RESOLVED** by `docs/17-designer-resolutions.md` — the function **is** stated in source as
> `1 + Brand Score / 50`, which is algebraically identical to the fit below (`1/50 = 0.02`), so
> the implemented coefficient was already correct. The resolutions doc also explains the
> ambiguity: source still contains a superseded `1 + Brand Score / 100` version alongside it.
>
> **Config not yet updated:** `config/profiles/default.json` still carries
> `"status": "fitted_not_confirmed"`. Upgrading that flag to reflect designer confirmation is a
> follow-up, deliberately not bundled into an unrelated phase.

Only three data points exist:

| Brand Score | Multiplier |
|---|---|
| 8.7 | ×1.174 |
| 31.2 | ×1.624 |
| 34.0 | ×1.68 |

**Proposed fit:** `Brand Multiplier = 1 + 0.02 × Brand Score` — reproduces all three exactly
(1.174 / 1.624 / 1.680).

**Status:** implement as proposed but flag; requires designer confirmation. Add a unit test
asserting all three data points.

---

## P1 — Raw conversion has an unstated CX Team term

`docs/00-formula-index.md` states raw conversion as `base + Reps bonus + CRM bonus`. That
composition is exact in Q1 (25.34% vs. an inferred 25.3%) but the ceiling binds in Q1, so the raw
figure never reaches an observable output there -- the composition was never actually tested.

`docs/13-quarter-2-reference.md` §4/§5 states raw conversion for both Q2 variants directly, and
`base + Reps + CRM` alone understates both:

| Variant | `base + Reps + CRM` | Doc's stated raw | Gap |
|---|---|---|---|
| Q2 Efficiency | 26.06% | 28.4% | +2.34 |
| Q2 Growth | 28.81% | 31.2% | +2.39 |

Both gaps match HR's CX Team `Repeat Purchase Rate` bonus (`2 × x^0.4`, `docs/12-quarter-1-reference.md`
§6.3) for the CX spend each variant used (₹1,50,000 in both, held steady per §4/§5's "HR &
Finance/Admin (held steady)" table): `2 × 1.50^0.4 = 2.35` pts, within 0.02-0.04 of both gaps
(28.41% and 31.16% computed vs. 28.4% and 31.2% quoted, both single-decimal roundings). The doc's
own inline aside also names it: "Raw uncapped conversion (**Sales+HR** alone)" -- Sales being
Reps+CRM, HR being CX Team.

**Status:** implemented (`compute_quarter` in `engines/quarter.py`) -- raw conversion now includes
`cx.repeat_rate_pts` in addition to carrying it forward as next quarter's free-repeat-unit rate.
Not stated in `docs/06-product-workspace.md`/`08-customer-experience-workspace.md`, so flagged
here rather than folded into `00-formula-index.md` as confirmed. Reproduces both Q2 variants to
within source-document rounding; the Q3 baseline (raw 29.3%, first quarter the ceiling doesn't
bind) could not be independently verified because the Q3 baseline's CRM/Onboarding and HR-line
split is not itemised in `docs/14-quarter-3-reference.md` §2, only department totals.

---

## RESOLVED — Q1's opening Repeat Purchase Rate (was P1)

`config/seeds/nadi_wear.json`'s `opening_scores.repeat_purchase_rate_pct` was left `null`, which
`CompanyState.opening` treats as `0`. Harmless in Q1 (free repeat units are `prior rate × prior
units sold`, provably zero with no prior quarter) but it made Q1's *closing* rate — Q2's
*opening* rate — come out at ~8.99% instead of the 19.0% `docs/13-quarter-2-reference.md` §1
states, costing ~56 units in Q2.

**Resolved by back-solving it exactly.** Q1's three contributing lines at their stated §12 spends:

| Line | Formula | Spend | Contribution |
|---|---|---|---|
| Email Marketing | `3 × x^0.5` | ₹1,60,000 | 3.794733 |
| Sales Onboarding | `3 × x^0.4` | ₹1,25,000 | 3.280086 |
| HR CX Team | `2 × x^0.4` | ₹90,000 | 1.917463 |
| | | **Total** | **8.992282** |

`19.0 − 8.992282 = 10.007718` — a 0.0077 residual against a round 10.0%, well inside the
single-decimal rounding the source uses throughout.

**Status:** seeded as `10.0` with a `"status": "derived_from_q2_opening"` flag. This is a
stronger class of inference than the fitted brand multiplier or the CX conversion term — those
fit a curve to data points, this inverts stated arithmetic and lands on a round number — but it
is still not directly stated, hence the flag. `tests/config/test_seeds.py` asserts the
*derivation*, not the constant, so a change to any of the three formulas fails loudly.

With this closed, the persisted Q1→Q2 chain reproduces `docs/13` §4's Efficiency-Final figures:
**872 units** and 107 free repeat units.

---

## P3 — Q2 Growth variant's stated production capacity does not match its own formula

`docs/13-quarter-2-reference.md` §2.5 states the attrition discount applies to "**both** Sales
Capacity and Production Capacity", and §4's Efficiency-Final variant confirms it exactly:
`400 × 1.024^0.7 × 0.929 × 0.794 = 299.99`, the **300** that section quotes. The engine was
applying supplier reliability but not attrition (giving 322.9); fixed in Phase 5.

§5's Growth & Profit variant does not reconcile as cleanly. It quotes **1,315** new effective
units for ₹8,40,000 of Manufacturing at 6.1% attrition and 79.8% reliability:

| Interpretation | Result |
|---|---|
| capacity × attrition × reliability | 1,329.61 |
| capacity × reliability only | 1,415.98 |
| capacity × attrition only | 1,666.18 |
| **§5's stated figure** | **1,315** |

No combination reproduces 1,315 — the closest is the same attrition × reliability reading that
is exact in §4, off here by 14.6 units (1.1%). Since that reading is confirmed exactly by the
other variant and by §2.5's prose, it is the one implemented, and §5's 1,315 is treated as an
arithmetic slip in the source rather than evidence of a different rule.

**Not blocking:** in §5's own scenario, supply does not bind (2,044 available against 1,871
demanded), so the discrepancy never reaches units sold. It would matter only in a quarter where
production capacity is the binding constraint.

**Action required:** designer confirms 1,315 is a typo for ~1,330, or states the rule that
produces it.

---

## P2 — Satisfaction Score has no stated baseline (record only; not blocking)

Customer-facing **Satisfaction Score** — built by Sales Onboarding (`+3 × x^0.5`), Operations
Logistics (`+0.05 × Logistics Efficiency`) and HR CX Team (`+4 × x^0.5`), and distinct from
*Employee* Satisfaction, which has a stated baseline of 65 and drives the Productivity
Multiplier — has no stated opening value in any source document.

**Unlike the Repeat Purchase Rate above, it cannot be back-solved:** no later quarter states an
opening value for it, so there is no equation to invert. `docs/12-quarter-1-reference.md` §5.4 and
§6.3 quote only the per-line *contributions* (+3.4, +3.3, +3.8), never a running total.

**Why it is not blocking:** nothing in the 22-line execution chain consumes it. It is an
output-only KPI — the three contributions are computed and reported, but no gate, multiplier or
downstream formula reads the accumulated score. So an absent baseline cannot move `units_sold`,
cash flow or valuation the way the Repeat Purchase Rate gap did.

**Action required:** designer supplies a baseline before Satisfaction Score is surfaced to
students as an absolute number, or before any future formula consumes it. Until then it is
meaningful only as a **delta** (how much this quarter's spend moved it), not as a level.

---

## P1 — Momentum Score entirely unspecified

`16-quarter-4-endgame.md` names seven inputs (Brand, Innovation, Quality, Supplier Reliability,
Repeat Purchase Rate, Cash Balance, Net Cash Flow trend) but gives **no weights, no normalisation,
and no tier cut-offs**.

**Downstream blocked items:**
- Tier assignment (Strong / Flat / Weak)
- Term-sheet menu contents per tier
- Path A covenant threshold formula
- Path B "true continuation value" calculation
- Exit & Growth Judgment trait's 3 sub-criteria

**Action required:** Q4 cannot be implemented at all without this. Highest-priority missing spec
after the P0 items.

---

## P1 — All 12 CX decisions have no formulas

`08-customer-experience-workspace.md` lists each decision's logic as an *engine name* (Retention
Engine, Referral Engine, Crisis Engine, Loyalty Engine, Trust Engine, Reputation Engine, Adoption
Engine, Engagement Engine, Customer Value Engine) — **none of which are specified anywhere in the
source set.**

The CX ratio definitions (CSAT, NPS, churn, etc.) tell you how to compute a KPI *from counts*, but
nothing specifies how a CX decision changes those counts.

**Affected keys:** `CX-001` through `CX-012` — all of them.

**Action required:** every CX decision key raises `NotImplementedError("CX engine formulas not
specified in source documents")`.

---

## P2 — Product workspace formula conflicts and missing coefficients

`06-product-workspace.md` states each formula twice with different terms:

| Variable | §4 version | §5 version |
|---|---|---|
| Product Quality | `Base + QA Investment + R&D Bonus` | `Base + QA + R&D − Technical Debt` |
| Innovation Score | `Previous + R&D Investment` | `R&D + New Features + Technology Adoption` |
| Product Rating | `Customer Satisfaction + Quality + Reliability` | `Customer Experience + Quality + Reliability` |
| Demand | `Brand Awareness + Marketing Impact + Product Quality` | `Market Fit + Brand Awareness + Marketing Impact` |

Neither version specifies coefficients or units — e.g. is `QA Investment` in rupees, lakhs, or a
normalised 0–100 score? Summing a rupee figure to a 0–100 quality score is dimensionally
incoherent.

**Recommendation:** prefer the fully-specified `12-quarter-1-reference.md` § R&D formulas
(`Quality Score += 6 × x^0.5`, etc.), which are dimensionally coherent and validated.

**Also missing:** PRO-008's `Readiness ≥ Threshold` — threshold value not stated. PRO-009 and
PRO-010 are absent entirely (score column sums to 83%, not 100%).

---

## P2 — Negotiation Engine unimplementable

```
Negotiation Score = Price Competitiveness + Relationship + Inventory + Brand + Delivery − Risk
Acceptance Probability = Negotiation Score × Buyer Flexibility × Market Demand
```

**Problems:** six differently-scaled quantities summed with no weights; the result multiplied by
two further unscaled factors; no normalisation to a 0–1 probability range.

**Action required:** `SAL-011` raises `NotImplementedError("Negotiation Score has no specified
weights or scales; Acceptance Probability has no normalisation")`.

---

## P2 — Calibration table conflicts

Three tables appear twice with different values:

| Table | First statement | Second statement |
|---|---|---|
| **Economy** | Boom +12% · Stable 0 · Slowdown −8% · Recession −18% (`09` §15) | Boom +18% · Growth +8% · Stable 0 · Slowdown −10% · Recession −25% (`09` M6) |
| **Creative quality** | Excellent +30% · Good +15% · Weak −20% · Poor −40% (`09` §3) | Excellent +25% · Good +12% · Weak −12% · Poor −25% (`09` M9) |
| **Landing page** | Excellent +35% · Good +20% · Weak −15% · Poor −35% (`09` §4) | Excellent +30% · Good +15% · Weak −15% · Poor −30% (`09` M10) |

**Action required:** designer picks one of each pair.

Also inconsistent: neutral baselines differ across modifier tables — Product Quality (M2) and
Brand Strength (M3) use **70** as neutral, but Customer Satisfaction (M5) uses **60**. May be
intentional; needs confirmation.

---

## P2 — Modifier derivation from company state not specified

`05-marketing-workspace.md` gives the canonical validation case
(`15% × 0.9 × 0.6 × 1.0 × 0.8 = 6.48%`) but the values `0.9 / 0.6 / 1.0 / 0.8` are illustrative
inputs, not outputs of any stated formula.

**Missing:** how Brand Strength, Market Saturation, Inventory Availability, and Competitor Activity
each derive a numeric multiplier from current company state.

**Partial source:** the M1–M13 lookup tables in `09-calibration-engine.md` may be the intended
derivation source, but the mapping from those tables' percentage outputs to multiplicative factors
is not stated.

---

## P2 — Determinism vs. variance design tension

`01-technical-architecture.md` specifies the platform as **deterministic**.
`09-calibration-engine.md` recommends replacing fixed percentages with **base ± variance** ranges
and random selection within them.

**These are incompatible as stated.**

**Recommendation if variance is adopted:** seed the RNG per `(company_id, quarter_id)` so replays
remain reproducible and the platform stays deterministic *from the student's perspective* while
producing quarter-to-quarter variation.

**Action required:** designer decision.

---

## P3 — Finance decisions with named options but no coefficients

| Key | Missing |
|---|---|
| `FIN-004` Cost Optimisation | Reduction % for Mild / Moderate / Aggressive not stated |
| `FIN-013` Vendor Payment Strategy | No coefficients for Pay Early / On Time / Delay |
| `FIN-009` Production Budget Approval | No formula |
| `FIN-010` Inventory Investment | No formula |
| `FIN-011` Dividend / Founder Withdrawal | No formula |
| `FIN-012` Contingency Fund | No formula |
| `FIN-014` R&D Investment Approval | No formula (but `12` § R&D provides a usable substitute) |

`FIN-008` Pricing Approval **is** implementable — coefficients are in `09-calibration-engine.md` § 5.

---

## P3 — Crisis Choice D offset value ambiguity

> ✅ **RESOLVED** by `docs/17-designer-resolutions.md` — **Choice A (Expedite via Air Freight)
> carries `+0.50`**, Choice B `+0.25`, Choice C `+0`. Internally consistent with Choice A's own
> description ("Capacity Penalty Multiplier effect fully reversed"), which only works
> arithmetically if its offset fully cancels the base 0.50 cut. Not yet implemented — the crisis
> engine is Phase 10.

`11-crisis-system.md` states the Strategic Choice offset set for Scenario D as `[0, +0.25, or
+0.50]` but only names Choice B as `+0.25`. **Which choice carries `+0.50` is not stated.**

---

## P3 — Finance scoring weight inconsistency

`04-finance-workspace.md` gives per-decision weight columns (Strategic / Resource / Risk /
Financial Discipline / Long-Term) for FIN-001…007, **and separately** a workspace-level matrix
(Strategic 35% · Resource 30% · Risk 15% · Discipline 10% · Long-Term 10%).

The relationship between the two is not stated — are per-decision weights averaged into the
workspace matrix, or applied independently?

Note also that these five Finance dimensions do **not** match the seven traits in
`10-scoring-methodology.md` (Systems Thinking, Adaptability, and Leadership are absent;
Resource Allocation and Financial Discipline don't appear in the master list). Each workspace
document defines its own scoring dimension set, and none map cleanly onto the master 7-trait
rubric.

**Action required:** designer must confirm whether workspace-level scoring is a separate layer
from the 7-trait cognitive scoring, or whether one derives from the other.

---

## P3 — Operations and People workspaces have no decision spec

Both appear in the quarter flow (`02`) and have formulas in the Q1 reference (`12`), but neither
has a decision-specification document equivalent to Finance/Marketing/Product/Sales/CX.

**Per the standing dead-code discipline:** do not scaffold routers for these workspaces. A router
that always returns 422 is dead code, not a uniform API surface.

---

## Summary — what can be built today

| Component | Buildable now |
|---|---|
| Marketing lead formulas (8 channels) | ✅ Yes |
| Sales capacity + conversion formulas | ✅ Yes |
| R&D Quality/Innovation/Ceiling | ✅ Yes |
| Operations capacity/cost/reliability | ✅ Yes |
| HR satisfaction/engagement/attrition | ✅ Yes |
| Finance/Admin compliance/forecast/audit | ✅ Yes |
| Full execution chain + 3 hard gates | ✅ Yes |
| P&L and valuation | ✅ Yes |
| Crisis engine (all 4 scenarios) | ✅ Yes (one minor offset gap) |
| Scoring engine (7 traits + modifiers) | ✅ Yes |
| Brand multiplier | ⚠️ Proposed fit, needs confirmation |
| CX workspace | ❌ No formulas exist |
| Q4 endgame | ❌ Momentum Score unspecified |
| Percentage-influence matrix model | ❌ Conflicts with power-law model |
| Negotiation engine | ❌ Unimplementable as written |

**Recommended build order:** the Q1 execution chain end-to-end (Marketing → Sales → R&D →
Operations → HR → Finance → P&L), validated against the documented Q1 result
(562 units, −₹31,27,837 NCF, ₹5.25 Cr valuation), before touching anything else.
