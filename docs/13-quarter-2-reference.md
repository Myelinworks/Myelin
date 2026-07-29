# Quarter 2 Reference — Compounding & Carryover Mechanics

> Source: `Q2_COMPLETE_REPORT.pdf`

Q2 is where **compounding first activates**. The source contains **two complete Q2 variants** run
against the same starting position, which together define the compounding model.

| Variant | Discretionary Spend | Units Sold | Net Cash Flow | CEO Score |
|---|---|---|---|---|
| **Efficiency-Final** | ₹42,73,200 | 872 | −₹7,79,603 | 82/100 |
| **Growth & Profit** | ₹82,63,600 | 1,871 | **+₹22,53,431** | 84/100 |

---

## 1. Starting position (identical for both variants)

| Metric | Value | What it means for Q2 |
|---|---|---|
| Cash Balance | ₹1,18,72,163 | Starting point for the ceiling |
| Fixed Costs (Q2) | ₹23,17,805 | Down from ₹23,50,000 — Q1's Forecast Accuracy bonus |
| Working Capital Buffer | ₹10,00,000 | Still protected |
| **Q2 Discretionary Ceiling** | **₹85,54,358** | `₹1,18,72,163 − ₹23,17,805 − ₹10,00,000` |
| Existing Customers | 4,562 | `4,000 + 562 sold in Q1` → Referral cap rises to `0.20 × 4,562 = 912` |
| Finished Goods Inventory | 729 units | Nearly covers Q2's demand on its own |
| Brand Score | 8.7 | **First quarter it actually multiplies leads (×1.174)** |
| SEO Asset | 4.5 | Pays out `4.5 × 25 = 113` free leads |
| Pre-Launch Buzz | 5.5 | Pays out `5.5 × 15 = 83` free leads (partial; full payoff Q3) |
| Repeat Purchase Rate | 19.0% | Generates `19.0% × 562 = 107` free units, no lead cost |
| Quality / Innovation Score | 9.95 / 7.5 | R&D Ceiling starts at 19.1% before any Q2 spend |
| Attrition Rate | 7.1% | **The one that bites in Q2** — discounts whatever capacity Q2 builds |
| Employee Satisfaction / Engagement | 70.5 / 65.7 | Starting points for HR multiplier and attrition |

> **Key structural point:** Q2 doesn't start from zero. Higher expected demand
> (Brand/SEO/Buzz/Repeat all pushing up) collides with a real headwind (attrition eroding capacity)
> for the first time.

---

## 2. New compounding mechanics activated in Q2

### 2.1 Brand Score as a lead multiplier

```
Brand Multiplier applied to (raw channel leads + free bonuses)
Brand Score 8.7  → ×1.174
Brand Score 31.2 → ×1.624    (Q3)
Brand Score 34.0 → ×1.68     (Q4)
```

> ⚠️ **Gap:** the *function* converting Brand Score → multiplier is **not stated**, only three
> data points. Fitting them: 8.7→1.174, 31.2→1.624, 34.0→1.68 suggests roughly
> `1 + Brand Score × 0.02`, which gives 1.174 / 1.624 / 1.680 — an exact match.
> **Proposed formula: `Brand Multiplier = 1 + 0.02 × Brand Score`.** This must be confirmed by the
> simulation designer before implementation. Tracked in `10-implementation-gaps.md`.

### 2.2 SEO Asset payout

```
Free leads this quarter = prior quarter's SEO Asset × 25
```
Q1's 4.5 → 113 free leads in Q2.

### 2.3 Pre-Launch Buzz payout

```
Q+1: Free leads = Buzz Score × 15
Q+2: Free leads = Buzz Score × 25, plus one-time Conversion bonus = Buzz Score × 0.3 points
```
Q1's 5.5 → 83 free leads in Q2.

### 2.4 Repeat purchase units (free, no lead cost)

```
Free repeat units = prior quarter Repeat Purchase Rate × prior quarter Units Sold
```
Q2: `19.0% × 562 = 107 units`.
Q3: `31.2% × 1,871 = 584 units`.

### 2.5 Attrition discount on capacity

```
Effective Capacity = Capacity formula result × (1 − prior quarter Attrition Rate)
```

