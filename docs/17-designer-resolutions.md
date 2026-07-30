# IMPLEMENTATION GAPS REGISTER — RESOLUTIONS
### Answering `10-implementation-gaps.pdf` Item by Item, Verified Against Source Documents

**Method used for every item below:** before writing a resolution, I grepped the actual Nadi Wear source documents (12–16 in your numbering) for the exact formula, ran the cited data points through it, and only wrote "confirmed" where the numbers matched exactly. Where no source document settles the question, that's stated plainly as an open decision — consistent with this register's own standing discipline of visible gaps over guessed numbers. I did not invent any coefficient that wasn't already validated somewhere in the source set.

---

## P0 — Blocking: Two Conflicting Company Baselines (PulseWear vs. Nadi Wear)

**Resolution: Nadi Wear is canonical. This is a recommendation for your sign-off, not a unilateral decision — I have no visibility into `03-pulsewear.md` or why it exists in the source set.**

Reasoning: every formula constant, every worked Q1–Q4 example, and every validated result in documents 12–16 was built and numerically verified against Nadi Wear's economics (₹4.00 Cr raised, ₹9,999 price, ₹3,250 COGS, 67.5% margin). I confirmed this directly — the Q1 validation case (562 units, −₹31,27,837 NCF, ₹5.25 Cr valuation) reproduces exactly against Nadi Wear's numbers when run through the documented formulas.

**Action still required from you:** confirm PulseWear is deprecated/superseded, or state why it exists (an earlier draft? a second product line? a template for a different cohort?). If PulseWear is actually the intended canonical company, everything in 12–16 needs re-deriving from scratch against its economics (₹2.00 Cr raised, ₹4,500 COGS, 55% margin, etc.) — none of the current constants transfer.

---

## P0 — Blocking: Two Incompatible Marketing Models

**Resolution: the power-law model is canonical.** All 8 channel formulas, the Brand/SEO/Buzz mechanics, and every Q1–Q4 lead calculation in the source set use `Leads = Constant × Spend^Exponent`, not the percentage-influence matrix. The channel sets genuinely differ (the matrix's LinkedIn Ads/event sponsorship/market expansion never appear anywhere in the validated formulas; the power-law model's Referral cap and Pre-Launch Buzz never appear in the matrix) — these aren't reconcilable as two views of one system, confirming the register's own read.

**Action still required from you:** confirm `05-marketing-workspace.md`'s matrix model should be archived/deprecated, not merged. If the matrix model represents a *different, later* product decision (e.g., a simplified mode for a different cohort), it should be documented as an alternative engine, not a competing spec for the same one.

---

## P1 — Brand Score → Multiplier Function

**Resolution: CONFIRMED, not merely proposed.** The formula is:
```
Brand Multiplier = 1 + Brand Score / 50
```
This is algebraically identical to the register's proposed fit (`1 + 0.02 × Brand Score`, since `0.02 = 1/50`) — same formula, different notation. I verified it against all three cited data points directly:

| Brand Score | Formula | Result | Register's cited value | Match? |
|---|---|---|---|---|
| 8.7 | 1 + 8.7/50 | 1.174 | ×1.174 | ✓ Exact |
| 31.2 | 1 + 31.2/50 | 1.624 | ×1.624 | ✓ Exact |
| 34.0 | 1 + 34.0/50 | 1.680 | ×1.68 | ✓ Exact |

**One thing worth flagging that likely caused the original ambiguity:** the source documents actually contain *two* versions of this formula at different points — an original `1 + Brand Score/100`, and a later, explicitly-labeled replacement: `1 + Brand Score/50 [was: ×(1 + Brand Score/100) — now TWICE as powerful per point]`. Both versions are still sitting in the source text. **Recommend deleting the deprecated `/100` version from the source documents** so a future reader doesn't hit the same ambiguity you did. No unit test is needed to *discover* the formula — it's already stated — but a regression test asserting all three data points (above) is still good practice to lock it in.

---

## P1 — Momentum Score Entirely Unspecified

**Partially resolved. A validated, working formula exists — but it's narrower than what `16-quarter-4-endgame.md` apparently describes.**

The version that was actually built, tested, and used to produce real Q4 results:
```
Momentum Score = (Q3 Units Sold ÷ Q1 Units Sold)^(1/2) − 1
```
This is a 2-input geometric quarterly growth rate. I confirmed it's fully specified and was successfully used to derive real numbers: a 59.9% momentum score drove a validated Growth Investor covenant (2,556 units) and an Acquisition trap price (₹14,82,56,189 vs. a true continuation value of ₹20,61,89,028) in one worked example, and a 108.8% momentum score drove a second, independently-computed set of offers in a separate full re-run.

