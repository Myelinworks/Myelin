# Calibration Layer V1 — Indian Consumer Goods

> Source: `calibration_engine.pdf`

This is the **modifier lookup layer**. Every table here is a directly implementable
`(input band → output %)` mapping.

## 1. Marketing defaults

| Variable | Default |
|---|---|
| Monthly Marketing Budget | ₹10,00,000 |
| Google Search Allocation | 35% |
| Meta Allocation | 40% |
| YouTube | 10% |
| Influencer | 10% |
| Email / CRM | 5% |

### Google Ads defaults

| Metric | Default |
|---|---|
| Average CPC | ₹20 |
| CTR | 5.2% |
| Landing Page Conversion | 3.8% |
| Lead Qualification | 80% |
| Sales Conversion | 22% |
| ROAS | 3.5x |

### Meta Ads defaults

| Metric | Default |
|---|---|
| CPC | ₹8 |
| CTR | 1.1% |
| Landing Page Conversion | 6.5% |
| Lead Qualification | 75% |
| Sales Conversion | 18% |
| ROAS | 2.8x |

### Organic marketing defaults

| Metric | Default |
|---|---|
| Organic Traffic Growth | 2% / Quarter |
| Conversion Rate | 2.8% |
| Repeat Purchase | 18% |

### Reference funnel (at ₹10,00,000 marketing budget)

| Stage | Default |
|---|---|
| Impressions | 12,500,000 |
| Reach | 7,000,000 |
| Clicks | 62,500 |
| Website Visitors | 60,000 |
| Leads | 2,400 |
| Qualified Leads | 1,920 |
| Customers | 422 |

## 2. Marketing budget → effect

| Decision | Immediate Effect | Delayed Effect |
|---|---|---|
| Budget +10% | Reach +6% | Brand +2% |
| Budget +20% | Reach +13% | Leads +9% |
| Budget +30% | Reach +18% | Leads +13% |
| Budget +50% | Reach +28% | Leads +18% |

## 3. Creative quality → CTR

| Score | CTR Effect |
|---|---|
| Excellent | +30% |
| Good | +15% |
| Average | 0 |
| Weak | −20% |
| Poor | −40% |

## 4. Landing page quality → conversion

| Quality | Conversion Effect |
|---|---|
| Excellent | +35% |
| Good | +20% |
| Average | 0 |
| Weak | −15% |
| Poor | −35% |

## 5. Product pricing → demand

| Price Change | Demand Change |
|---|---|
| −5% | +5% |
| −10% | +10% |
| −20% | +18% |
| +5% | −4% |
| +10% | −8% |
| +20% | −18% |

> This table is the coefficient source for **FIN-008 Pricing Approval**.

## 6. Product quality change → satisfaction / complaints

| Improvement | Satisfaction |
|---|---|
| +10% | +5% |
| +20% | +9% |
| +30% | +13% |

| Quality Drop | Complaint Increase |
|---|---|
| −10% | +8% |
| −20% | +18% |
| −30% | +30% |

## 7. Customer satisfaction → repeat purchase

| Score | Repeat Purchase |
|---|---|
| 90 | 45% |
| 80 | 35% |
| 70 | 25% |
| 60 | 15% |
| 50 | 8% |

## 8. Production

| Decision | Effect |
|---|---|
| Production +10% | Capacity +10% |
| Production +20% | Capacity +20% |
| Production > Demand | Inventory ↑ |
| Demand > Production | Lost Sales |

## 9. Inventory level → holding cost

| Inventory Level | Holding Cost |
|---|---|
| Normal | 0 |
| +20% | +4% |
| +40% | +9% |
| +60% | +16% |

## 10. HR

| Decision | Effect |
|---|---|
| Salary +10% | Retention +5% |
| Salary +20% | Retention +10% |
| Training +10% | Productivity +3% (**next quarter**) |
| Training +20% | Productivity +6% (**next quarter**) |

## 11. Finance

| Decision | Effect |
|---|---|
| Loan ₹1 Cr | Cash +₹1 Cr |
| Interest Rate | **10% p.a.** |
| Share Buyback | EPS +4% |
| Dividend | Investor Satisfaction +5% |

## 12. Operations