| Quarter | Attrition (from prior Q) | Multiplier applied |
|---|---|---|
| Q2 | 7.1% | ×0.929 |
| Q3 | 6.1% | ×0.939 |

Applies to **both** Sales Capacity (`500 × x`) and Production Capacity (`400 × x^0.7`).

### 2.6 Fixed cost reduction chain

```
Next quarter Fixed Costs = this quarter Fixed Costs × (1 − Cash Efficiency Bonus)
Cash Efficiency Bonus    = (Forecast Accuracy − 50) × 0.1%
```

| Quarter | Forecast Accuracy | Bonus | Resulting next-Q Fixed Costs |
|---|---|---|---|
| Q1 | 63.7 | 1.37% | ₹23,17,805 |
| Q2 (Efficiency) | 71.7 | 2.17% | ₹22,67,393 |

---

## 3. The diagnostic test — why Q1's allocation could not simply be repeated

Before deciding Q2's numbers, Q2 was run **once with Q1's exact allocation unchanged**, purely to
isolate the effect of compounding from the effect of decision-making.

### What the test revealed

| Problem found | Evidence | Why it happened |
|---|---|---|
| **Sales Capacity became a severe bottleneck** | Effective Leads reached 3,776 (from Brand+SEO+Buzz+HR compounding), but Sales Capacity — the same ₹5,45,000 Reps spend as Q1 — only produced 2,725, and Attrition (7.1%) discounted it further to **2,532**. **1,244 leads (a third of all demand) were wasted.** | The business had structurally changed underneath an unchanged decision — Marketing's own compounding assets generated more demand than Q1's capacity plan anticipated |
| **R&D's Conversion Ceiling still bound tightly** | Raw achievable conversion was 27.4%, but the Ceiling (same R&D spend as Q1) only allowed 23.2% + 1.5% warranty = 24.7% — a persistent 2.7pt gap | Cumulative Quality/Innovation Score grows **slower** than Marketing/Sales' raw conversion potential grows, at equal repeated spend |

**Naive-repeat result:** 733 units, −₹19,22,012 NCF — proving compounding works even with zero new
decisions, but also that a third of demand was being thrown away.

---

## 4. Variant A — Efficiency-Final (₹42,73,200)

### Department split and reasoning

| Department | Q1 | Q2 | Why |
|---|---|---|---|
| Marketing | ₹16,00,000 | **₹11,50,000 ↓** | Google/Meta slashed — their only value (raw lead volume) was exactly what was being wasted at the Sales gate. Brand/SEO/Email/Referral, whose value doesn't depend on lead volume being usable, kept or increased |
| Sales | ₹8,00,000 | **₹10,45,800 ↑** | Reps raised just enough to build capacity (3,000) slightly above the leads Marketing now generates (2,834) — sized precisely, not maximally |
| R&D | ₹5,00,000 | **₹7,00,000 ↑** | Diagnostic showed the Ceiling still binding |
| Operations | ₹6,00,000 | **₹3,27,400 ↓** | The 729 units already in inventory cover most of Q2's demand — building large new capacity on top was pure waste |
| HR | ₹3,00,000 | **₹5,00,000 ↑** | Training & Development directly fights the Attrition Rate that just cost 1,244 leads |
| Finance/Admin | ₹7,00,000 | **₹5,50,000 ↓** | Compliance risk already well-managed (19.7%) — least urgent this quarter |

> **Central financial lesson: spending less can produce more, if the "less" is specifically the
> part that wasn't buying anything.**

### Marketing channel detail

| Channel | Q1 | Q2 | Calculation | Leads |
|---|---|---|---|---|
| Google Ads | ₹4,00,000 | ₹50,000 | `375 × 0.50^0.68` | 234 |
| Meta Ads | ₹1,92,000 | ₹50,000 | `200 × 0.50^0.65` | 127 |
| Social & Influencer | ₹2,08,000 | ₹2,50,000 ↑ | `225 × 2.50^0.72` | 435 |
| Content/SEO | ₹1,28,000 | ₹1,50,000 ↑ | `75 × 1.50^0.62` | 96 |
| Events/PR | ₹80,000 | ₹80,000 | `90 × 0.80^0.62` | 78 |
| Email Marketing | ₹1,60,000 | ₹1,60,000 | `80 × 1.60^0.55` | 104 |
| Referral | ₹2,40,000 | ₹2,73,600 ↑ | cap = 912, cost = ₹2,73,600 (exact) | 912 |
| Pre-Launch Buzz | ₹1,92,000 | ₹1,36,400 | `4 × 1.364^0.5` | 0 |
| **Raw total** | | | | **1,987** |

