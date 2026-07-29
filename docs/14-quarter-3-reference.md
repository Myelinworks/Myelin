# Quarter 3 Reference — Crisis Quarter

> Source: `q3.pdf` (Nadi Wear Pvt. Ltd. — Q3 Complete Quarterly Report)

Q3 is where the **crisis system activates**. All 4 crisis variants branch from a shared baseline
allocation. Every branch is documented here in full.

---

## 1. Starting position (carried from Q2 Growth & Profit endpoint)

| Metric | Value |
|---|---|
| Cash Balance | ₹1,41,25,594 |
| Fixed Costs (Q3) | ₹22,67,393 |
| Working Capital Buffer | ₹10,00,000 |
| Existing Customers | 6,433 |
| Brand Score | 31.2 |
| Repeat Purchase Rate | 31.2% |
| Quality Score / Innovation Score | 24.65 / 17.5 (before Q3 R&D spend) |
| Supplier Reliability | 79.8 (before Q3 Ops spend) |
| Attrition Rate (bites this quarter) | 6.1% |

### Balance sheet — start of Q3

| Assets | Value |
|---|---|
| Cash | ₹1,41,25,594 |
| Inventory (173 units, prior cost basis) | ₹5,15,921 |
| Equipment & Tooling (net book value) | ₹20,00,000 |
| Product IP / Capitalised Dev Cost | ₹8,00,000 |
| Accounts Receivable | ₹10,00,000 |
| **Total Assets** | **₹1,84,41,515** |
| Liabilities (vendor payables) | ₹12,00,000 |
| **Net Worth** | **₹1,72,41,515** |

---

## 2. Baseline allocation (shared across all 4 crisis branches)

| Department | Spend | Key Result |
|---|---|---|
| Marketing (8 lines) | ₹18,85,980 | Raw Leads = 3,601 |
| Sales | ₹10,00,000 | Capacity = 2,817 (after 6.1% attrition) |
| R&D | ₹6,00,000 | Ceiling = 29.6%, Innovation Score → 25.4 |
| Operations | ₹14,50,000 | Available to Sell = 2,102, Cost/Unit = ₹2,938 |
| HR | ₹5,00,000 | Productivity Multiplier ≈ 1.106 |
| Finance/Admin | ₹4,50,000 | Maintains compliance discipline |
| **Baseline Total** | **₹58,85,980** | |

### Baseline full calculation chain

```
Raw Leads = 3,601 (all 7 Marketing channels + SEO/Buzz free bonuses)
× Brand Score multiplier (31.2 → ×1.624)     = 5,847
× HR Productivity Multiplier (×1.106)        = 6,467 Effective Leads (before any crisis)

Sales Capacity = 2,817  ← the binding constraint on leads, even before any crisis hits

R&D Ceiling = 29.6%
Raw uncapped conversion = 29.3%
  → R&D has FINALLY caught up to what Sales/Marketing can produce
    (ceiling no longer binds at baseline — first time in the simulation)

Available to Sell = 2,102
```

The baseline then **branches into 4 different outcomes** depending on which crisis hits and how
it's handled.

---

## 3. Consequence A — Price Warrior

### The event

Vantis launches at ₹6,999 — a ₹3,000 undercut — triggering a 25% Demand Dampening and a
−8 point Conversion Penalty.

### Strategic choice

**Choice C (Hold Price) + ₹10,00,000 on Comparison Ads**

Rationale: running the numbers showed Choice A (cutting price) actually *loses* money once the
margin sacrifice on all units is counted. Cutting price to ₹7,999 produces a Net Cash Flow of
−₹15,21,149 — worse than doing nothing. The expert answer here comes from actually running the
numbers, which favoured defending conversion through marketing spend over sacrificing margin on
every unit.

### Calculation

| Step | Calculation | Result |
|---|---|---|
| Demand Dampening | `Raw Leads × 0.75` (before Brand/HR multipliers) | 2,701 raw → 4,853 effective after multipliers |
| Conversion Recovery | `min(8, 2 × 10.0^0.5)` = 6.32 pts clawed back | Net penalty only −1.68 |
| Final Conversion Rate | `29.3% (raw) − 1.68 + 3.0 (warranty)` | **30.60%** |
| Leads Used | `MIN(4,853, Sales Capacity 2,817)` | 2,817 (capacity-bound) |
| Units from funnel | `2,817 × 30.60%` | 862 |
| + Free Repeat Units | `31.2% × 1,871 Q2 units` | +584 |
| **Total Units Sold** | | **1,446** |

### Q3 P&L — Consequence A

