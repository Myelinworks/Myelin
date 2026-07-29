# Sales Workspace

> Source: `sales_workspace.pdf`

## Objective

Convert market demand into profitable revenue by selecting the right sales channels,
partnerships, pricing execution, negotiations, customer segments, and revenue strategies.

## 1. Sales scoring weights

| Skill | Weight |
|---|---|
| Revenue Optimization | 25% |
| Strategic Thinking | 20% |
| Customer Focus | 20% |
| Negotiation & Decision Making | 15% |
| Channel Strategy | 10% |
| Long-Term Growth | 10% |

## 2. Sales decision table

| ID | Decision | Interaction | Variables Updated | Formula / Logic | Affects | Score |
|---|---|---|---|---|---|---|
| SAL-001 | Sales Channel Prioritization | Strategy Cards | Channel Allocation | Revenue Distribution | Revenue | 8% |
| SAL-002 | Marketplace Strategy | Opportunity Cards | Marketplace Revenue | `Conversion × Traffic` | Marketing | 8% |
| SAL-003 | Enterprise / B2B Deals | Opportunity Cards | Enterprise Revenue | Contract Value | Operations | 8% |
| SAL-004 | Pricing Execution | Pricing Cards | Selling Price | Finance Pricing | Revenue | 8% |
| SAL-005 | Promotional Offers | Promotion Cards | Sales Velocity | Promotion Effect | Marketing | 8% |
| SAL-006 | Customer Segment Strategy | Segment Cards | Segment Revenue | Segment Conversion | Marketing | 8% |
| SAL-007 | Distribution Expansion | Expansion Cards | Distribution Coverage | Channel Growth | Operations | 8% |
| SAL-008 | Sales Forecast | Forecast Board | Forecast Revenue | Demand Prediction | Finance | 6% |
| SAL-009 | Partnership Approval | Partnership Cards | Partner Revenue | Partner Performance | Marketing | 8% |
| SAL-010 | Customer Retention Strategy | Strategy Cards | Repeat Purchase | Retention Impact | Customer Success | 8% |
| SAL-011 | Negotiation | Interactive Negotiation | Deal Terms | Negotiation Engine | Revenue | 12% |
| SAL-012 | Quarter Sales Approval | Executive Approval | Sales Plan | Final Lock | Company | 10% |

Score column sums to **100%** ✓

## 3. Sales variables

| Variable | Initial | Updated By |
|---|---|---|
| Quarterly Revenue | ₹0 | Sales |
| Units Sold | 550 | Sales Engine |
| Selling Price | ₹10,000 | Finance |
| Average Selling Price (ASP) | ₹10,000 | Sales |
| Website Revenue | ₹0 | Sales |
| Marketplace Revenue | ₹0 | Sales |
| Enterprise Revenue | ₹0 | Sales |
| Partner Revenue | ₹0 | Sales |
| Revenue by Segment | ₹0 | Sales |
| Revenue by Channel | ₹0 | Sales |
| Average Order Value (AOV) | ₹10,000 | Sales |
| Website Conversion Rate | 2.8% | Sales |
| Marketplace Conversion Rate | 5.2% | Sales |
| Enterprise Conversion Rate | 18% | Sales |
| Repeat Purchase Rate | 18% | Sales |
| Customer Lifetime Value (CLV) | ₹0 | Sales Engine |
| Revenue Forecast | ₹0 | Sales |
| Forecast Accuracy | 0% | Sales Engine |
| Negotiation Success Rate | 0% | Sales |
| Discount Utilization | 0% | Sales |
| Channel Mix | System | Sales |

## 4. Sales formulas — **authoritative**