```
Raw channel total                          1,987
+ SEO Asset free leads (4.5 × 25)          + 113
+ Pre-Launch Buzz free leads (5.5 × 15)    +  83
Subtotal                                   2,182
× Brand Score multiplier (8.7 → ×1.174)  → 2,562
× HR Productivity Multiplier (×1.106)    → 2,834 Effective Leads
```

New assets built: Brand Score +8.05 → **16.75** · SEO Asset +5.25 → **9.75** · new Buzz Score **4.67**

### Sales — sized precisely, not maximally

A first attempt overshot: raising Reps to ₹12,00,000 built 5,574 capacity against only 2,834 leads —
roughly ₹5–6,00,000 bought capacity that went completely unused.

| Line | Spend | Formula | Calculation | Result |
|---|---|---|---|---|
| Reps & Commissions | ₹6,45,800 | `500 × x × 0.929` | `500 × 6.458 × 0.929` | 3,000 capacity |
| — same spend | | `2 × x^0.5` | `2 × 6.458^0.5` | +5.08 pts |
| CRM Tools | ₹2,00,000 | `1.5 × x^0.4` | `1.5 × 2.00^0.4` | +1.98 pts |
| Onboarding | ₹2,00,000 | `Sat += 3×x^0.5`, `Repeat += 3×x^0.4` | | +4.24 Sat, +3.95 Repeat |

```
Leads Used = MIN(2,834, 3,000) = 2,834  ← zero leads wasted
```

### R&D

| Line | Spend | Calculation | Result |
|---|---|---|---|
| Quality/QA | ₹4,00,000 | `6 × 4.00^0.5` / `8 − 1.2 × 4.00^0.5` | Quality **21.95** (9.95+12.0), Defect **5.6%** |
| Innovation/Feature | ₹3,00,000 | `5 × 3.00^0.5` / `8 × 3.00^0.5` | Innovation **16.16**, Feature +13.86 → 25.86/100 |

```
Conversion Ceiling = 15% + (21.95 + 0.5 × 16.16) × 0.3% = 24.0%
+ Warranty (upgraded to 2-year, justified by lower Defect Rate) = +3.0%
Final Conversion Rate = 27.0%

Raw uncapped conversion (Sales+HR alone) = 28.4%
→ Ceiling STILL binds, but the gap narrowed from 2.7pts (naive repeat) to 1.4pts
```

**Why increasing R&D spend was worth it:** every point the Ceiling gains converts leads that were
**already generated and already paid for** — the highest-leverage rupee in the whole allocation,
since it needs no new leads or capacity, just permission to convert more of what already exists.

### Operations — right-sized, not just cut

| Line | Spend | Calculation | Result |
|---|---|---|---|
| Manufacturing | ₹1,02,400 | `400 × 1.024^0.7 × 0.929` | 300 new capacity, **₹3,159/unit** |
| Supplier & QC | ₹1,25,000 | `74.9 + 4 × 1.25^0.5` | **79.4** |
| Logistics | ₹1,00,000 | `65.5 + 5 × 1.00^0.5` | **70.5** → +3.5 Satisfaction |

```
Available to Sell = 300 + 729 (carried inventory) = 1,029
vs. 872 units actually sold → only 157 units carried into Q3
```

**Why unit cost rose (₹3,087 → ₹3,159):** less Manufacturing spend means fewer economies of scale.
A deliberate trade-off — the savings from not overbuilding capacity vastly outweigh a ₹72/unit
increase on 872 units (₹62,784 total vs. hundreds of thousands saved).

### HR

