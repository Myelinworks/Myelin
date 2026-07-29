# Product Workspace

> Source: `product_workspace_.pdf`

## Objective

Enable students to build, improve, validate, launch, and manage products while balancing
customer needs, innovation, quality, cost, and time-to-market.

## 1. Product decisions

| ID | Decision | Interaction | Variables Updated | Formula / Logic | Affects | Score |
|---|---|---|---|---|---|---|
| PRO-001 | Select Market Opportunity | Opportunity Cards | Opportunity Score, Product Pipeline | `Opportunity × Market Demand` | Product | 8% |
| PRO-002 | Create New Product | Product Studio | Product Portfolio | Creates New Product | Marketing, Finance | 12% |
| PRO-003 | Prioritize Features | Priority Board | Feature Progress | `Completed ÷ Planned Features` | Marketing, Customer Satisfaction | 10% |
| PRO-004 | R&D Investment | Investment Cards | Innovation Score | `Previous + R&D Investment` | Finance | 8% |
| PRO-005 | Quality Strategy | Trade-off Cards | Product Quality | `Base + QA Investment` | Operations | 8% |
| PRO-006 | Approve Prototype | Approval | Prototype Status | `Development = 100%` | Marketing | 6% |
| PRO-007 | Beta Testing | Beta Program | Feedback Score | Feedback Collected | Customer Success | 6% |
| PRO-008 | Launch Product | Executive Approval | Product Status | `Readiness ≥ Threshold` | Sales, Marketing, Operations | 15% |
| PRO-011 | Customer Feedback Prioritization | Decision Board | Roadmap Priority Score | Feature Priority | Customer Success | 5% |
| PRO-012 | Retire Product | Approval | Product Portfolio | Product Lifecycle | Finance | 5% |

> ⚠️ **Note:** IDs PRO-009 and PRO-010 are absent from the source. Score column sums to 83%,
> not 100% — the missing 17% presumably belongs to the two absent decisions. Tracked in
> `10-implementation-gaps.md`.

> ⚠️ **Gap:** the `Readiness ≥ Threshold` condition in PRO-008 does not specify the threshold value.

## 2. Product variables

| Variable | Initial Value | Updated By |
|---|---|---|
| Product Portfolio | 1 Product | Product |
| Product Quality | 72 | Product |
| Feature Completion | 78% | Product |
| Innovation Score | 50 | Product |
| Product Rating | 4.3 | Product |
| Product Cost | ₹4,500 | Product |
| Product Price | ₹10,000 | Finance |
| Product Stage | Released | Product |
| Product Readiness | 100% | Product |
| Product Demand | 60 | Simulation |

## 3. Product lifecycle — stage gating

| Stage | Marketing | Sales | Operations |
|---|---|---|---|
| Idea | Market Research | — | — |
| Research | Customer Validation | — | — |
| Prototype | Landing Page | — | — |
| Development | Coming Soon | — | — |
| Beta Testing | Waitlist | — | — |
| Manufacturing Ready | Launch Planning | — | Production Planning |
| Released | Full Campaign | Sales Enabled | Manufacturing Enabled |

This table is a **capability gate**: Sales and Operations are locked out entirely until the
`Released` stage.

## 4. Core formulas (first statement)

| Variable | Formula |
|---|---|
| Product Quality | `Base Quality + QA Investment + R&D Bonus` |
| Feature Completion | `Completed Features ÷ Planned Features × 100` |
| Innovation Score | `Previous Score + R&D Investment` |
| Product Readiness | `(Development + Testing + Manufacturing) ÷ 3` |
| Product Demand | `Brand Awareness + Marketing Impact + Product Quality` |
| Product Rating | `Customer Satisfaction + Product Quality + Reliability` |
| Product ROI | `Revenue − Development Cost` |

## 5. Extended formula set (second, expanded statement)

The source restates the formulas later with additional terms. **Where the two conflict, this
expanded set is the later/fuller statement:**

| Variable | Formula |
|---|---|
| Product Quality | `Base Quality + QA Investment + R&D Bonus − Technical Debt` |
| Innovation Score | `R&D Investment + New Features + Technology Adoption` |
| Feature Completion | `Completed Features ÷ Planned Features × 100` |
| Product Readiness | `(Development + Testing + Manufacturing) ÷ 3` |
| Product Rating | `Customer Experience + Quality + Reliability` |
| Demand Score | `Market Fit + Brand Awareness + Marketing Impact` |
| Product Health | `Quality + Customer Satisfaction + Demand` |
| Product Development Cost | `Feature Cost + R&D Cost + Testing Cost` |
| Time to Market | `Remaining Development ÷ Development Velocity` |
| Product ROI | `Revenue Generated − Development Cost` |

> ⚠️ **Conflict:** §4 and §5 give different formulas for Product Quality, Innovation Score,
> Product Rating, and Demand. Neither version specifies coefficients or units for its terms
> (e.g. is `QA Investment` in rupees, lakhs, or a normalised score?). **All of these are
> unimplementable as written.** Tracked in `10-implementation-gaps.md`.
>
> Contrast with `12-quarter-1-reference.md` § R&D, which gives fully-specified, dimensionally
> coherent versions of the same concepts (`Quality Score += 6 × x^0.5` where x = spend in ₹ lakhs).
> **The Q1 reference formulas should be preferred.**

## 6. Product scoring weights

| Skill | Weight |
|---|---|
| Strategic Thinking | 25% |
| Customer-Centric Thinking | 20% |
| Innovation | 20% |
| Long-Term Thinking | 15% |
| Resource Utilization | 10% |
| Decision Quality | 10% |

## 7. Product dependency matrix

| Product Decision | Finance | Marketing | Sales | Operations | Customer Success |
|---|---|---|---|---|---|
| Product Creation | ✅ | ✅ | ❌ | ❌ | ❌ |
| Feature Priority | ❌ | ✅ | ❌ | ❌ | ✅ |
| R&D Investment | ✅ | ❌ | ❌ | ❌ | ❌ |
| Quality Strategy | ❌ | ✅ | ❌ | ✅ | ✅ |
| Prototype Approval | ❌ | ✅ | ❌ | ❌ | ❌ |
| Beta Testing | ❌ | ✅ | ❌ | ❌ | ✅ |
| Launch Approval | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manufacturing Approval | ❌ | ❌ | ❌ | ✅ | ❌ |
| Product Retirement | ✅ | ✅ | ✅ | ✅ | ✅ |