```
Revenue  = 1,446 × ₹9,999                              ₹1,44,56,288
COGS     = 1,446 × ₹2,938                               ₹42,49,548
Gross Profit                                           ₹1,02,06,740
− Warranty Cost                                             ₹2,24,634
− Holding Cost (656 units carried)                             ₹98,400
Adjusted Gross Profit                                   ₹98,83,706
− Fixed Costs                                           ₹22,67,393
− Discretionary Spend (₹58,85,980 + ₹10,00,000 crisis) ₹68,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                          +₹7,31,791 — profitable, even under crisis
Cash Balance (end Q3)                                 ₹1,48,57,385
```

### Balance sheet — end of Q3 (A)

| Assets | Value |
|---|---|
| Cash | ₹1,48,57,385 |
| Inventory (656 units × ₹2,938) | ₹19,27,479 |
| Equipment, IP, AR (carried) | ₹38,00,000 |
| Total Assets | ₹2,05,84,864 |
| Liabilities | ₹12,00,000 |
| **Net Worth** | **₹1,93,84,864** |

### KPIs — A

| KPI | Value |
|---|---|
| Units Sold | 1,446 |
| Net Cash Flow | +₹7,31,791 |
| Crisis Penalty Neutralized | 79% (6.32 of 8 conversion points recovered) |
| Valuation | ₹12,95,23,492 |

---

## 4. Consequence B — Marketing Blitz

### The event

Vantis launches at a comparable ₹9,499 with a massive awareness campaign — 40% Demand Dampening
(steepest of any variant) and a mild −3 point Conversion Penalty.

### Strategic choice

**Choice B (Differentiate) + ₹6,00,000 split: ₹1L Price-Match, ₹4L Comparison Ads, ₹1L Retention**

### Calculation

| Step | Calculation | Result |
|---|---|---|
| Demand Dampening | `Raw Leads × 0.60` | Steepest cut |
| Dampening Recovery | `min(1.0, 0.60 + 0.20 × 1.0^0.5)` = 0.80 | 80% of normal demand restored |
| Choice B Qualification | Quality Score 35.9 ≥ 25 → base −3 penalty reduced to −1.2 | |
| Comparison Ads Recovery | `min(1.2, 2 × 4.0^0.5)` = 1.2 — fully recovers the reduced penalty | Net penalty = 0 |
| Final Conversion Rate | `29.3% (raw) + 3.0 (warranty)` | **32.28%** |
| Leads Used | Capacity-bound at 2,817 | |
| **Total Units Sold** | `2,817 × 32.28% + 584 repeat` | **1,493** |

### Q3 P&L — Consequence B

```
Revenue  = 1,493 × ₹9,999                              ₹1,49,28,224
COGS     = 1,493 × ₹2,938                               ₹43,87,634
Gross Profit                                           ₹1,05,40,590
− Warranty Cost                                             ₹2,32,163
− Holding Cost (609 units carried)                             ₹91,350
Adjusted Gross Profit                                  ₹1,02,17,077
− Fixed Costs                                           ₹22,67,393
− Discretionary Spend (₹58,85,980 + ₹6,00,000)         ₹64,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                         +₹14,64,794 — best NCF of the 4
Cash Balance (end Q3)                                 ₹1,55,90,388
```

### Balance sheet — end of Q3 (B)

| Assets | Value |
|---|---|
| Cash | ₹1,55,90,388 |
| Inventory (609 units × ₹2,938) | ₹17,89,382 |
| Equipment, IP, AR (carried) | ₹38,00,000 |
| Total Assets | ₹2,11,79,770 |
| Liabilities | ₹12,00,000 |
| **Net Worth** | **₹1,99,79,770** |

### KPIs — B

| KPI | Value |
|---|---|
| Units Sold | 1,493 |
| Net Cash Flow | +₹14,64,794 |
| Crisis Penalty Neutralized | 100% Conversion Penalty; 80% Demand Dampening |
| Valuation | ₹13,36,20,836 |

---

## 5. Consequence C — Feature Leapfrog

### The event

Vantis launches at ₹10,499 (pricier) with superior specs — 20% Demand Dampening (mildest of the
3 competitor variants), and a −6/−2 double penalty (conversion + Ceiling) **unless Innovation
Score ≥ 20**.

### Strategic choice

**Choice C (Hold Price) + ₹0 extra spend**

The baseline Q3 R&D investment already pushed Innovation Score to 25.4, **clearing the threshold
before the crisis decision even needed to be made.**

### Calculation