| Decision | Effect |
|---|---|
| New Factory | Capacity +30% |
| Automation | Productivity +15% |
| Maintenance Reduction | Breakdown Risk +12% |

## 13. Brand awareness → demand

| Increase | Demand Effect |
|---|---|
| +10% | +4% |
| +20% | +8% |
| +30% | +11% |

## 14. Market share → competitor reaction

| Market Share | Competitor Reaction |
|---|---|
| <10% | Ignore |
| 10–20% | Moderate Competition |
| 20–30% | Price Competition |
| >30% | Aggressive Response |

## 15. Economy → demand (short form)

| Economy | Demand |
|---|---|
| Boom | +12% |
| Stable | 0 |
| Slowdown | −8% |
| Recession | −18% |

## 16. Seasonality (generic quarters)

| Quarter | Demand |
|---|---|
| Q1 | 100% |
| Q2 | 108% |
| Q3 | 95% |
| Q4 | 115% |

## 17. Variable bounds (min/max clamps)

| Variable | Base Value | Min | Max |
|---|---|---|---|
| Google CTR | 5.2% | 3.8% | 7.2% |
| Meta CTR | 1.1% | 0.7% | 1.8% |
| Google CVR | 3.8% | 2.5% | 6.0% |
| Meta CVR | 6.5% | 4.0% | 9.0% |
| Price Elasticity | −0.8 | −0.5 | −1.3 |
| Marketing ROI | 3.5x | 2.2x | 5.5x |

## 18. The master multiplier chain

```
Final Result
  = Base Market
  × Competitor Modifier
  × Brand Modifier
  × Product Modifier
  × Customer Modifier
  × Economy Modifier
  × Season Modifier
  × Random Event Modifier
  × Student Decision Modifier
```

*"This makes every quarter different while still being explainable."*

---

# The 13 Modifier Lookup Tables

These are the concrete tables feeding the multiplier chain above.

## M1. Competitor actions

| Competitor Action | Your Sales | Your Leads | Your Market Share | Your Brand |
|---|---|---|---|---|
| Heavy Advertising | −4% | −8% | −3% | −2% |
| Price Reduction 5% | −6% | −2% | −5% | 0 |
| Price Reduction 10% | −12% | −4% | −9% | 0 |
| Premium Product Launch | −3% | −2% | −2% | −5% |
| New Distribution | −5% | −1% | −4% | 0 |
| Product Recall | +8% | +6% | +5% | +3% |
| Factory Shutdown | +10% | +7% | +6% | +2% |
| Competitor Acquisition | −6% | −3% | −5% | −2% |

## M2. Product quality

| Quality Score | Conversion | Customer Satisfaction | Repeat Purchase | Complaints |
|---|---|---|---|---|
| 100 | +18% | +20% | +18% | −40% |
| 90 | +10% | +12% | +10% | −20% |
| 80 | +5% | +5% | +5% | −10% |
| 70 | 0 | 0 | 0 | 0 |
| 60 | −8% | −10% | −8% | +15% |
| 50 | −15% | −20% | −18% | +35% |

**70 is the neutral baseline.**

## M3. Brand strength

| Brand Score | CTR | Conversion | Price Acceptance | Repeat Purchase |
|---|---|---|---|---|
| 100 | +20% | +18% | +12% | +20% |
| 90 | +15% | +12% | +8% | +15% |
| 80 | +8% | +6% | +4% | +8% |
| 70 | 0 | 0 | 0 | 0 |
| 60 | −6% | −4% | −3% | −6% |
| 50 | −15% | −10% | −8% | −15% |

**70 is the neutral baseline.**

## M4. Market demand

| Market Condition | Demand |
|---|---|
| Very High | +20% |
| High | +12% |
| Normal | 0 |
| Low | −10% |
| Very Low | −20% |

## M5. Customer satisfaction

| Satisfaction | Referral | Repeat Purchase | Reviews |
|---|---|---|---|
| 90 | +18% | +22% | +15% |
| 80 | +10% | +12% | +8% |
| 70 | +5% | +5% | +4% |
| 60 | 0 | 0 | 0 |
| 50 | −10% | −12% | −15% |
| 40 | −20% | −25% | −35% |

**60 is the neutral baseline here** (note: differs from M2/M3, which use 70).

## M6. Economy (long form)

