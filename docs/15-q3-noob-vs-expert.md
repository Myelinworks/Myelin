# Q3 — Novice vs. Expert Calibration Pairs

> Source: `noob_vs_expert_q3.pdf`

Eight complete Q3 runs — a **novice** and an **expert** response to each of the 4 crisis
scenarios — all branching from the **identical shared baseline**. This is the calibration data
set for the scoring engine: it establishes the realistic score spread the engine must be able to
produce across a cohort.

---

## The shared baseline (identical for all 8 runs)

| Item | Value |
|---|---|
| Baseline discretionary allocation | ₹58,85,980 |
| Cash Balance (start) | ₹1,41,25,594 |
| Fixed Costs (Q3) | ₹22,67,393 |
| Brand Score | 31.2 (→ lead multiplier ×1.624) |
| Sales Capacity | 2,817 (after 6.1% attrition) |
| R&D Ceiling at baseline | 29.6% |
| Raw uncapped conversion | 29.3% |
| Available to Sell | 2,102 |
| Free Repeat Units | 584 (`31.2% × 1,871`) |
| Warranty | 2-year (+3.0 conversion points) |
| Quality Score / Innovation Score | 35.9 / 25.4 (after baseline Q3 R&D) |
| Supplier Reliability | 84.7 (after baseline Q3 Ops) |

**Only the crisis response differs between each pair.** Every other number is held constant, which
is what makes the score gap purely attributable to crisis-handling skill.

---

## Scenario A — Price Warrior

### Novice response

**Choice A (Cut Price to ₹7,999) + ₹2,00,000 on Retention Offers**

The instinctive answer: a competitor undercuts on price, so match them. The novice never runs the
margin math.

| Step | Calculation | Result |
|---|---|---|
| Conversion Penalty | Removed entirely by Choice A | 0 |
| Gross Margin | Falls 67.5% → ~55% | Margin/unit ₹4,900 (from ₹6,749) |
| Demand Dampening | `× 0.75`, no Price-Match Fund spend | 4,853 effective leads |
| Retention Offers | `MAX(0%, 8% − 1.5 × 2.0^0.5)` = 5.88% churn | ~378 customers lost |
| Final Conversion Rate | `29.3% + 3.0 warranty` | 32.28% |
| Leads Used | `MIN(4,853, 2,817)` | 2,817 |
| Units Sold | `2,817 × 32.28% + 584` | **1,493** |

```
Revenue = 1,493 × ₹7,999                                ₹1,19,42,507
COGS    = 1,493 × ₹2,938                                  ₹43,87,634
Gross Profit                                              ₹75,54,873
− Warranty + Holding                                       ₹3,23,513
− Fixed Costs                                             ₹22,67,393
− Discretionary (₹58,85,980 + ₹2,00,000)                  ₹60,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                            −₹11,22,013 ← LOSS
```

**Why it fails:** the price cut sacrifices ~₹2,000/unit of margin across *all* 1,493 units
(≈₹29.9L of margin destroyed) to remove an 8-point conversion penalty that could have been
recovered for ₹10L of Comparison Ads. **The novice paid three times the price for the same fix.**

### Expert response

**Choice C (Hold Price) + ₹10,00,000 on Comparison Ads** — as documented in `14-quarter-3-reference.md` § Consequence A.

```
Units Sold: 1,446 · Net Cash Flow: +₹7,31,791 · CEO Score: 85
```

### The pair

| | Novice | Expert | Delta |
|---|---|---|---|
| Units Sold | 1,493 | 1,446 | −47 |
| Revenue | ₹1,19,42,507 | ₹1,44,56,288 | **+₹25,13,781** |
| Net Cash Flow | −₹11,22,013 | +₹7,31,791 | **+₹18,53,804** |
| CEO Score | **58** | **85** | **+27** |

**The lesson:** selling *more* units at a worse price produced *less* money. This is the clearest
demonstration in the whole simulation that volume is not the objective — margin-weighted volume is.

---

## Scenario B — Marketing Blitz

### Novice response

**Choice A (Cut Price) + ₹1,00,000 on Comparison Ads**

The novice applies the same reflex learned from Scenario A's framing — cut price — to a crisis
that isn't about price at all.

| Step | Calculation | Result |
|---|---|---|
| Conversion Penalty | Only −3 to begin with; Choice A removes it | Recovers almost nothing |
| Margin sacrificed | ~₹1,850/unit across all units | Large cost for a small fix |
| Demand Dampening | `× 0.60`, no recovery spend | **The dominant, unaddressed penalty** |
| Effective Leads | Heavily suppressed | ~3,508 |
| Units Sold | Still capacity-bound at 2,817 | **1,493** |