| Line | Spend | Calculation | Result |
|---|---|---|---|
| Culture & Benefits | ₹1,50,000 | `70.5 + 5 × 1.50^0.5` | Satisfaction **76.6**, Multiplier **1.106** |
| Training & Development | ₹2,00,000 | `65.7 + 6 × 2.00^0.5` | Engagement **74.2**, Attrition **6.1%** (from 7.1%) |
| Customer Experience | ₹1,50,000 | `Sat += 4×x^0.5`, `Repeat += 2×x^0.4` | +4.2 Sat, +2.1 Repeat |

**Note the lag:** Q2's own capacity formulas used Q1's 7.1% attrition. This quarter's improved 6.1%
becomes the number that discounts **Q3's** capacity.

### Finance/Admin

| Line | Spend | Calculation | Result |
|---|---|---|---|
| Compliance & Legal | ₹2,20,000 | `58.4 + 5 × 2.20^0.5` | 65.8 |
| Financial Planning | ₹1,80,000 | `63.7 + 6 × 1.80^0.5` | 71.7 → 2.17% Q3 cost cut |
| Audit Prep | ₹1,50,000 | `57.2 + 5 × 1.50^0.5` | 63.3 |

```
Q3 Fixed Costs = ₹23,17,805 × (1 − 2.17%) = ₹22,67,393
Combined Penalty Risk = max(5%, 40 − 0.25×65.8 − 0.10×63.3) ≈ 17.2%
```

### Efficiency-Final P&L

```
Raw Leads (7 channels)                              1,987
+ Free bonuses (SEO 113, Buzz 83)                   2,182
× Brand multiplier (1.174)                          2,562
× HR multiplier (1.106)                             2,834 Effective Leads
Sales Capacity (right-sized)                        3,000
Leads Used = MIN(2,834, 3,000)                      2,834 — zero waste
Conversion Rate = Ceiling 24.0% + Warranty 3.0%     27.0%
Units from funnel = 2,834 × 27.0%                     766
+ Free repeat units (19.0% × 562)                    +107
TOTAL UNITS SOLD                                      872
Revenue = 872 × ₹9,999                        ₹87,22,397
COGS    = 872 × ₹3,159                        ₹27,55,617
Gross Profit                                  ₹59,66,781
− Warranty Cost (872 × 5.6% × ₹1,500 × 1.8)    ₹1,31,896
− Holding Cost (157 units carried)               ₹23,483
Adjusted Gross Profit                         ₹58,11,402
− Fixed Costs                                 ₹23,17,805
− Discretionary Spend                         ₹42,73,200
────────────────────────────────────────────────────────
NET CASH FLOW                                 −₹7,79,603
Cash Balance (end Q2)                       ₹1,10,92,560
```

> Note the warranty cost multiplier `× 1.8` for a 2-year warranty. The 1-year formula is
> `Units × Defect Rate × ₹1,500`; the 2-year variant multiplies by 1.8.

---

## 5. Variant B — Growth & Profit (₹82,63,600) — the profitable quarter

### The premise

> Every lead-generation formula has an exponent under 1.0 (diminishing returns), **but diminishing
> doesn't mean unprofitable** — as long as marginal revenue from one more rupee still exceeds ₹1 of
> cost, spending more remains worth it, just at a shrinking rate of return. The efficiency reports
> stopped scaling once *waste* was eliminated; this version keeps scaling as long as it's still
> *profitable* to do so.

Total spend: **₹82,63,600 (96.6% of the ₹85,54,358 ceiling)**, keeping a ₹2,90,758 cushion purely
as a safety margin against calculation variance — not because more spend stopped being worthwhile.

### Department split

| Department | Efficiency-Final | Growth version | Why the increase |
|---|---|---|---|
| Marketing | ₹11,50,000 | **₹29,23,600** | Google and Meta restored and expanded — generating far more raw leads is now directly the point |
| Sales | ₹10,45,800 | **₹20,00,000** | Capacity must scale to match the much larger lead pool — sized with a real buffer, not a knife-edge match |
| R&D | ₹7,00,000 | **₹10,00,000** | More Quality/Innovation raises the Ceiling further |
| Operations | ₹2,68,000 | **₹11,40,000** | Real new production capacity needed — 729 inherited units can't carry the quarter at this scale |
| HR | ₹5,00,000 | ₹5,00,000 | Already appropriately sized |
| Finance/Admin | ₹5,50,000 | ₹5,00,000 | Marginally trimmed — lowest-leverage department for a growth quarter |

