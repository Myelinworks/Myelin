# Master Formula Index

> Derived from all source documents. Every implementable formula in one place.
> **Units convention: `x` = spend on that line in ₹ lakhs.** A ₹4,00,000 spend means `x = 4.00`.

Formulas marked ✅ are fully specified and implementable. Formulas marked ⚠️ have a stated shape
but a missing constant, weight, or threshold — see `10-implementation-gaps.md`.

---

## Marketing Engine

| Line | Formula | Status |
|---|---|---|
| Google Ads | `Leads = 375 × x^0.68` | ✅ |
| Meta Ads — leads | `Leads = 200 × x^0.65` | ✅ |
| Meta Ads — impressions | `Impressions = 40,000 × x` | ✅ |
| Meta Ads — brand | `Brand Score += 1.2 × x` | ✅ |
| Social & Influencer — leads | `Leads = 225 × x^0.72` | ✅ |
| Social & Influencer — brand | `Brand Score += 2.5 × x` | ✅ |
| Content/SEO — leads | `Leads = 75 × x^0.62` | ✅ |
| Content/SEO — asset | `SEO Asset += 3.5 × x` | ✅ |
| Content/SEO — payout | `Free leads next quarter = SEO Asset × 25` | ✅ |
| Events/PR — leads | `Leads = 90 × x^0.62` | ✅ |
| Events/PR — brand | `Brand Score += 1.5 × x` | ✅ |
| Email Marketing — leads | `Leads = 80 × x^0.55` | ✅ |
| Email Marketing — repeat | `Repeat Purchase Rate += 3 × x^0.5` (pts) | ✅ |
| Referral — cap | `Lead Cap = 0.20 × existing customers` | ✅ |
| Referral — cost | `₹300 per lead, flat` | ✅ |
| Pre-Launch Buzz — build | `Buzz Score = 4 × x^0.5`, zero leads this quarter | ✅ |
| Pre-Launch Buzz — Q+1 | `Free leads = Buzz Score × 15` | ✅ |
| Pre-Launch Buzz — Q+2 | `Free leads = Buzz Score × 25`, `Conversion += Buzz Score × 0.3` pts (one-time) | ✅ |
| Brand multiplier | `Lead Multiplier = 1 + 0.02 × Brand Score` | ⚠️ *fitted from 3 data points, needs designer confirmation* |

## Sales Engine

| Line | Formula | Status |
|---|---|---|
| Reps — capacity | `Capacity = 500 × x` (linear) | ✅ |
| Reps — conversion | `Conversion Bonus = 2 × x^0.5` (pts) | ✅ |
| CRM Tools | `Conversion Bonus = 1.5 × x^0.4` (pts) | ✅ |
| Onboarding — satisfaction | `Satisfaction += 3 × x^0.5` | ✅ |
| Onboarding — repeat | `Repeat Purchase Rate += 3 × x^0.4` (pts) | ✅ |
| Attrition discount | `Effective Capacity = Capacity × (1 − prior quarter Attrition Rate)` | ✅ |
| Revenue | `Units Sold × Selling Price` | ✅ |
| ASP | `Revenue ÷ Units Sold` | ✅ |
| AOV | `Revenue ÷ Total Orders` | ✅ |
| Conversion Rate | `Orders ÷ Visitors × 100` | ✅ |
| Repeat Purchase Rate | `Repeat Customers ÷ Active Customers × 100` | ✅ |
| CLV | `AOV × Purchase Frequency × Customer Lifespan` | ✅ |
| Forecast Accuracy | `Actual Revenue ÷ Forecast Revenue × 100` | ✅ |
| Channel Contribution | `Channel Revenue ÷ Total Revenue × 100` | ✅ |
| Net Sales | `Gross Sales − Discounts − Returns` | ✅ |
| Negotiation Score | `Price Competitiveness + Relationship + Inventory + Brand + Delivery − Risk` | ⚠️ *no weights or scales* |
| Acceptance Probability | `Negotiation Score × Buyer Flexibility × Market Demand` | ⚠️ *no normalisation* |

## R&D Engine

| Line | Formula | Status |
|---|---|---|
| Quality/QA — score | `Quality Score += 6 × x^0.5` (cumulative, never resets) | ✅ |
| Quality/QA — defects | `Defect Rate = max(2%, 8% − 1.2 × x^0.5)` | ✅ |
| Innovation — features | `Feature Completeness += 8 × x^0.5` (resets at 100) | ✅ |
| Innovation — score | `Innovation Score += 5 × x^0.5` (never decays) | ✅ |
| **Conversion Ceiling** | `15% + (Quality Score + 0.5 × Innovation Score) × 0.3%` | ✅ |
| Warranty bonus | 1yr `+1.5` pts · 2yr `+3.0` pts, **additive after the ceiling** | ✅ |
| Warranty cost (1yr) | `Units Sold × Defect Rate × ₹1,500` | ✅ |
| Warranty cost (2yr) | `Units Sold × Defect Rate × ₹1,500 × 1.8` | ✅ |

