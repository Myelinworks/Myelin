# Finance Workspace Specification

> Source: `finance_workspace.pdf`

## 1. Decision specification (FIN-001 … FIN-007, fully specified)

These seven carry a complete spec row: UI component, input range, default, variables updated,
formula, and effect chain.

### FIN-001 — Department Budget Allocation

| Field | Value |
|---|---|
| UI Component | Sliders |
| Input Range | ₹0 – Available Budget |
| Default | System Recommendation |
| Variables Updated | Department Budgets, Cash |
| **Formula** | `Budget ≤ Available Cash` |
| Immediate Effect | Budgets Updated |
| Secondary Effect | Department Capacity |
| Long-Term Effect | Revenue, Profit, Valuation |
| Dependencies | All Departments |

Scoring weights: Strategic Thinking 35% · Resource Allocation 30% · Risk Management 5% · Financial Discipline 20% · Long-Term Thinking 10%

### FIN-002 — Emergency Cash Reserve

| Field | Value |
|---|---|
| UI Component | Slider |
| Input Range | ₹0 – ₹50 L |
| Default | ₹15 L |
| Variables Updated | Reserve Cash, Cash |
| **Formula** | `Cash Reserve ÷ Cash` |
| Immediate Effect | Spending Power ↓ |
| Secondary Effect | Liquidity ↑ |
| Long-Term Effect | Survival ↑ |
| Dependencies | Finance |

Scoring weights: Strategic 10% · Resource 15% · Risk 40% · Financial Discipline 25% · Long-Term 10%

### FIN-003 — Capital Expenditure

| Field | Value |
|---|---|
| UI Component | Multi-Select |
| Options | Office, Equipment, Software, Automation |
| Default | None |
| Variables Updated | Fixed Assets, Cash |
| **Formula** | `Cash − CapEx` |
| Immediate Effect | Cash ↓ |
| Secondary Effect | Productivity ↑ |
| Long-Term Effect | Efficiency ↑ |
| Dependencies | Operations |

Scoring weights: Strategic 20% · Resource 20% · Risk 10% · Financial Discipline 10% · Long-Term 40%

### FIN-004 — Cost Optimisation

| Field | Value |
|---|---|
| UI Component | Dropdown |
| Options | None, Mild, Moderate, Aggressive |
| Default | None |
| Variables Updated | Burn Rate, Morale |
| **Formula** | `Expenses × Reduction %` |
| Immediate Effect | Expenses ↓ |
| Secondary Effect | Morale ↓ |
| Long-Term Effect | Runway ↑ |
| Dependencies | HR, Operations |

Scoring weights: Strategic 20% · Resource 15% · Risk 25% · Financial Discipline 30% · Long-Term 10%

> ⚠️ **Gap:** the actual `Reduction %` values for Mild / Moderate / Aggressive are **not specified**.

### FIN-005 — Debt Utilisation

| Field | Value |
|---|---|
| UI Component | Dropdown |
| Options | ₹0, ₹10 L, ₹25 L, ₹50 L |
| Default | ₹0 |
| Variables Updated | Debt, Cash |
| **Formula** | `Cash + Loan` |
| Immediate Effect | Cash ↑ |
| Secondary Effect | Interest ↑ |
| Long-Term Effect | Credit Score ↓ |
| Dependencies | Investor Engine |

Scoring weights: Strategic 15% · Resource 10% · Risk 45% · Financial Discipline 20% · Long-Term 10%

> Interest rate is given in `09-calibration-engine.md` as **10% p.a.**

### FIN-006 — Hiring Budget Approval

| Field | Value |
|---|---|
| UI Component | Slider |
| Input Range | ₹0 – ₹20 L |
| Default | ₹8 L |
| Variables Updated | Hiring Budget, Payroll |
| **Formula** | `Payroll + New Salaries` |
| Immediate Effect | Hiring ↑ |
| Secondary Effect | Burn ↑ |
| Long-Term Effect | Productivity ↑ |
| Dependencies | HR |

