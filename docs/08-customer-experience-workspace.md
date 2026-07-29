# Customer Experience (CX) Workspace

> Source: `The_student_responds_strategically_and_those_decisions_ripple_into_Product_Marketing_Sales_Operations_and_Finance_.pdf`

## Objective

Improve customer satisfaction, increase retention, reduce churn, strengthen brand trust, build
community, and maximise customer lifetime value through strategic customer experience decisions.

## 1. CX scoring weights

| Evaluation Metric | Weight |
|---|---|
| Customer-Centric Thinking | 30% |
| Strategic Thinking | 20% |
| Problem Solving | 15% |
| Brand Building | 10% |
| Long-Term Thinking | 10% |
| Decision Quality | 10% |
| Crisis Management | 5% |

## 2. CX decision table

| ID | Decision | Interaction | Variables Updated | Formula / Logic | Cross-Dept | Score |
|---|---|---|---|---|---|---|
| CX-001 | Customer Support Strategy | Strategy Cards | Resolution Time, CSAT | Support Efficiency | Brand Trust | 8% |
| CX-002 | Complaint Resolution | Live Scenarios | CSAT, Trust | Resolution Quality | Product | 10% |
| CX-003 | Return & Warranty Policy | Policy Cards | Return Rate, Warranty Cost | Return Policy Engine | Finance | 8% |
| CX-004 | Loyalty Program | Program Builder | Loyalty Score | Retention Engine | Sales | 8% |
| CX-005 | Referral Program | Campaign Builder | Referral Rate | Referral Engine | Marketing | 8% |
| CX-006 | Customer Feedback Prioritization | Feedback Board | Feature Requests | Feedback Priority | Product | 8% |
| CX-007 | Community Strategy | Community Planner | Community Growth | Engagement Engine | Marketing | 7% |
| CX-008 | Customer Education | Content Planner | Product Adoption | Adoption Engine | Product | 6% |
| CX-009 | Churn Prevention | Risk Cards | Churn Rate | Retention Engine | Sales | 10% |
| CX-010 | Brand Crisis Response | Crisis Scenarios | Brand Trust, Sentiment | Crisis Engine | Company | 12% |
| CX-011 | VIP Customer Strategy | Opportunity Cards | CLV, Loyalty | Customer Value Engine | Sales | 5% |
| CX-012 | Quarter CX Approval | Executive Approval | CX Locked | Quarter Commit | Company | 10% |

Score column sums to **100%** ✓

> ⚠️ **Gap:** every "Formula / Logic" entry here names an *engine* (Retention Engine, Referral
> Engine, Crisis Engine, …) rather than stating a formula. **None of these engines are specified
> anywhere in the source set.** All 12 CX decisions are therefore unimplementable as written.
> Tracked in `10-implementation-gaps.md`.

## 3. CX variables

| Variable | Initial | Formula | Updated By | Scoring Impact |
|---|---|---|---|---|
| Customer Satisfaction (CSAT) | 78 | `Positive Experiences ÷ Total Experiences × 100` | CX | 15% |
| Net Promoter Score (NPS) | 32 | `% Promoters − % Detractors` | CX | 10% |
| Customer Loyalty | 55 | Loyalty Engine | CX | 8% |
| Brand Trust | 55 | Trust Engine | CX | 10% |
| Brand Reputation | 58 | Reputation Engine | CX | 8% |
| Churn Rate | 6% | `Lost Customers ÷ Active Customers × 100` | CX | 12% |
| Repeat Purchase Rate | 18% | `Repeat Customers ÷ Active Customers × 100` | CX | 8% |
| Referral Rate | 9% | `Referred Customers ÷ Active Customers × 100` | CX | 6% |
| Community Members | 1,200 | `Previous + New Members` | CX | 4% |
| Product Adoption | 62 | `Active Feature Usage ÷ Active Customers × 100` | CX | 5% |
| Average Resolution Time | 24 hrs | `Total Resolution Time ÷ Tickets` | CX | 3% |
| First Contact Resolution | 72% | `First Contact Resolved ÷ Total Tickets × 100` | CX | 3% |
| Return Rate | 2.1% | `Returned Units ÷ Units Sold × 100` | CX | 4% |
| Warranty Claims | 1.8% | `Warranty Claims ÷ Units Sold × 100` | CX | 2% |
| Customer Lifetime Value (CLV) | Engine | `AOV × Purchase Frequency × Customer Lifespan` | Engine | 8% |
| Social Sentiment | 62 | `Positive Mentions − Negative Mentions` | Engine | 4% |