**The gap that remains real:** if `16-quarter-4-endgame.md` names seven inputs (Brand, Innovation, Quality, Supplier Reliability, Repeat Purchase Rate, Cash Balance, NCF trend), that's a materially richer momentum concept than the validated 2-input version — nothing in the source set specifies weights for folding those five additional factors in. I'm not going to invent them.

**Recommendation:** adopt the validated 2-input (Units-based) formula as Momentum Score, and treat the other five factors as separate, already-specified inputs to **Tier Assignment** instead (which is a different calculation — see below) rather than trying to cram all seven into one score. This isn't a guess at your intent; it's a description of what's actually implementable today without inventing coefficients.

### Downstream items this unblocks:

| Item | Status |
|---|---|
| Tier Assignment (Strong/Flat/Weak — called Thriving/Stable/Distressed in the validated version) | **Resolved.** `Q3 NCF > 0 AND Valuation grew in both Q2 and Q3` → Thriving. `Buffer breached at any point OR Q3 NCF < 0 with cash declining 2+ consecutive quarters` → Distressed. Everything else → Stable. Fully specified, no missing coefficients. |
| Term-sheet menu contents per tier | **Resolved.** Three distinct menus specified (Thriving: Growth Investor/Acquisition Trap/Independent; Stable: Bridge Financing/Fair-Value Acquisition/Prove Stability; Distressed: Rescue Financing/Fire-Sale/High-Risk Independent). |
| Path A covenant threshold formula | **Resolved.** `Covenant = Prior Units × (1 + 1.3 × Momentum Score)` |
| Path B "true continuation value" formula | **Resolved.** `True Continuation Value = Current Valuation × (1 + Momentum Score)` |
| Exit & Growth Judgment trait's 3 sub-criteria | **Resolved.** (1) Reasoning references the actual Q1-Q3 trend, not just a headline number; (2) chosen path matches what the trajectory supports; (3) consequences are owned in the student's stated reasoning, not attributed to luck. |

---

## P1 — All 12 CX Decisions Have No Formulas

**Confirmed as a real, unresolved gap. No formulas exist anywhere in the source set for Retention Engine, Referral Engine, Crisis Engine, Loyalty Engine, Trust Engine, Reputation Engine, Adoption Engine, Engagement Engine, or Customer Value Engine.**

I am deliberately not proposing substitutes here. Inventing plausible-sounding formulas for nine named-but-unspecified "engines" is exactly the failure mode this register exists to prevent. **Recommend keeping `NotImplementedError("CX engine formulas not specified in source documents")` on CX-001 through CX-012 exactly as the register states**, until a designer writes the actual specs.

---

## P2 — Product Workspace Formula Conflicts and Missing Coefficients

**Resolution: use `12-quarter-1-reference.md`'s R&D formulas, exactly as the register itself already recommends.** I can confirm these are dimensionally coherent and validated — `Quality Score += 6 × x^0.5` and `Innovation Score += 5 × x^0.5` (x = spend in ₹ lakhs) were checked directly against source and reproduce every worked example in the Q1–Q4 documents without alteration.

The §4/§5 duplicate versions in `06-product-workspace.md` (Product Quality, Innovation Score, Product Rating, Demand — each stated twice with different, uncosted terms) should be treated as superseded drafts, not reconciled — there's no principled way to merge "Base + QA Investment + R&D Bonus" with "Base + QA + R&D − Technical Debt" without inventing a Technical Debt coefficient that appears nowhere else.

**Still genuinely unresolved, and I'm not guessing at these:**
- PRO-008's Readiness ≥ Threshold — no threshold value stated anywhere
- PRO-009 and PRO-010 — absent entirely (confirmed: the visible score column only sums to 83%, which is a real, checkable inconsistency, not a rounding artifact)

---

## P2 — Negotiation Engine Unimplementable

**Confirmed correct as stated in the register.** Six differently-scaled quantities summed with no stated weights, multiplied by two further unscaled factors, with no normalization to a 0–1 probability range — there is no responsible way to implement this without inventing every coefficient. **Recommend keeping SAL-011's `NotImplementedError` exactly as specified.**

---

## P2 — Calibration Table Conflicts