| Economy | Demand | Financing | Customer Spending |
|---|---|---|---|
| Boom | +18% | Easier | +15% |
| Growth | +8% | Normal | +6% |
| Stable | 0 | Normal | 0 |
| Slowdown | −10% | Harder | −8% |
| Recession | −25% | Difficult | −20% |

> ⚠️ **Conflict:** §15 gives a shorter, milder economy table (Boom +12%, Slowdown −8%,
> Recession −18%). This long-form table (Boom +18%, Slowdown −10%, Recession −25%) adds a
> "Growth" band and stronger swings. **Pick one.** Tracked in `10-implementation-gaps.md`.

## M7. Seasonality (industry-specific example: bicycles)

| Quarter | Demand |
|---|---|
| Jan–Mar | −5% |
| Apr–Jun | +12% |
| Jul–Sep | +4% |
| Oct–Dec | +18% |

> This is an *example* of an industry seasonality curve, distinct from the generic §16 table.
> The smartwatch/wearables curve is not specified.

## M8. Random events

| Event | Probability | Impact |
|---|---|---|
| Viral Social Media Post | 4% | Brand +20% |
| Factory Fire | 2% | Production −35% |
| Government Subsidy | 5% | Demand +10% |
| Fuel Price Increase | 8% | Logistics Cost +15% |
| New Competitor | 5% | Market Share −5% |
| Supplier Bankruptcy | 3% | Inventory −25% |
| Celebrity Endorsement | 2% | Brand +15% |
| Product Recall | 2% | Brand −25% |
| Economic Slowdown | 5% | Demand −12% |
| Festival Season | 15% | Sales +15% |

Probabilities sum to **51%** — so roughly half of quarters see no random event.

## M9. Marketing creative

| Creative Score | CTR |
|---|---|
| Excellent | +25% |
| Good | +12% |
| Average | 0 |
| Weak | −12% |
| Poor | −25% |

> ⚠️ **Conflict with §3** (Excellent +30%, Good +15%, Weak −20%, Poor −40%). Tracked in
> `10-implementation-gaps.md`.

## M10. Website / landing page

| Landing Page | Conversion |
|---|---|
| Excellent | +30% |
| Good | +15% |
| Average | 0 |
| Weak | −15% |
| Poor | −30% |

> ⚠️ **Conflict with §4** (Excellent +35%, Good +20%, Weak −15%, Poor −35%).

## M11. Pricing vs industry average

| Difference vs Industry Average | Demand |
|---|---|
| −20% | +18% |
| −10% | +10% |
| −5% | +5% |
| Same | 0 |
| +5% | −4% |
| +10% | −8% |
| +20% | −18% |

Consistent with §5 ✓

## M12. Inventory stock level

| Stock Level | Effect |
|---|---|
| 120% | Holding Cost +10% |
| 100% | Ideal |
| 90% | Minor Shortage |
| 80% | Lost Sales −5% |
| 70% | Lost Sales −12% |
| 60% | Lost Sales −22% |

## M13. HR employee satisfaction

| Employee Satisfaction | Productivity | Attrition |
|---|---|---|
| 90 | +12% | −10% |
| 80 | +6% | −5% |
| 70 | 0 | 0 |
| 60 | −6% | +8% |
| 50 | −12% | +18% |

---

## The recommended improvement: weight + variance, not fixed percentages

> *"I would not use fixed percentages directly. Instead, each event would have a weight and a
> variance."*

| Variable | Base | Variance |
|---|---|---|
| Competitor Price Cut | −8% | ±3% |
| Product Quality | +10% | ±2% |
| Brand Strength | +8% | ±2% |
| Economy | −12% | ±4% |
| Festival Season | +15% | ±5% |

Then, if a competitor cuts prices, the engine doesn't always apply −8%. It randomly selects a
value within the allowed range (e.g. −6.7% this quarter, −9.4% next quarter), and that result is
then influenced by the student's own decisions.

> ⚠️ **Design tension:** the platform is specified as **deterministic** in
> `01-technical-architecture.md`. Adding variance makes it stochastic. If variance is adopted,
> the RNG must be seeded per `(company_id, quarter_id)` so replays are reproducible.
> Tracked in `10-implementation-gaps.md`.
