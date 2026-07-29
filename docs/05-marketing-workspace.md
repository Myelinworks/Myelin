# Marketing Workspace — Decision Matrix (Base Impact)

> Source: `Marketing_Workspace_Decision_Matrix_Base_Impact.pdf`

## How to read this matrix

**These percentages do NOT mean "Sales always increase by 15%."** They represent the
**maximum base influence** a decision can exert **before** the simulation applies contextual
modifiers.

```
Decision × Current Company State × Market State = Actual Result
```

### Canonical worked example — Increase Google Ads Budget

| Step | Value |
|---|---|
| Base Sales Impact | +15% |
| Brand Strength Modifier | × 0.9 |
| Market Saturation Modifier | × 0.6 |
| Inventory Availability Modifier | × 1.0 |
| Competitor Activity Modifier | × 0.8 |
| **Actual Sales Increase** | **15% × 0.9 × 0.6 × 1.0 × 0.8 = 6.48%** |

> **This 6.48% figure is the canonical validation case for the decision engine.**
> A unit test asserting this result should be the first test written.

### The four modifiers

A modifier is a factor that changes the effectiveness of a student's decision. The four named
in this document are:

1. **Brand Strength**
2. **Market Saturation**
3. **Inventory Availability**
4. **Competitor Activity**

These live in a `modifiers` table keyed on `(company_id, quarter_id, modifier_key)`, batch-fetched
at the start of workspace processing.

> ⚠️ **Gap:** this document does not specify how each modifier's numeric value is *derived* from
> company state. The `0.9 / 0.6 / 1.0 / 0.8` values in the worked example are illustrative inputs,
> not a formula. See `09-calibration-engine.md` for related lookup tables that may serve as the
> derivation source, and `10-implementation-gaps.md`.

---

## Matrix 1 — Channel Budget Decisions

| Student Decision | Marketing | Sales | Finance | Operations | Manufacturing | Supply Chain | HR | Customer Support | Product | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| Increase Google Ads Budget | +20% | +15% | −8% | +5% | +6% | +3% | +2% | +4% | 0% | +7% |
| Increase Meta Ads Budget | +18% | +12% | −7% | +4% | +5% | +3% | +2% | +5% | 0% | +6% |
| Increase LinkedIn Ads | +10% | +9% | −5% | +2% | +2% | +1% | +1% | +1% | 0% | +4% |
| Increase SEO Budget | +15% | +10%* | −4% | +2% | +2% | +1% | +3% | +1% | +4% | +10% |
| Increase Content Marketing | +16% | +8% | −5% | +2% | +2% | +1% | +2% | +2% | +6% | +8% |
| Increase Influencer Budget | +22% | +14% | −9% | +3% | +4% | +2% | +1% | +8% | 0% | +10% |
| Increase PR Budget | +18% | +5% | −6% | +1% | +1% | 0% | +1% | +4% | 0% | +12% |
| Increase Email Marketing | +10% | +12% | −3% | +3% | +3% | +2% | +1% | +5% | 0% | +5% |
| Increase Referral Budget | +12% | +16% | −4% | +4% | +3% | +2% | +1% | +2% | 0% | +6% |
| Sponsor Events | +20% | +8% | −10% | +2% | +2% | +1% | +3% | +3% | 0% | +10% |

\* SEO's Sales impact is asterisked in the source, indicating a delayed/compounding effect rather
than an immediate one. See `12-quarter-1-reference.md` § Content/SEO for the SEO Asset mechanic.

## Matrix 2 — Pricing & Promotion Decisions

| Decision | Marketing | Sales | Finance | Operations | Manufacturing | Supply Chain | HR | Customer Support | Product | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| 10% Discount | +12% | +25% | −18% | +15% | +20% | +15% | +3% | +10% | 0% | +5% |
| Bundle Products | +8% | +15% | −8% | +8% | +10% | +8% | 0% | +4% | +3% | +4% |
| Free Shipping | +10% | +18% | −12% | +10% | +8% | +18% | 0% | +6% | 0% | +3% |
| Premium Pricing | −5% | −8% | +15% | −6% | −5% | −5% | 0% | −2% | +2% | +8% |

## Matrix 3 — Brand Decisions

| Decision | Marketing | Sales | Finance | Operations | Manufacturing | Supply Chain | HR | Customer Support | Product | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| Premium Brand Positioning | +15% | +8% | +12% | −3% | +4% | +2% | +2% | +2% | +10% | +15% |
| Mass Market Positioning | +20% | +18% | −6% | +15% | +18% | +15% | +5% | +8% | −4% | +6% |
| Sustainability Campaign | +12% | +6% | −5% | +2% | +5% | +4% | +2% | +2% | +5% | +10% |

## Matrix 4 — Team Decisions

| Decision | Marketing | Sales | Finance | Operations | Manufacturing | Supply Chain | HR | Customer Support | Product | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| Hire Marketing Staff | +18% | +5% | −10% | 0% | 0% | 0% | +15% | 0% | 0% | +4% |
| Fire Marketing Staff | −20% | −6% | +8% | 0% | 0% | 0% | −18% | 0% | 0% | −5% |
| Employee Training | +12% | +5% | −4% | 0% | 0% | 0% | +10% | +1% | +2% | +4% |
| Outsource Agency | +15% | +8% | −7% | 0% | 0% | 0% | −4% | 0% | 0% | +3% |

## Matrix 5 — Market Expansion Decisions

| Decision | Marketing | Sales | Finance | Operations | Manufacturing | Supply Chain | HR | Customer Support | Product | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| Enter New City | +18% | +15% | −10% | +12% | +15% | +18% | +6% | +5% | +3% | +15% |
| Enter New Country | +25% | +20% | −18% | +20% | +22% | +25% | +12% | +10% | +8% | +25% |
| Target Enterprise | +10% | +12% | +8% | +5% | +4% | +2% | +3% | +2% | +3% | +8% |
| Target Students | +18% | +16% | −5% | +8% | +10% | +8% | +2% | +5% | +2% | +4% |

---

## Implementation note

This matrix gives **base impact percentages per (decision, department)**. It does **not** give:

- The spend→base-impact curve (i.e. how much spend triggers "Increase Google Ads Budget")
- The modifier derivation formulas

For the actual spend-driven lead-generation formulas that the Q1–Q4 reports validate against,
see `12-quarter-1-reference.md` § Marketing. Those are **different formulas** from this matrix —
the matrix is a percentage-influence model, while Q1–Q4 use power-law lead formulas
(`Leads = Constant × Spend^Exponent`). **These two models must be reconciled before implementation.**
Tracked in `10-implementation-gaps.md`.