**Genuinely unresolved — I have no basis to pick a side, and won't guess.** For all three tables (Economy, Creative Quality, Landing Page), both versions exist in `09-calibration-engine.md` with no dating, versioning, or cross-reference indicating which supersedes which. One observation that might help your review, offered as an observation only, not a resolution: the "second statement" versions in each pair are consistently *more granular or more extreme* (e.g., Economy's second version adds a "Growth +8%" tier the first version lacks, and widens Recession from −18% to −25%) — this pattern is consistent with the second statement being a later revision, but consistent-with is not confirms-as, and I'm flagging the pattern rather than resolving it.

The neutral-baseline inconsistency (70 for Product Quality/Brand Strength vs. 60 for Customer Satisfaction) is also confirmed as-stated — could be intentional (different KPIs plausibly have different "neutral" anchors), but needs your explicit confirmation either way.

---

## P2 — Modifier Derivation From Company State Not Specified

**This gap likely resolves itself as a side effect of the P0 marketing-model decision above.** The missing derivations (Brand Strength, Market Saturation, Inventory Availability, Competitor Activity → numeric multiplier) are only needed if the percentage-influence matrix model is adopted. If the power-law model is confirmed canonical (as recommended above), this entire gap becomes moot — the power-law model doesn't use these four modifiers at all; Brand Score enters through the already-confirmed `1 + Brand Score/50` multiplier instead, and nothing in the validated formula set references Market Saturation, Inventory Availability, or Competitor Activity as multiplicative factors.

**If the matrix model is kept for some other reason,** this gap remains real and unresolved — the M1–M13 lookup tables' mapping to multiplicative factors genuinely isn't stated anywhere I can find.

---

## P2 — Determinism vs. Variance Design Tension

**Not something the source formulas can resolve — this is a platform architecture decision, correctly flagged as outside the Q1–Q4 mechanics.** The register's own suggested resolution (seed the RNG per `(company_id, quarter_id)`) is sound engineering practice for exactly this tension — it preserves reproducible replays while still allowing quarter-to-quarter variation — but I'd note this is a recommendation worth adopting, not something I can "confirm" the way I confirmed a formula against data points. **Needs your sign-off as a technical decision**, not a simulation-design one.

---

## P3 — Finance Decisions With Named Options But No Coefficients

| Key | Status |
|---|---|
| FIN-004 (Cost Optimisation %) | Unresolved — no Mild/Moderate/Aggressive reduction percentages anywhere in source |
| FIN-013 (Vendor Payment Strategy) | Unresolved — no Pay Early/On Time/Delay coefficients |
| FIN-009 (Production Budget Approval) | Unresolved — no formula |
| FIN-010 (Inventory Investment) | Unresolved — no formula |
| FIN-011 (Dividend/Founder Withdrawal) | Unresolved — no formula |
| FIN-012 (Contingency Fund) | Unresolved — no formula |
| **FIN-014 (R&D Investment Approval)** | **Resolved** — `12-quarter-1-reference.md`'s R&D formulas (confirmed above) are a directly usable substitute, exactly as the register notes |
| FIN-008 (Pricing Approval) | Already implementable per the register — coefficients exist in `09-calibration-engine.md` §5, which I don't have visibility into but have no reason to doubt |

I'm not proposing formulas for the six unresolved items. Every other department's formulas in this project (Marketing, Sales, R&D, Ops, HR) follow a consistent square-root-diminishing-returns pattern, and it would be easy to pattern-match new Finance coefficients in that same style — but doing so would be exactly the "guessed formula presented as authoritative" this register exists to prevent. If you want candidate formulas drafted in that consistent style for your review (explicitly labeled as proposals, not validated), I can do that as a separate, clearly-flagged exercise — but I won't fold invented numbers into this resolutions document as if they were confirmed.

---

## P3 — Crisis Choice D Offset Value Ambiguity

**Resolution: CONFIRMED.** The full offset set for Scenario D (Global Supply Shock) is fully specified in the source material:
```
Strategic Choice offset: +0.50 (Choice A, full) · +0.25 (Choice B) · +0 (Choice C)
```
Choice A ("Expedite via Air Freight") carries the +0.50 offset — this is stated explicitly and is internally consistent with Choice A's own separate description elsewhere in the same document ("Capacity Penalty Multiplier effect fully reversed — 100% capacity retained"), which only makes arithmetic sense if its offset is +0.50 (fully canceling the base 0.50 cut). This isn't a gap; it was likely just missed in the extraction that produced the register, since it's stated on the same line as Choice B's offset rather than in a separate callout.

---

## P3 — Finance Scoring Weight Inconsistency

**Both parts of this question were already worked through directly with you; consolidating the resolution here:**