Scoring weights: Strategic 20% · Resource 30% · Risk 10% · Financial Discipline 10% · Long-Term 30%

### FIN-007 — Growth Investment

| Field | Value |
|---|---|
| UI Component | Slider |
| Input Range | ₹0 – ₹50 L |
| Default | ₹20 L |
| Variables Updated | Growth Budget |
| **Formula** | `Investment Distribution` |
| Immediate Effect | Cash ↓ |
| Secondary Effect | Growth ↑ |
| Long-Term Effect | Market Share ↑ |
| Dependencies | Marketing, Product |

Scoring weights: Strategic 35% · Resource 25% · Risk 10% · Financial Discipline 10% · Long-Term 20%

## 2. Finance variables

| ID | Variable | Type | Initial | Updated By | Used By |
|---|---|---|---|---|---|
| FIN-V001 | Cash Available | Currency | ₹1.56 Cr | Finance Engine | All Workspaces |
| FIN-V002 | Department Budget | Currency | ₹0 | FIN-001 | All Departments |
| FIN-V003 | Monthly Burn | Currency | ₹26 L | Finance Engine | Dashboard |
| FIN-V004 | Quarterly Burn | Currency | ₹78 L | Finance Engine | Dashboard |
| FIN-V005 | Reserve Cash | Currency | ₹15 L | FIN-002 | Finance |
| FIN-V006 | Credit Line | Currency | ₹50 L | Finance | Finance |
| FIN-V007 | Outstanding Debt | Currency | ₹0 | FIN-005 | Finance |
| FIN-V008 | Interest Expense | Currency | ₹0 | Finance Engine | Finance |
| FIN-V009 | Capital Expenditure | Currency | ₹0 | FIN-003 | Operations |
| FIN-V010 | Fixed Assets | Currency | ₹45 L | Finance | Dashboard |
| FIN-V011 | Operating Expenses | Currency | ₹0 | Finance Engine | Dashboard |
| FIN-V012 | Hiring Budget | Currency | ₹8 L | FIN-006 | HR |
| FIN-V013 | Growth Budget | Currency | ₹20 L | FIN-007 | Marketing, Product |
| FIN-V014 | Cash Runway | Months | 6 | Finance Engine | Dashboard |
| FIN-V015 | Company Valuation | Currency | ₹20 Cr | Valuation Engine | Dashboard |
| FIN-V016 | Investor Confidence | Score | 60 | Simulation Engine | Fundraising |

## 3. Finance Engine formulas — **authoritative**

| Variable | Formula |
|---|---|
| Available Budget | `Opening Cash − Reserve Cash` |
| Closing Cash | `Opening Cash + Revenue − Total Expenses − Investments` |
| Monthly Burn | `Fixed Costs + Variable Costs` |
| Quarterly Burn | `Monthly Burn × 3` |
| Cash Runway | `Cash Available ÷ Monthly Burn` |
| Debt Ratio | `Outstanding Debt ÷ Total Assets` |
| Budget Utilisation | `Total Budget Used ÷ Total Budget Allocated` |
| Growth Investment Ratio | `Growth Budget ÷ Total Budget` |
| Reserve Ratio | `Reserve Cash ÷ Cash Available` |
| Operating Margin | `(Revenue − Operating Expenses) ÷ Revenue` |

## 4. Finance dependency matrix

| Finance Decision | Marketing | Product | Sales | Operations | HR | Company |
|---|---|---|---|---|---|---|
| Budget Allocation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cash Reserve | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Capital Expenditure | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Cost Optimisation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Debt Utilisation | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Hiring Budget | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Growth Investment | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |

## 5. Overall Finance scoring matrix

| Evaluation Dimension | Weight |
|---|---|
| Strategic Thinking | 35% |
| Resource Allocation | 30% |
| Risk Management | 15% |
| Financial Discipline | 10% |
| Long-Term Thinking | 10% |

> Note: these sum to 100%. The per-decision weight columns in §1 are a separate, decision-level
> breakdown and are **not** the same as this workspace-level matrix.

