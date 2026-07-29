# Myelin — Simulation Design Reference (`backend/docs/`)

Canonical, machine-readable extraction of the Myelin simulation design source documents.
These files are the **specification of record** for the decision engine. Where a document
states a numeric coefficient, that coefficient is authoritative. Where a document states
only a qualitative effect, **no coefficient may be invented** — the corresponding decision
key must raise `NotImplementedError` with the reason recorded in `10-implementation-gaps.md`.

## Source → Markdown map

| # | Source file | Markdown file | Contents |
|---|---|---|---|
| 1 | `Myelin_Technical_Architecture_md.pdf` | [`01-technical-architecture.md`](01-technical-architecture.md) | Stack, deployment, cost, timeline, dual-pipeline overview |
| 2 | `Quater_flow.pdf` | [`02-quarter-flow-and-evidence-pipeline.md`](02-quarter-flow-and-evidence-pipeline.md) | Quarter execution order, cost taxonomy, Evidence Engine architecture |
| 3 | `__Product_launched.pdf` | [`03-company-load-state.md`](03-company-load-state.md) | PulseWear default seed state — all 11 state blocks |
| 4 | `finance_workspace.pdf` | [`04-finance-workspace.md`](04-finance-workspace.md) | FIN-001…015 decisions, FIN-V001…016 variables, formulas, dependencies |
| 5 | `Marketing_Workspace_Decision_Matrix_Base_Impact.pdf` | [`05-marketing-workspace.md`](05-marketing-workspace.md) | Base impact matrix (10 depts × 21 decisions), modifier chain |
| 6 | `product_workspace_.pdf` | [`06-product-workspace.md`](06-product-workspace.md) | PRO-001…012, lifecycle stages, formulas, dependencies |
| 7 | `sales_workspace.pdf` | [`07-sales-workspace.md`](07-sales-workspace.md) | SAL-001…012, variables, formulas, Negotiation Engine |
| 8 | `The_student_responds_strategically…pdf` | [`08-customer-experience-workspace.md`](08-customer-experience-workspace.md) | CX-001…012, variables, formulas, hidden CX engine |
| 9 | `calibration_engine.pdf` | [`09-calibration-engine.md`](09-calibration-engine.md) | Indian consumer-goods defaults, all 13 modifier lookup tables, variance model |
| 10 | `SCORING_METHODOLOGY.pdf` | [`10-scoring-methodology.md`](10-scoring-methodology.md) | 7 traits, 21 sub-criteria, modifier triggers, score bands |
| 11 | `CRISIS_SYSTEM_REFERENCE.pdf` | [`11-crisis-system.md`](11-crisis-system.md) | 4 crisis scenarios, all penalty/recovery formulas, crisis modifiers |
| 12 | `quarter_1.pdf` | [`12-quarter-1-reference.md`](12-quarter-1-reference.md) | **Master formula reference.** Every channel/line formula with worked Q1 numbers |
| 13 | `Q2_COMPLETE_REPORT.pdf` | [`13-quarter-2-reference.md`](13-quarter-2-reference.md) | Compounding mechanics, two Q2 variants, carryover chain |
| 14 | `q3.pdf` | [`14-quarter-3-reference.md`](14-quarter-3-reference.md) | Crisis quarter, all 4 consequence branches, balance sheets |
| 15 | `noob_vs_expert_q3.pdf` | [`15-q3-noob-vs-expert.md`](15-q3-noob-vs-expert.md) | Crisis-response calibration pairs (8 runs, shared baseline) |
| 16 | `q4.pdf` | [`16-quarter-4-endgame.md`](16-quarter-4-endgame.md) | Momentum Score, tier assignment, 3 term-sheet menus |
| — | *(derived)* | [`00-formula-index.md`](00-formula-index.md) | **Every formula in one place**, grouped by engine |
| — | *(derived)* | [`10-implementation-gaps.md`](10-implementation-gaps.md) | Decisions with no numeric coefficient — must raise `NotImplementedError` |

## Reading order for a new engineer

1. `01-technical-architecture.md` — what the system is
2. `02-quarter-flow-and-evidence-pipeline.md` — execution order (this defines engine call order)
3. `03-company-load-state.md` — seed state
4. `12-quarter-1-reference.md` — **the most important file**; contains the actual working formulas
5. `00-formula-index.md` — consolidated lookup
6. `10-implementation-gaps.md` — what must NOT be guessed

## Two conflicting company baselines — resolve before implementing

Source documents contain **two different companies**:

| | PulseWear (`03-company-load-state.md`) | Nadi Wear (`12`–`16`) |
|---|---|---|
| Capital raised | ₹2.00 Cr | ₹4.00 Cr |
| Cash at Q1 start | ₹1.56 Cr | ₹1.50 Cr |
| Selling price | ₹10,000 | ₹9,999 |
| Manufacturing cost | ₹4,500 | ₹3,250 |
| Gross margin | 55% | 67.5% |
| Fixed cost/quarter | ₹78 L (₹26 L/mo) | ₹23.50 L |
| Starting inventory | 1,920 units | 600 units |
| Starting customers | 530 active / 920 registered | 4,000 |
| Base conversion | — | 19% |

**PulseWear is the load-state spec; Nadi Wear is the worked-example spec.** All formulas in
`12`–`16` were calibrated against Nadi Wear numbers. Running those formulas against PulseWear's
state will not reproduce the documented results. This must be reconciled by the simulation
designer before Q1 can be validated — it is tracked in `10-implementation-gaps.md`.