**Pre-Launch Buzz deliberately minimised to ₹50,000** — the one line actively working against this
quarter's goal, since Buzz has zero payoff this quarter by design.

### Marketing calculation

| Channel | Formula | Calculation | Leads |
|---|---|---|---|
| Google Ads | `375 × x^0.68` | `375 × 12.00^0.68` | 2,032 |
| Meta Ads | `200 × x^0.65` | `200 × 5.00^0.65` | 569 |
| Social & Influencer | `225 × x^0.72` | `225 × 6.00^0.72` | 817 |
| Content/SEO | `75 × x^0.62` | `75 × 2.00^0.62` | 115 |
| Events/PR | `90 × x^0.62` | `90 × 1.00^0.62` | 90 |
| Email Marketing | `80 × x^0.55` | `80 × 2.00^0.55` | 117 |
| Referral | cap-matched | | 912 |
| **Raw total** | | | **4,652** |

```
+ SEO Asset free leads (4.5 × 25)                113
+ Pre-Launch Buzz free leads (5.5 × 15)           83
Subtotal                                       4,848
× Brand Score multiplier (8.7 → ×1.174)      → 5,691
× HR Productivity Multiplier (×1.106)        → 6,297 Effective Leads
```

New assets: Brand Score **+22.5 → 31.2** (biggest single-quarter build yet) · SEO Asset **+7.0 → 11.5**
· new Buzz Score only **2.8**

### Sales — with a real buffer

```
Reps & Commissions ₹14,00,000:  Capacity = 500 × 14.00 × 0.939 = 6,573
                                (vs. 6,297 leads — a real ~276-lead buffer)
                                Bonus    = 2 × 14.00^0.5 = +7.48 pts
CRM Tools ₹3,00,000:            1.5 × 3.00^0.4 = +2.29 pts
Onboarding ₹3,00,000:           +5.20 Sat, +4.66 Repeat

Leads Used = MIN(6,297, 6,573) = 6,297 — zero leads wasted, buffer intact
```

**Why not knife-edge match:** at this scale a capacity shortfall wastes far more potential revenue
per lead. With 6,297 effective leads in play, even a small gap wastes hundreds of units' worth of
demand. A real buffer here is cheap insurance.

### R&D

```
Quality/QA ₹6,00,000:        Quality = 9.95 + 6 × 6.00^0.5 = 24.65,  Defect = 5.1%
Innovation ₹4,00,000:        Innovation = 7.5 + 5 × 4.00^0.5 = 17.5

Conversion Ceiling = 15% + (24.65 + 0.5 × 17.5) × 0.3% = 25.0%
+ Warranty (2-year) = +3.0%
Final Conversion Rate = 28.0%

Raw uncapped conversion = 31.2% → Ceiling STILL binds by ~3.2pts
```

**Why the gap didn't close despite ₹10,00,000 in R&D:** the raw conversion rate also grew (from the
much bigger Reps spend), so **R&D was chasing a moving target.**

### Operations

```
Manufacturing ₹8,40,000:   400 × 8.40^0.7 × 0.939 = 1,315 new effective units
                           Cost = max(2600, 3250 − 90 × 8.40^0.5) = ₹2,989/unit
Supplier & QC ₹1,50,000:   74.9 + 4 × 1.50^0.5 = 79.8
Logistics ₹1,50,000:       65.5 + 5 × 1.50^0.5 = 71.6 → +3.6 Satisfaction

Available to Sell = 1,315 + 729 = 2,044 units
```