| Step | Calculation | Result |
|---|---|---|
| Innovation Score check | 25.4 ≥ 20 → threshold already cleared | |
| Conversion Penalty | auto-reduces −6 → −2; Ceiling Penalty waived entirely | |
| Demand Dampening | `Raw Leads × 0.80` (mildest variant) | |
| Final Conversion Rate | `29.3% (raw, Ceiling not reduced) + 3.0 (warranty) − 2 (remaining penalty)` | **30.28%** |
| Leads Used | Capacity-bound at 2,817 | |
| **Total Units Sold** | `2,817 × 30.28% + 584` | **1,437** |

### Q3 P&L — Consequence C

```
Revenue  = 1,437 × ₹9,999                              ₹1,43,64,867
COGS     = 1,437 × ₹2,938                               ₹42,22,506
Gross Profit                                           ₹1,01,42,361
− Warranty Cost                                             ₹2,23,255
− Holding Cost (665 units carried)                             ₹99,750
Adjusted Gross Profit                                   ₹98,19,356
− Fixed Costs                                           ₹22,67,393
− Discretionary Spend (₹58,85,980 + ₹0)                ₹58,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                         +₹16,67,284 — best NCF of all 4
                                                       achieved with ZERO crisis spending
Cash Balance (end Q3)                                 ₹1,57,92,878
```

### Balance sheet — end of Q3 (C)

| Assets | Value |
|---|---|
| Cash | ₹1,57,92,878 |
| Inventory (665 units × ₹2,938) | ₹19,53,923 |
| Equipment, IP, AR (carried) | ₹38,00,000 |
| Total Assets | ₹2,15,46,801 |
| Liabilities | ₹12,00,000 |
| **Net Worth** | **₹2,03,46,801** |

### KPIs — C

| KPI | Value |
|---|---|
| Units Sold | 1,437 |
| Net Cash Flow | +₹16,67,284 (best of all 4) |
| Crisis Penalty Neutralized | **100%** — entirely by prior-quarter R&D investment, zero this-quarter spend |
| Valuation | ₹12,89,45,243 |

---

## 6. Consequence D — Global Supply Shock

### The event

A global disruption cuts Production Capacity by a base 50%, raises Manufacturing Cost/Unit by
₹500, and drops Logistics Efficiency by 15 points for the quarter.

### Strategic choice

**Choice B (Diversify Suppliers) + ₹2,00,000 on the Emergency Supply Chain Fund**

### Calculation

| Step | Formula | Calculation | Result |
|---|---|---|---|
| Supplier Reliability entering Q3 | `79.8 + 4 × Ops^0.5` | `79.8 + 4 × 3.625^0.5` | ≈84.7 (after Q3 Ops spend) |
| Capacity Penalty Multiplier | `MIN(1.0, MAX(0.10, 0.50 + 0.005×(84.7−50) + 0.25 + 0.10×2.0^0.5))` | `0.50 + 0.174 + 0.25 + 0.141` | **1.00 (capped)** — full capacity retained |
| Available to Sell | Full Production Capacity + inventory, un-penalised | | **2,451** (vs. 1,707 with "do nothing") |
| Manufacturing Cost/Unit | `Base + ₹500 surcharge` | | ₹3,438 |
| Conversion Rate | Unaffected by supply crisis | | 32.28% |
| Leads Used | Capacity-bound at 2,817 | | |
| **Total Units Sold** | `2,817 × 32.28% + 584` | | **1,493** |

### Q3 P&L — Consequence D

```
Revenue  = 1,493 × ₹9,999                              ₹1,49,28,224
COGS     = 1,493 × ₹3,438                               ₹51,34,134
Gross Profit                                             ₹97,94,090
− Warranty Cost                                             ₹2,32,163
− Holding Cost (958 units carried)                          ₹1,43,700
Adjusted Gross Profit                                   ₹94,18,227
− Fixed Costs                                           ₹22,67,393
− Discretionary Spend (₹58,85,980 + ₹2,00,000)         ₹60,85,980
────────────────────────────────────────────────────────────────────
NET CASH FLOW                                          +₹10,66,033
Cash Balance (end Q3)                                 ₹1,51,91,627
Permanent Supplier Reliability gain: 79.8 → 94.7 (+10, forever)
```

### Balance sheet — end of Q3 (D)

| Assets | Value |
|---|---|
| Cash | ₹1,51,91,627 |
| Inventory (958 units × ₹3,438) | ₹32,93,824 |
| Equipment, IP, AR (carried) | ₹38,00,000 |
| Total Assets | ₹2,22,85,451 |
| Liabilities | ₹12,00,000 |
| **Net Worth** | **₹2,10,85,451** |