## 6. Recommended full decision set (FIN-001 … FIN-015)

Design note from source: *"7 decisions are too few for a CEO simulation, and 20+ become
overwhelming. For Myelin, aim for 12–15 high-impact finance decisions."*

| ID | Decision | Type | Frequency | Difficulty | Cross-Dept Impact |
|---|---|---|---|---|---|
| FIN-001 | Department Budget Allocation | Slider | Quarterly | ⭐⭐⭐ | All Departments |
| FIN-002 | Emergency Cash Reserve | Slider | Quarterly | ⭐⭐ | All Departments |
| FIN-003 | Capital Expenditure (CapEx) | Multi-Select | Quarterly | ⭐⭐⭐ | Product, Operations |
| FIN-004 | Cost Optimisation Strategy | Dropdown | Quarterly | ⭐⭐⭐⭐ | All Departments |
| FIN-005 | Debt / Credit Utilisation | Dropdown | When Needed | ⭐⭐⭐⭐ | Company |
| FIN-006 | Hiring Budget Approval | Slider | Quarterly | ⭐⭐⭐ | People |
| FIN-007 | Growth Investment Allocation | Slider | Quarterly | ⭐⭐⭐⭐ | Marketing, Product, Sales |
| FIN-008 | Pricing Approval | Dropdown | Quarterly | ⭐⭐⭐⭐⭐ | Marketing, Sales, Product |
| FIN-009 | Production Budget Approval | Slider | Quarterly | ⭐⭐⭐⭐ | Operations |
| FIN-010 | Inventory Investment | Slider | Quarterly | ⭐⭐⭐ | Operations, Sales |
| FIN-011 | Dividend / Founder Withdrawal | Toggle | Rare | ⭐⭐⭐ | Cash, Investor Confidence |
| FIN-012 | Contingency Fund Allocation | Slider | Quarterly | ⭐⭐⭐ | Company |
| FIN-013 | Vendor Payment Strategy | Dropdown | Quarterly | ⭐⭐⭐ | Operations, Supplier Trust |
| FIN-014 | R&D Investment Approval | Slider | Quarterly | ⭐⭐⭐⭐ | Product |
| FIN-015 | Quarter Financial Approval | Confirm | End of Quarter | ⭐⭐⭐⭐⭐ | Entire Company |

### FIN-008 — Pricing Approval (detail)

Finance owns the final pricing decision rather than Marketing or Sales.

Choices: **Maintain Price · Increase 5% · Increase 10% · Decrease 5% · Decrease 10%**

Affects: Revenue · Demand · Gross Margin · Brand Positioning · Market Share

> Demand-change coefficients for each price step are in `09-calibration-engine.md` § Product Pricing.

### FIN-013 — Vendor Payment Strategy (detail)

Choices: **Pay Early · Pay On Time · Delay Payment**

Effects: Cash Flow · Supplier Reliability · Future Discounts · Production Risk

> ⚠️ **Gap:** no numeric coefficients specified for any of the three choices.

### FIN-015 — Quarter Financial Approval (detail)

At the end of each quarter the CEO reviews a financial summary before advancing. The system flags:

- Overspending
- Negative cash flow
- Low runway
- High inventory
- Budget overruns

The player then confirms the quarter. This reinforces financial accountability without requiring
accounting knowledge.

## 7. Final consolidated Finance Workspace (13 decisions)

Consolidations applied to keep the workspace focused:

- CapEx + R&D Investment → **"Strategic Investment"**
- Emergency Cash Reserve + Contingency Fund → **"Liquidity Management"**

Final list:

1. Department Budget Allocation
2. Liquidity Management
3. Strategic Investment
4. Cost Optimisation
5. Debt / Credit Utilisation
6. Hiring Budget Approval
7. Growth Investment Allocation
8. Pricing Approval
9. Production Budget Approval
10. Inventory Investment
11. Vendor Payment Strategy
12. Founder Withdrawal / Dividend
13. Quarter Financial Approval