**Unit cost fell to ₹2,989** (below Q1's ₹3,087) — at this much larger Manufacturing spend,
economies of scale pushed cost down. A real additional benefit of operating at scale that the
smaller efficiency-focused versions couldn't access.

### HR & Finance/Admin (held steady)

| Dept | Line | Spend | Result |
|---|---|---|---|
| HR | Culture & Benefits | ₹1,50,000 | Satisfaction 76.6, Multiplier 1.106 |
| HR | Training & Development | ₹2,00,000 | Engagement 74.2, Attrition 6.1% |
| HR | Customer Experience | ₹1,50,000 | +4.2 Sat, +2.1 Repeat |
| Fin | Compliance & Legal | ₹2,00,000 | Compliance 65.5 |
| Fin | Financial Planning | ₹1,80,000 | Forecast 71.7 → Q3 cost cut |
| Fin | Audit Prep | ₹1,20,000 | Audit Readiness 62.7 |

`Q3 Fixed Costs = ₹22,67,393` · `Compliance Penalty Risk ≈ 17.4%`

### Growth & Profit P&L

```
Raw Leads (7 channels)                              4,652
+ Free bonuses (SEO 113, Buzz 83)                   4,848
× Brand multiplier (1.174)                          5,691
× HR multiplier (1.106)                             6,297 Effective Leads
Leads Used = MIN(6,297, 6,573)                      6,297 — zero waste
Conversion Rate = Ceiling 25.0% + Warranty 3.0%     28.0%
Units from funnel = 6,297 × 28.0%                   1,764
+ Free repeat units (19.0% × 562)                    +107
TOTAL UNITS SOLD                                    1,871
Available to Sell (supply check)                    2,044 ✓ no stockout
Revenue = 1,871 × ₹9,999                    ₹1,87,09,661
COGS    = 1,871 × ₹2,989                       ₹55,93,167
Gross Profit                                ₹1,31,16,493
− Warranty Cost                                 ₹2,55,668
− Holding Cost (173 units carried)                ₹25,989
Adjusted Gross Profit                       ₹1,28,34,836
− Fixed Costs                                  ₹23,17,805
− Discretionary Spend                          ₹82,63,600
────────────────────────────────────────────────────────
NET CASH FLOW                                +₹22,53,431  ← PROFITABLE
Cash Balance (end Q2)                       ₹1,41,25,594
```

---

## 6. Every Q2 version side by side

| Metric | Q1 | Naive Repeat | Efficiency-Final | Inventory-Priority | Growth & Profit |
|---|---|---|---|---|---|
| Discretionary Spend | ₹45,00,000 | ₹45,00,000 | ₹42,73,200 | ₹42,13,800 | ₹82,63,600 |
| Units Sold | 562 | 733 | 872 | 872 | **1,871** |
| Revenue | ₹56,15,653 | ₹73,24,978 | ₹87,22,397 | ₹87,22,397 | **₹1,87,09,661** |
| Net Cash Flow | −₹31,27,837 | −₹19,22,012 | −₹7,79,603 | −₹7,27,690 | **+₹22,53,431** |
| Cash Balance | ₹1,18,72,163 | ₹99,50,151 | ₹1,10,92,560 | ₹1,11,44,473 | **₹1,41,25,594** |
| Valuation | ₹5,25,07,602 | ₹6,71,94,295 | ₹7,89,33,060 | ₹7,88,57,324 | **₹16,41,06,732** |
| Leads/units wasted | 216 | 1,244 | ~0 | ~0 | 0 |

---

## 7. Valuation — Q2

### Efficiency-Final
```
Revenue Multiple (70%)     (₹87,22,397 × 4) × 3.0x            = ₹10,46,68,770
Asset-Based (20%)          Net Tangible Assets                = ₹1,46,87,101
Intangible (added in full) (16.75+16.16+21.95)×₹20,000
                           + 5,434×₹300                       = ₹27,27,501
Blended                                                       = ₹7,89,33,060
```
Implied return: 1.97x on ₹4 Cr raised.

### Growth & Profit
```
Revenue Multiple (70%)     (₹1,87,09,661 × 4) × 3.0x          = ₹22,45,15,927
Asset-Based (20%)          Net Tangible Assets                = ₹1,77,43,502
Intangible (added in full) (31.2+17.5+24.65)×₹20,000
                           + 6,433×₹300                       = ₹33,96,882
Blended                                                       = ₹16,41,06,732
```
Implied return: **4.10x** on ₹4 Cr raised.

---

## 8. What carries into Q3 (Growth & Profit endpoint — the canonical Q3 starting state)

| Metric | Value |
|---|---|
| Cash Balance | ₹1,41,25,594 |
| Brand Score | **31.2** (nearly 4x every prior version) |
| SEO Asset | 11.5 |
| Repeat Purchase Rate | 31.2% |
| Quality / Innovation Score | 24.65 / 17.5 |
| Attrition Rate (bites Q3) | 6.1% |
| Customers | 6,433 (up from 4,562) |
| Total Employees | ~48 |
| Finished Goods Inventory | 173 units |
| Q3 Fixed Costs | ₹22,67,393 |
| Supplier Reliability | 79.8 |
| Compliance / Audit Readiness | 65.5 / 62.7 |

---

## 9. CEO scoring — Growth & Profit variant (84/100)

| Trait (Weight) | Points | Evidence |
|---|---|---|
| Strategic Thinking (15) | **14** | Correctly identified that diminishing returns ≠ unprofitable — real margin existed between "efficient" spend and the ceiling, and scaled every lever to capture it |
| Leadership (10) | **9** | Decisive, high-conviction call to nearly double spend rather than defaulting to the safer proven path |
| Adaptability (15) | **12** | Successfully pivoted the entire allocation philosophy (efficiency → scale) — strong, though a *directed* pivot rather than self-discovered from new data |
| Systems Thinking (20) | **18** | Every department scaled together in coordination — Sales capacity built with real buffer, R&D raised to match, Ops sized for genuine new production |
| Risk Management (15) | **10** | Kept a ₹2,90,758 cushion and avoided debt — but overall risk exposure roughly doubled, and a real fixed cost commitment now rides on formulas holding up at an untested scale |
| Capital Allocation (15) | **14** | Precisely identified where more capital was still profitable (Google/Meta/Reps/Ops) vs. where it wasn't (Referral at cap, Buzz minimised) |
| Long-Term Thinking (10) | **6** | Deliberately sacrificed Pre-Launch Buzz for this quarter's profit — legitimate given the mandate, but a real reduction in Q3/Q4 compounding pipeline. **The clearest miss** |
| **Subtotal** | **83** | |

### Modifiers — each tied to a checkable threshold, not vibes

| Modifier | Trigger condition (the actual rule) | Points |
|---|---|---|
| Profitability | `Net Cash Flow > 0` (binary; first quarter this has ever been true) | **+3** |
| Perfect channel match | `Referral Spend = Referral Cap × ₹300` exactly | **+2** |
| Compounding asset cut | Buzz Score built this quarter < 50% of prior quarter's Buzz spend equivalent | **−2** |
| Ceiling under-shot | `Raw Conversion Rate − Ceiling Conversion Rate > 3 points` | **−2** |
| **Net Modifier** | | **+1** |

```
FINAL SCORE = 83 + 1 = 84/100 → STRONG CEO (band 75–89, near the top)
```

**Why this scored higher than the efficiency version (82) despite more risk:** the efficiency
version proved *discipline*; this version proved *conviction backed by evidence* — two quarters of
real data justified the bigger bet, and it paid off as the model predicted. What holds it back from
Exceptional (90+) are the same two issues in every version: R&D's ceiling still isn't closed, and a
genuinely long-term-optimal CEO would have found a way to fund Pre-Launch Buzz **and** the scale-up,
rather than trading one for the other.

---

## 10. The lessons

**Efficiency-Final:** *"Q1 taught that departments have to work together. Q2 taught that 'working
together' isn't the same as 'spending more everywhere.' The single biggest improvement — nearly
₹7,21,000 — came not from a smarter growth bet, but from refusing to pay for capacity or supply
beyond what the rest of the business could actually use."*

**Growth & Profit:** *"The first two Q2 reports taught precision — match every gate exactly to
demand, waste nothing. This version teaches the lesson precision alone can't: sometimes the right
move isn't to spend less, it's to spend more, everywhere, at once, because diminishing returns
still leave real profit on the table well beyond the 'efficient' spend level. The real skill isn't
choosing between efficiency and scale — it's knowing which quarter, with which evidence in hand,
calls for each."*