## Operations Engine

| Line | Formula | Status |
|---|---|---|
| Manufacturing — capacity | `Production Capacity = 400 × x^0.7` | ✅ |
| Manufacturing — unit cost | `max(₹2,600, ₹3,250 − 90 × x^0.5)` | ✅ |
| Supplier & QC | `Supplier Reliability += 4 × x^0.5` (baseline 70) | ✅ |
| Effective capacity | `Production Capacity × (Supplier Reliability ÷ 100)` | ✅ |
| Logistics — efficiency | `Logistics Efficiency += 5 × x^0.5` (baseline 60) | ✅ |
| Logistics — satisfaction | `Satisfaction += 0.05 × Logistics Efficiency` | ✅ |
| **Available to Sell** | `(Production Capacity × Supplier Reliability ÷ 100) + carried inventory` | ✅ |
| Holding cost | `₹150 per unsold unit per quarter` | ✅ |

## HR Engine

| Line | Formula | Status |
|---|---|---|
| Culture & Benefits | `Employee Satisfaction += 5 × x^0.5` (baseline 65) | ✅ |
| Productivity Multiplier | `1 + (Satisfaction − 50) × 0.004` | ✅ |
| Training & Development | `Employee Engagement += 6 × x^0.5` (baseline 60) | ✅ |
| Attrition Rate | `max(3%, 15% − 0.12 × Engagement)` | ✅ |
| CX Team — satisfaction | `Satisfaction += 4 × x^0.5` | ✅ |
| CX Team — repeat | `Repeat Purchase Rate += 2 × x^0.4` (pts) | ✅ |
| Total Employees | `14 + Σ(department spend ÷ ₹2,00,000)` | ✅ |

## Finance / Admin Engine

| Line | Formula | Status |
|---|---|---|
| Compliance & Legal | `Compliance Score += 5 × x^0.5` (baseline 50) | ✅ |
| Financial Planning | `Forecast Accuracy += 6 × x^0.5` (baseline 55) | ✅ |
| Cash Efficiency Bonus | `(Forecast Accuracy − 50) × 0.1%` → discount to **next** quarter's Fixed Costs | ✅ |
| Audit Prep | `Audit Readiness += 5 × x^0.5` (baseline 50) | ✅ |
| Penalty Risk | `max(5%, 40% − 0.25 × Compliance − 0.10 × Audit Readiness)` | ✅ |
| Available Budget | `Opening Cash − Reserve Cash` | ✅ |
| Discretionary Ceiling | `Cash − Fixed Costs − Working Capital Buffer` | ✅ |
| Closing Cash | `Opening Cash + Revenue − Total Expenses − Investments` | ✅ |
| Cash Runway | `Cash Available ÷ Monthly Burn` | ✅ |
| Debt Ratio | `Outstanding Debt ÷ Total Assets` | ✅ |
| Operating Margin | `(Revenue − Operating Expenses) ÷ Revenue` | ✅ |
| Debt interest | 10% p.a. | ✅ |

## Crisis Engine

| Scenario | Formula | Status |
|---|---|---|
| A — dampening | `Raw Leads × 0.75` | ✅ |
| A — conversion penalty | `−8` pts | ✅ |
| A — brand erosion (if ₹0 spent) | `Brand Score − 3` | ✅ |
| B — dampening | `Raw Leads × 0.60` | ✅ |
| B — conversion penalty | `−3` pts | ✅ |
| B — brand erosion (if ₹0 spent) | `Brand Score − 8` | ✅ |
| C — dampening | `Raw Leads × 0.80` | ✅ |
| C — conversion penalty | `−6` pts, or `−2` if Innovation Score ≥ 20 | ✅ |
| C — ceiling penalty | additional `−2` off R&D Ceiling, waived if Innovation ≥ 20 | ✅ |
| **D — Capacity Multiplier** | `MIN(1.0, MAX(0.10, 0.50 + 0.005×(SupplierRel − 50) + ChoiceOffset + 0.10×x^0.5))` | ✅ |
| D — choice offsets | `0` / `+0.25` (Choice B) / `+0.50` | ⚠️ *which choice is +0.50 not stated* |
| D — cost surcharge | `+₹500/unit` | ✅ |
| Price-Match Fund | `Dampening Recovery = MIN(1.0, 0.75 + 0.15 × x^0.5)` | ✅ |
| Comparison Ads | `Conversion Recovery = MIN(8, 2 × x^0.5)` pts | ✅ |
| Retention Offers | `Customer Loss = MAX(0%, 8% − 1.5 × x^0.5)` | ✅ |
| Emergency Supply Fund | `+0.10 × x^0.5` to Capacity Multiplier | ✅ |
| Choice D — A | `Dampening Recovery = 0.75 + 0.20 × x^0.5` | ✅ |
| Choice D — B | `Dampening Recovery = 0.60 + 0.25 × x^0.5`, brand contribution halved | ✅ |
| Choice D — C | `Innovation Score += 3 × x^0.5` (this quarter only) | ✅ |
| Choice D — D | `Contract Capacity = 320 × x^0.7 × 0.75`, `+₹350/unit` | ✅ |