## 4. CX formulas (consolidated restatement)

| Variable | Formula |
|---|---|
| Customer Satisfaction | `Positive Experiences ÷ Total Experiences × 100` |
| NPS | `% Promoters − % Detractors` |
| Churn Rate | `Lost Customers ÷ Active Customers × 100` |
| Retention Rate | `Active Customers ÷ Previous Customers × 100` |
| Referral Rate | `Referred Customers ÷ Active Customers × 100` |
| Product Adoption | `Active Feature Users ÷ Active Customers × 100` |
| Customer Lifetime Value | `Average Order Value × Purchase Frequency × Customer Lifespan` |
| Brand Trust | `Previous Trust + Positive Experiences − Negative Experiences` |
| Community Growth | `New Members − Inactive Members` |
| Social Sentiment | `Positive Mentions − Negative Mentions` |

> These are **ratio definitions**, not decision-impact formulas. They tell you how to *compute a
> KPI from counts*, but nothing in the document specifies how a student's CX decision changes
> those counts. That link is the missing piece.

## 5. CX dependency matrix

| CX Decision | Finance | Marketing | Product | Sales | Operations |
|---|---|---|---|---|---|
| Support Strategy | ❌ | ❌ | ❌ | ❌ | ❌ |
| Complaint Resolution | ❌ | ❌ | ✅ | ❌ | ❌ |
| Return & Warranty | ✅ | ❌ | ✅ | ❌ | ✅ |
| Loyalty Program | ❌ | ✅ | ❌ | ✅ | ❌ |
| Referral Program | ❌ | ✅ | ❌ | ✅ | ❌ |
| Customer Feedback | ❌ | ❌ | ✅ | ❌ | ❌ |
| Community Strategy | ❌ | ✅ | ❌ | ❌ | ❌ |
| Customer Education | ❌ | ❌ | ✅ | ❌ | ❌ |
| Churn Prevention | ❌ | ❌ | ❌ | ✅ | ❌ |
| Brand Crisis | ✅ | ✅ | ✅ | ✅ | ✅ |
| VIP Strategy | ❌ | ❌ | ❌ | ✅ | ❌ |

## 6. Hidden CX engine variables

| Hidden Variable | Purpose |
|---|---|
| Customer Health Score | Overall customer relationship quality |
| Brand Advocacy Score | Probability of recommending the brand |
| Customer Trust Score | Trust accumulated over time |
| Customer Happiness Index | Emotional satisfaction |
| Product Adoption Score | Depth of product usage |
| Community Engagement Score | Community activity level |
| Churn Risk Score | Probability of losing customers |
| Escalation Risk | Probability of issues becoming public |
| Review Score Momentum | Trend of online ratings |
| Word-of-Mouth Index | Organic recommendation strength |
| Service Quality Index | Overall support effectiveness |
| Brand Sentiment Index | Public perception across channels |

## 7. CX scoring engine — variable → trait mapping

| Variable | Influences |
|---|---|
| CSAT | Customer-Centric Thinking, Decision Quality |
| NPS | Brand Building, Long-Term Thinking |
| Brand Trust | Strategic Thinking, Crisis Management |
| Churn Rate | Problem Solving, Customer-Centric Thinking |
| Referral Rate | Brand Building |
| Repeat Purchase | Long-Term Thinking |
| Community Growth | Strategic Thinking |
| Product Adoption | Customer-Centric Thinking |
| Social Sentiment | Crisis Management, Brand Building |
| CLV | Strategic Thinking, Long-Term Growth |

## 8. ⭐ Signature feature — Dynamic Customer Stories

Instead of dashboards full of tickets, every quarter the student receives dynamic customer
stories such as:

- A viral influencer complaint after a product failure
- A request from thousands of users for a new feature
- A spike in warranty claims after a manufacturing issue
- A Reddit thread praising or criticising the product
- A competitor offering free replacements to your customers

The student responds strategically, and those decisions ripple into Product, Marketing, Sales,
Operations, and Finance.

## 9. Workspace rhythm

For consistency with the other workspaces: keep **12 decisions** and make "Quarter CX Approval"
the final step that locks all CX decisions before the simulation advances.

Every workspace follows the same rhythm:

```
analyze → decide → approve → execute
```