| Variable | Formula |
|---|---|
| Revenue | `Units Sold × Selling Price` |
| Average Selling Price | `Revenue ÷ Units Sold` |
| Average Order Value | `Revenue ÷ Total Orders` |
| Website Revenue | `Website Orders × Selling Price` |
| Marketplace Revenue | `Marketplace Orders × Selling Price` |
| Enterprise Revenue | `Enterprise Units × Selling Price` |
| Conversion Rate | `Orders ÷ Visitors × 100` |
| Repeat Purchase Rate | `Repeat Customers ÷ Active Customers × 100` |
| Customer Lifetime Value | `AOV × Purchase Frequency × Customer Lifespan` |
| Revenue Forecast Accuracy | `Actual Revenue ÷ Forecast Revenue × 100` |
| Channel Contribution | `Channel Revenue ÷ Total Revenue × 100` |
| Discount Impact | `Discount Amount ÷ Revenue × 100` |
| Gross Sales | `Units Sold × Selling Price` |
| Net Sales | `Gross Sales − Discounts − Returns` |

## 5. The Negotiation Engine — signature mechanic

**Students never simply click Accept.** Every large deal becomes negotiable.

### Example deal

| Field | Value |
|---|---|
| Buyer | Corporate Client |
| Wants | 1,000 Smartwatches |
| Initial Offer | ₹8,800 |
| Payment | 90 Days |
| Warranty | 2 Years |
| Delivery | 20 Days |

### Negotiable levers

| Variable | Options |
|---|---|
| Price | Counter Offer |
| Quantity | Counter Offer |
| Delivery Timeline | Faster / Standard |
| Warranty | 1 Year / 2 Years |
| Payment Terms | Advance / 30 / 60 / 90 Days |
| Support | Basic / Premium |
| Free Accessories | Yes / No |

### Negotiation formulas

```
Negotiation Score
  = Price Competitiveness
  + Relationship Score
  + Inventory Availability
  + Brand Strength
  + Delivery Capability
  − Risk
```

```
Acceptance Probability
  = Negotiation Score
  × Buyer Flexibility
  × Market Demand
```

> ⚠️ **Gap:** neither formula specifies the scale, units, or weight of any term. `Negotiation
> Score` is an unweighted sum of six differently-scaled quantities, and `Acceptance Probability`
> multiplies it by two further unscaled factors with no normalisation to a 0–1 range.
> **Unimplementable as written.** Tracked in `10-implementation-gaps.md`.

### Variables updated by a negotiation

- Enterprise Revenue
- Gross Margin
- Inventory
- Customer Satisfaction
- Partner Relationship
- Cash Flow

## 6. Sales dependency matrix

| Sales Decision | Finance | Marketing | Product | Operations | Customer Success |
|---|---|---|---|---|---|
| Channel Strategy | ❌ | ✅ | ❌ | ❌ | ❌ |
| Marketplace Strategy | ❌ | ✅ | ❌ | ❌ | ❌ |
| Enterprise Deals | ❌ | ❌ | ✅ | ✅ | ❌ |
| Pricing Execution | ✅ | ❌ | ❌ | ❌ | ❌ |
| Promotions | ✅ | ✅ | ❌ | ❌ | ❌ |
| Customer Segments | ❌ | ✅ | ❌ | ❌ | ❌ |
| Distribution Expansion | ❌ | ❌ | ❌ | ✅ | ❌ |
| Forecast | ✅ | ✅ | ❌ | ✅ | ❌ |
| Partnerships | ❌ | ✅ | ❌ | ❌ | ❌ |
| Retention | ❌ | ❌ | ✅ | ❌ | ✅ |
| Negotiation | ✅ | ❌ | ✅ | ✅ | ❌ |

## 7. Hidden Sales Engine variables

Not shown to the student; drive the engine internally.

- Sales Momentum
- Brand Pull
- Competitive Pressure
- Price Elasticity
- Channel Efficiency
- Customer Trust
- Deal Probability
- Partner Relationship Score
- Seasonal Demand
- Market Saturation
- Sales Risk
- Customer Churn Risk

> Price Elasticity, Seasonal Demand, and Market Saturation have concrete values/curves in
> `09-calibration-engine.md`. The rest have no specified derivation.