**Part 1 — per-decision weights vs. workspace matrix:** these should be **applied independently, not averaged.** The per-decision columns (FIN-001…007) score how well each individual decision was executed; the workspace-level matrix (35/30/15/10/10) scores how much each dimension matters for Finance as a whole. Averaging the first into the second silently assumes every FIN-item is equally representative of, say, "Strategic" — usually false. The defensible approach is a weighted composite: each FIN-item's per-dimension score weighted by (a) that item's own importance and (b) the workspace matrix's dimension weight — a genuine two-factor weighting, not a straight average. **This is a design recommendation for your confirmation, not a value that was already specified anywhere** — the register is correct that the relationship is unstated in the source.

**Part 2 — five Finance dimensions vs. seven master traits:** these are **two different layers, not one derived from the other.** Workspace-level facts (Strategic/Resource/Risk/Discipline/Long-Term scores per department) function as **evidence** that feeds the reasoning behind the master 7-trait judgment scores — they are not mathematically rolled up into them. Concretely: a department-level fact like "Referral spend matched its cap exactly" is a checkable execution fact; whether that fact demonstrates good "Capital Allocation" (one of the master 7 traits) is a separate, interpretive judgment about what that fact reveals, not a formula applied to it. This is exactly why the standalone scoring methodology keeps trait subtotals and modifiers as two separately-summed numbers rather than blending workspace precision into trait weights. **Recommend documenting this explicitly as a 3-layer model (Execution Facts → Trait Judgment → Modifiers) in the master scoring spec**, so future workspace documents don't each invent their own dimension set expecting it to roll up automatically.

---

## P3 — Operations and People Workspaces Have No Decision Spec

**Confirmed as stated — and confirmed fixable.** The underlying formulas for both exist and are fully validated (Operations: capacity/cost/reliability formulas; HR/People: satisfaction/engagement/attrition formulas — both already listed correctly as ✅ Buildable in the register's own summary table). What's actually missing is a decision-catalog *document* in the same format as Finance/Marketing/Product/Sales/CX (i.e., an "OPS-001…00N" / "PPL-001…00N" style spec), not the underlying math.

**Agree fully with the register's own recommendation: do not scaffold routers that would always 422.** That's dead code. If you want, I can author the missing decision-spec documents for Operations and People using the already-validated formulas as their content — that would be additive documentation, not new invented mechanics, since every number in it already exists and is tested.

---

## Updated Summary — What Can Be Built Today

| Component | Status | Change from register |
|---|---|---|
| Marketing lead formulas (8 channels) | ✅ Yes | unchanged |
| Sales capacity + conversion formulas | ✅ Yes | unchanged |
| R&D Quality/Innovation/Ceiling | ✅ Yes | unchanged |
| Operations capacity/cost/reliability | ✅ Yes | unchanged |
| HR satisfaction/engagement/attrition | ✅ Yes | unchanged |
| Finance/Admin compliance/forecast/audit | ✅ Yes | unchanged |
| Full execution chain + 3 hard gates | ✅ Yes | unchanged |
| P&L and valuation | ✅ Yes | unchanged |
| Crisis engine (all 4 scenarios) | ✅ Yes, **fully** | Choice D ambiguity resolved — no remaining gap |
| Scoring engine (7 traits + modifiers) | ✅ Yes | unchanged |
| **Brand multiplier** | ✅ **Yes — confirmed, not proposed** | upgraded from ⚠ Proposed |
| **Momentum Score (2-input, Units-based) + Tier Assignment + Term Sheet formulas** | ✅ **Yes, for the validated scope** | upgraded from ❌ Unspecified |
| CX workspace | ❌ No formulas exist | unchanged — correctly held open |
| Percentage-influence matrix model | ❌ Deprecated (recommend) in favor of power-law | resolved via recommendation |
| Negotiation engine | ❌ Unimplementable as written | unchanged — correctly held open |
| Finance FIN-004/009/010/011/012/013 | ❌ No coefficients | unchanged — correctly held open |
| Product PRO-008/009/010 | ❌ Threshold/formulas missing | unchanged — correctly held open |
| Calibration table conflicts (3 tables) | ❌ Designer must pick one of each pair | unchanged — pattern noted, not resolved |
| Company baseline (PulseWear vs. Nadi Wear) | ⚠ Recommend Nadi Wear | needs your sign-off |

**Recommended build order, unchanged from the register's own conclusion:** the Q1 execution chain end-to-end, validated against the documented Q1 result (562 units, −₹31,27,837 NCF, ₹5.25 Cr valuation) — which I independently re-confirmed against source in the course of writing this document, not just taken on faith from the register.