## Valuation Engine

| Component | Formula | Status |
|---|---|---|
| Revenue Multiple | `(Quarterly Revenue × 4) × 3.0x` | ✅ |
| Asset-Based | `Total Assets − Liabilities` | ✅ |
| Intangible Premium | `(Brand + Innovation + Quality) × ₹20,000 + Customers × ₹300` | ✅ |
| **Blended** | `0.70 × RevenueMultiple + 0.20 × AssetBased + IntangiblePremium` | ✅ |

## Scoring Engine

| Component | Formula | Status |
|---|---|---|
| Trait points | `Trait Weight × (fraction of 3 sub-criteria satisfied)` | ✅ |
| Sub-criterion credit | met = `1/3` · partial = `1/6` · not met = `0` | ✅ |
| Final Score | `Σ Trait Points + Σ Modifiers` | ✅ |
| Trait weights | Systems 20 · Strategic 15 · Adaptability 15 · Risk 15 · Capital 15 · Leadership 10 · Long-Term 10 | ✅ |
| Score bands | 90–100 Exceptional · 75–89 Strong · 60–74 Competent · 40–59 Weak · <40 Poor | ✅ |
| Momentum Score | weighted composite of 7 inputs | ⚠️ *weights and cut-offs unspecified* |

## CX Engine

| Metric | Formula | Status |
|---|---|---|
| CSAT | `Positive Experiences ÷ Total Experiences × 100` | ✅ *(definition only)* |
| NPS | `% Promoters − % Detractors` | ✅ *(definition only)* |
| Churn Rate | `Lost Customers ÷ Active Customers × 100` | ✅ *(definition only)* |
| Retention Rate | `Active Customers ÷ Previous Customers × 100` | ✅ *(definition only)* |
| Referral Rate | `Referred ÷ Active Customers × 100` | ✅ *(definition only)* |
| Product Adoption | `Active Feature Users ÷ Active Customers × 100` | ✅ *(definition only)* |
| Brand Trust | `Previous Trust + Positive Experiences − Negative Experiences` | ⚠️ *no units* |
| Social Sentiment | `Positive Mentions − Negative Mentions` | ⚠️ *no source for mention counts* |
| All 12 CX decision effects | named engines, no formulas | ⚠️ **entirely unspecified** |

---

## The canonical execution chain

```
1.  Raw Leads = Σ(all Marketing channel formulas)
2.  + SEO Asset payout (prior quarter SEO Asset × 25)
3.  + Pre-Launch Buzz payout (Buzz × 15 at Q+1, × 25 at Q+2)
4.  × Brand Multiplier                                   [Q2+ only]
5.  × HR Productivity Multiplier
    → Effective Leads
6.  MIN(Effective Leads, Sales Capacity × (1 − Attrition))
    → Leads Actually Used                                ← HARD GATE 1
7.  Conversion Rate = R&D Conversion Ceiling + Warranty Bonus
                                                          ← HARD GATE 2
8.  Units from funnel = Leads Used × Conversion Rate
9.  + Free repeat units = prior Repeat Rate × prior Units Sold
10. MIN(Total Units, Available to Sell)
    → UNITS SOLD                                          ← HARD GATE 3
11. Revenue      = Units Sold × Selling Price
12. COGS         = Units Sold × Manufacturing Cost/Unit
13. Gross Profit = Revenue − COGS
14. − Warranty Cost = Units Sold × Defect Rate × ₹1,500 (× 1.8 if 2-year)
15. − Holding Cost  = (Available to Sell − Units Sold) × ₹150
    → Adjusted Gross Profit
16. − Fixed Costs
17. − Total Discretionary Spend
    → NET CASH FLOW
```

### The two regression tests every implementation must pass

**Test 1 — Warranty is additive AFTER the ceiling, not subject to it.**
```
Final Conversion Rate = Conversion Ceiling + Warranty Bonus
NOT: MIN(Conversion Ceiling, raw + Warranty Bonus)
```

**Test 2 — Sales Capacity is re-checked AFTER all multipliers.**
```
Leads Actually Used = MIN(Effective Leads, Sales Capacity)
where Effective Leads already includes Brand and HR multipliers.
```

Both errors occurred in the original Q1 report and nearly cancelled out by coincidence. See
`12-quarter-1-reference.md` § 9.

### The canonical modifier-chain validation case

From `05-marketing-workspace.md`:
```
15% × 0.9 × 0.6 × 1.0 × 0.8 = 6.48%
```
This should be the first unit test written for the modifier chain.
