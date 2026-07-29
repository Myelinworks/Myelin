# Implementation Gaps Register

> Derived. **Every item here must raise `NotImplementedError` with the stated reason, or be
> resolved by the simulation designer before implementation.**

Standing discipline for this project: *no guessed formulas presented as authoritative; visible
gaps preferred over silently wrong numbers.*

---

## P0 — Blocking: two conflicting company baselines

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