```
Revenue = 1,493 × ₹8,149 (post-cut)                     ₹1,21,66,457
NET CASH FLOW                                            −₹9,45,220 ← LOSS
```

**Why it fails:** the novice spent margin to fix a −3 penalty while ignoring a 40% demand cut —
the steepest dampening of any scenario. **Right instinct, wrong crisis.**

### Expert response

**Choice B (Differentiate) + ₹6,00,000 split across Price-Match / Comparison Ads / Retention** —
as documented in `14-quarter-3-reference.md` § Consequence B.

```
Units Sold: 1,493 · Net Cash Flow: +₹14,64,794 · CEO Score: 86
```

### The pair

| | Novice | Expert | Delta |
|---|---|---|---|
| Units Sold | 1,493 | 1,493 | 0 |
| Net Cash Flow | −₹9,45,220 | +₹14,64,794 | **+₹24,10,014** |
| CEO Score | **55** | **86** | **+31** — the widest gap of the 4 pairs |

**Why this pair has the widest score gap:** both runs sold the identical number of units. The
entire ₹24L difference came from *how* those units were sold — the novice's price cut destroyed
margin on every one of them while leaving the actual problem untouched. It is the purest possible
isolation of decision quality from outcome volume.

---

## Scenario C — Feature Leapfrog

### Novice response

**Choice A (Cut Price) + ₹0 additional spend**

The novice doesn't check the Innovation Score threshold, doesn't realise the crisis is already
neutralised, and cuts price out of panic.

| Step | Result |
|---|---|
| Innovation Score 25.4 ≥ 20 | Threshold already cleared — penalty was *already* only −2 |
| Choice A | Sacrifices margin to fix a penalty that was already minimal |
| Demand Dampening | `× 0.80` (mildest variant), unaddressed |
| Units Sold | **1,437** |

```
NET CASH FLOW                                            −₹4,18,662 ← LOSS
```

**Why it fails:** the crisis had *already been won* two quarters earlier by R&D investment. The
novice paid a real margin cost to solve a problem that no longer existed. **The most avoidable
loss of the eight runs.**

### Expert response

**Choice C (Hold Price) + ₹0 additional spend** — as documented in `14-quarter-3-reference.md`
§ Consequence C.

```
Units Sold: 1,437 · Net Cash Flow: +₹16,67,284 · CEO Score: 88
```

### The pair

| | Novice | Expert | Delta |
|---|---|---|---|
| Units Sold | 1,437 | 1,437 | 0 |
| Net Cash Flow | −₹4,18,662 | +₹16,67,284 | **+₹20,85,946** |
| Crisis spend | ₹0 | ₹0 | 0 |
| CEO Score | **61** | **88** | **+27** |

**The lesson:** both players spent exactly ₹0 responding to the crisis. The entire ₹20.9L
difference came from a single decision — whether to cut price — made with or without checking one
number. **Diagnosis, not spending, was the whole game here.**

---

## Scenario D — Global Supply Shock

### Novice response

**Choice A (Absorb the shock) + ₹0 on the Emergency Supply Chain Fund**

| Step | Calculation | Result |
|---|---|---|
| Capacity Penalty Multiplier | `MIN(1.0, MAX(0.10, 0.50 + 0.005×(84.7−50) + 0 + 0))` | `0.50 + 0.174` = **0.674** |
| Available to Sell | Production capacity × 0.674 + inventory | **1,707** (vs. 2,451 expert) |
| Manufacturing Cost/Unit | Base + ₹500 surcharge | ₹3,438 |
| Demand available | 2,817 × 32.28% + 584 = 1,493 | |
| **Units Sold** | `MIN(1,493 demand, 1,707 supply)` | **1,493** — supply gate did NOT bind |

```
Revenue = 1,493 × ₹9,999                                ₹1,49,28,224
COGS    = 1,493 × ₹3,438                                  ₹51,34,134
Gross Profit                                              ₹97,94,090
− Warranty + Holding (214 units)                           ₹2,64,263
− Fixed Costs                                             ₹22,67,393
− Discretionary (₹58,85,980 + ₹0)                         ₹58,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                            +₹13,76,454 ← STILL PROFITABLE
```