### KPIs — D

| KPI | Value |
|---|---|
| Units Sold | 1,493 |
| Net Cash Flow | +₹10,66,033 (lowest NCF, but only by trade-off) |
| Crisis Fully Neutralized | Yes — Capacity Multiplier hit the 1.00 cap |
| Valuation | **₹13,38,41,972** (highest of all 4 — largest asset base from biggest carried inventory) |

---

## 7. CEO scoring — all 4 consequences

| Trait (Weight) | A: Price Warrior | B: Marketing Blitz | C: Feature Leapfrog | D: Supply Shock |
|---|---|---|---|---|
| Strategic Thinking (15) | 14 — ran the numbers rather than trusting the textbook answer | 13 — correctly diagnosed an attention problem, not a price one | 12 — recognised prior investment already solved it | 13 — chose the only lastingly-beneficial option |
| Leadership (10) | 9 | 9 | 8 | 9 |
| Adaptability (15) | 13 | 13 | 11 | 12 |
| Systems Thinking (20) | 17 | 18 | 16 | **19** — connected Supplier Reliability history directly to this quarter's outcome |
| Risk Management (15) | 12 | 12 | **13** — didn't overspend on an unnecessary response | 12 |
| Capital Allocation (15) | **13** — ₹10L well-targeted at the actual constraint | 13 | **14** — zero unnecessary spend | 12 |
| Long-Term Thinking (10) | 7 | 7 | **8** — trusted a 2-quarter investment to pay off | **9** — the only scenario with a permanent asset gained |
| **Subtotal** | **85** | **85** | **82** | **86** |

### Crisis modifiers

| Modifier | A | B | C | D |
|---|---|---|---|---|
| Crisis fully neutralized (+3) | No | Partial (+1) | **Yes (+3)** | **Yes (+3)** |
| Crisis-proofed by prior investment (+3) | No | No | **Yes (+3)** | **Yes (+3)** |
| Structural improvement made (+2) | No | No | No | **Yes (+2)** |
| Crisis ignored (−4) | No | No | No | No |
| **Net Modifier** | **0** | **+1** | **+6** | **+8** |

### Final scores

| Variant | Score | Band |
|---|---|---|
| A: Price Warrior | 85 + 0 = **85** | Strong |
| B: Marketing Blitz | 85 + 1 = **86** | Strong |
| C: Feature Leapfrog | 82 + 6 = **88** | Strong (near-Exceptional) |
| D: Supply Shock | 86 + 8 = **94** | **EXCEPTIONAL** |

**Why D scored highest:** it's the only one of the four where the expert response created a
**permanent, compounding asset** (Supplier Reliability +10 forever) on top of fully neutralising
this quarter's shock — satisfying both major modifier categories simultaneously.

**Why C came remarkably close despite zero crisis spending:** the scoring methodology rewards
systems thinking and long-term thinking as much as active crisis management. A team that built R&D
early enough that a crisis simply doesn't land is demonstrating the deepest form of good CEO
judgment — even though there's nothing dramatic to point to in Q3 itself.

---

## 8. Master summary — all 4 consequences side by side

| Metric | A: Price Warrior | B: Marketing Blitz | C: Feature Leapfrog | D: Supply Shock |
|---|---|---|---|---|
| Units Sold | 1,446 | 1,493 | 1,437 | 1,493 |
| Revenue | ₹1,44,56,288 | ₹1,49,28,224 | ₹1,43,64,867 | ₹1,49,28,224 |
| Net Cash Flow | +₹7,31,791 | +₹14,64,794 | **+₹16,67,284** | +₹10,66,033 |
| Cash Balance | ₹1,48,57,385 | ₹1,55,90,388 | ₹1,57,92,878 | ₹1,51,91,627 |
| Net Worth | ₹1,93,84,864 | ₹1,99,79,770 | ₹2,03,46,801 | **₹2,10,85,451** |
| Valuation | ₹12,95,23,492 | ₹13,36,20,836 | ₹12,89,45,243 | **₹13,38,41,972** |
| CEO Score | 85 | 86 | 88 | **94** |

**The finding that ties the whole quarter together:** every single one of the 4 possible
consequences ended Q3 profitable and with growing Net Worth — proving that the Q1–Q2 foundation
(Brand Score 31.2, Quality Score 35.9, Innovation Score 25.4, Supplier Reliability 79.8) was
strong enough to absorb any single severe shock thrown at it. The differences between scenarios
aren't about survival — they're entirely about how much upside a well-prepared company can still
capture while a crisis is happening.