**Why the novice got away with it here — the single most instructive result in the set:** the
company's Supplier Reliability of 84.7, built across Q1 and Q2, contributed a +0.174 offset that
kept the multiplier at 0.674 rather than the 0.50 base. That was enough capacity (1,707) to cover
the 1,493 units demanded. **Two quarters of unglamorous supplier investment silently absorbed a
"severe" crisis for a player who did nothing at all.**

But the novice gains **no permanent Supplier Reliability improvement**, carries only 214 units of
inventory, and — critically — got lucky that demand happened to sit below the reduced supply
ceiling. Had Marketing generated more leads, or Sales Capacity been higher, the 1,707 gate would
have bound hard and cost real revenue.

### Expert response

**Choice B (Diversify Suppliers) + ₹2,00,000 Emergency Fund** — as documented in
`14-quarter-3-reference.md` § Consequence D.

```
Units Sold: 1,493 · Net Cash Flow: +₹10,66,033 · CEO Score: 94
Permanent Supplier Reliability gain: +10, forever
```

### The pair — the one where the novice out-earns the expert

| | Novice | Expert | Delta |
|---|---|---|---|
| Units Sold | 1,493 | 1,493 | 0 |
| Net Cash Flow | **+₹13,76,454** | +₹10,66,033 | **−₹3,10,421** |
| Available to Sell | 1,707 | 2,451 | +744 |
| Inventory carried | 214 units | 958 units | +744 |
| Permanent Reliability gain | **None** | **+10 forever** | |
| CEO Score | **68** | **94** | **+26** |

**Why the expert scored 26 points higher despite earning ₹3.1L less this quarter:** the expert
spent ₹2,00,000 buying a permanent +10 Supplier Reliability improvement and 744 additional units
of production capacity. The novice banked the ₹2L this quarter and got nothing durable. **The
scoring methodology deliberately rewards the trade — this is the clearest case in the entire
simulation where Net Cash Flow and CEO Score diverge, and it is by design.**

This pair is the strongest single argument for scoring decision quality separately from financial
outcome. A scoring system that simply ranked by cash would have called the novice the better CEO.

---

## Master calibration table — all 8 runs

| Scenario | | Units | Net Cash Flow | CEO Score | Band |
|---|---|---|---|---|---|
| A: Price Warrior | Novice | 1,493 | −₹11,22,013 | **58** | Weak |
| A: Price Warrior | Expert | 1,446 | +₹7,31,791 | **85** | Strong |
| B: Marketing Blitz | Novice | 1,493 | −₹9,45,220 | **55** | Weak |
| B: Marketing Blitz | Expert | 1,493 | +₹14,64,794 | **86** | Strong |
| C: Feature Leapfrog | Novice | 1,437 | −₹4,18,662 | **61** | Competent |
| C: Feature Leapfrog | Expert | 1,437 | +₹16,67,284 | **88** | Strong |
| D: Supply Shock | Novice | 1,493 | +₹13,76,454 | **68** | Competent |
| D: Supply Shock | Expert | 1,493 | +₹10,66,033 | **94** | **Exceptional** |

### Calibration properties the engine must reproduce

| Property | Evidence |
|---|---|
| **Score spread** | 55–94, a 39-point range across identical starting conditions |
| **Novice band** | 55–68 (Weak → Competent) |
| **Expert band** | 85–94 (Strong → Exceptional) |
| **Consistent gap** | +26 to +31 points, expert over novice, in every pair |
| **Score ≠ cash** | Scenario D: novice earns more cash, scores 26 points lower |
| **Units ≠ score** | Scenarios B, C, D: identical units sold, ~30-point score gap |

### The three novice failure modes the engine should be able to detect

1. **Reflexive price-cutting** (A, B, C) — reaching for the price lever regardless of whether price is the actual problem. Present in 3 of the 4 novice runs.
2. **Failure to diagnose before acting** (C) — not checking whether the crisis threshold had already been cleared by prior investment.
3. **Banking short-term cash over durable assets** (D) — declining a ₹2,00,000 spend that buys a permanent capability, because this quarter's number looks better without it.

### The overarching finding

> Across all eight runs, the crisis never determined the outcome. What determined the outcome was
> whether the player correctly diagnosed **which** problem they actually had — and in Scenario D,
> whether they were willing to accept a slightly worse quarter to build something permanent. The
> spread between a 55 and a 94 came almost entirely from diagnosis quality, not from spending
> capacity: three of the four expert runs cost ₹10,00,000 or less in crisis response, and one cost
> nothing at all.
