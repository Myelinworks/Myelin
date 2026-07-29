# CEO Scoring Methodology

> Source: `SCORING_METHODOLOGY.pdf`
> *A reusable rubric for grading any quarter's allocation decisions*

## Purpose

Defines how a student's quarterly allocation decisions are converted into a single **CEO Score
out of 100**. Designed to be applied **identically every quarter** — Q1, Q2, Q3, Q4 — so scores
are comparable across a student's own progression and across different students' playthroughs.
Nothing in this methodology is specific to any one quarter's numbers.

## The master formula

```
Final Score = Σ(Trait Points Earned, across all 7 traits) + Σ(Modifiers)

where:
  Trait Points Earned = Trait Weight × (fraction of that trait's 3 sub-criteria satisfied)
```

Each trait is scored out of its own weight by checking **3 sub-criteria**, each worth roughly
one-third of that trait's total weight. A trait earns full marks only when all 3 sub-criteria are
clearly met.

## The 7 traits and their weights

| Trait | Weight | Why this weight |
|---|---|---|
| **Systems Thinking** | **20** (highest) | Recognising and fixing cross-department dependencies is the single hardest, highest-value skill this simulation is built to teach — the entire redesign from soft bonuses to hard gates (Sales Capacity, R&D's Conversion Ceiling, Operations' Available to Sell) exists to test this trait specifically |
| Strategic Thinking | 15 | Whether a coherent, followed-through thesis exists behind the numbers |
| Adaptability | 15 | Whether the student changes course when the business itself changes underneath a prior decision |
| Risk Management | 15 | Whether cash, debt, and downside exposure are being actively managed, not just hoped for |
| Capital Allocation | 15 | Whether spend is matched to marginal return, department by department |
| Leadership | 10 | Real, but harder to observe directly from allocation numbers alone — shows more in process (how a student reacts to bad news) than in the spend table itself |
| Long-Term Thinking | 10 | Real, but in any single quarter can only be evidenced by investments whose payoff hasn't arrived yet — inherently a smaller, earlier signal |

**Weights sum to exactly 100**, so trait scores map directly onto the final scale without a
separate conversion step.

## The 21 sub-criteria — what actually gets checked

*This section is meant to be reused verbatim every quarter.*

### Strategic Thinking (15 pts)
1. A stated, coherent thesis exists behind the allocation (not a random or default split)
2. The thesis is genuinely followed through in the actual numbers, not abandoned partway
3. The thesis correctly targets wherever the quarter's real constraint actually is (demand, capacity, conversion ceiling, or cash)

### Leadership (10 pts)
1. Decisions are made without excessive hedging or indecision
2. The student is proactive — raising issues or opportunities themselves, not only reacting when prompted
3. The student owns the trade-offs their allocation makes, rather than ignoring or downplaying them

### Adaptability (15 pts)
1. The student recognises when a prior quarter's approach no longer fits the current situation
2. The change made is driven by evidence (results, audits, carryover data), not arbitrary impulse
3. The change, once made, is well-executed — not just attempted

### Systems Thinking (20 pts)
1. Cross-department dependencies are correctly identified (e.g. leads vs. capacity, conversion vs. quality ceiling, demand vs. supply)
2. Departments are sized in coordination with each other, not decided in isolation
3. No single department is left as an unaddressed bottleneck once the rest of the allocation is finalised

### Risk Management (15 pts)
1. A real cash or debt safety margin exists after the allocation is made
2. Downside exposure is bounded, not open-ended, if assumptions prove wrong
3. The level of risk taken is proportionate to the evidence available at the time of the decision

### Capital Allocation (15 pts)
1. Marginal spend in each department roughly matches that department's marginal return
2. No channel or department is funded past the point where extra spend stops producing extra usable output (a hard cap, a capacity ceiling, or a demand ceiling)
3. No channel or department is left funded below the level that proven demand or a known constraint would justify

### Long-Term Thinking (10 pts)
1. At least one investment is made whose payoff is not this quarter's (e.g. a compounding score, a long-horizon mechanic)
2. That investment is not sacrificed entirely for short-term gain when the two compete for the same budget
3. The long-term investment is sized proportionately to the company's current stage and cash position

## Scoring each sub-criterion

| Sub-criterion result | Fraction credited |
|---|---|
| Clearly met | 1/3 of trait weight |
| Partially met | 1/6 of trait weight |
| Not met | 0 |

### Worked example — Systems Thinking (weight 20)

```
Sub-criterion 1 clearly met    → 20/3  = 6.67
Sub-criterion 2 clearly met    → 20/3  = 6.67
Sub-criterion 3 partially met  → 20/6  = 3.33
Trait Points Earned            ≈ 16.7
```

In practice, round to whole or half points using judgment on the evidence — the fractional math
is scaffolding, not a rigid computation to the decimal.

## The modifier layer — why it exists separately

The 7 traits measure the **quality of thinking** behind a decision. Modifiers measure
**execution precision** — whether the numbers that resulted from that thinking were actually
clean and free of waste. A student can reason well (high trait scores) while still leaving real
inefficiency in the numbers, or can execute cleanly on a mediocre plan. Keeping these separate
stops one dimension from masking the other.

### Standard modifier triggers (apply every quarter)

| Modifier | Trigger condition (the checkable rule) | Points |
|---|---|---|
| Profitability achieved | `Net Cash Flow > 0` for the quarter | **+3** |
| Perfect channel match | Any channel with a hard cap (e.g. Referral) is funded to exactly its cap cost, with zero over- or under-spend | **+2** (per channel achieving this) |
| Zero capacity waste | `Leads Used = Leads Generated` (Sales Capacity was not a binding, wasteful constraint) | **+2** |
| Zero supply waste | `Units Sold` lands within a small, deliberate buffer of `Available to Sell` (no large unplanned inventory carryover) | **+2** |
| Compounding asset cut | Any compounding asset (Brand Score, SEO Asset, Buzz Score, Innovation Score) receives materially less investment than the prior quarter, with no strategic justification stated | **−2** |
| Ceiling/gate under-shot | The gap between a department's raw, uncapped potential and the actual hard-gated result exceeds roughly **3 points/units** of the relevant metric (e.g. raw conversion rate vs. R&D's Conversion Ceiling) | **−2** |
| Cash buffer breached | The mandatory Working Capital Buffer is spent into during the quarter | **−3** |
| Debt taken without justification | A loan or credit line is used without a stated reason tied to a specific, funded growth plan | **−2** |

**Modifiers are additive and uncapped in either direction** — apply every one that genuinely
triggers based on that quarter's actual numbers.

## Final aggregation

```
Final Score = (Σ Trait Points Earned, max 100) + (Σ Modifiers, can be positive or negative)
```

The final score is **not capped at 100 by formula**, but in practice a genuinely clean,
well-reasoned quarter rarely exceeds it by much — a score meaningfully above 100 should prompt a
recheck of whether a modifier was applied too generously.

## Score bands

| Band | Range | Interpretation |
|---|---|---|
| **Exceptional** | 90–100 | Outperformed the model's own built-in assumptions — caught and fixed a structural problem **before** it cost real money, proactively rather than reactively |
| **Strong** | 75–89 | Real, demonstrated improvement and correct instincts, with identifiable remaining inefficiencies |
| **Competent** | 60–74 | Sound but **reactive** decision-making — fixing problems only after they're pointed out, rather than anticipating them |
| **Weak** | 40–59 | Siloed, short-term decisions that ignore visible risk signals |
| **Poor** | Below 40 | Allocation is incoherent enough that the company's survival past a few quarters is genuinely in question |

### The most important line to apply consistently

**Strong vs. Exceptional:** a quarter only earns "Exceptional" if problems were **caught and
corrected before being pointed out** — proactive discovery, not responsive correction. Nearly
every real playthrough, even a very good one, tends to land in "Strong" for exactly this reason:
reactive correction, however fast and well-executed, is still reactive.

## How to apply this each quarter

1. **Gather the quarter's final numbers** before scoring: Net Cash Flow, Leads Used vs. Leads Generated, Units Sold vs. Available to Sell, any channel spend vs. its cap, and what (if anything) was cut from the prior quarter's investment mix.
2. **Score each of the 7 traits** against its 3 sub-criteria, using evidence from that quarter's actual decisions and results.
3. **Apply every modifier that genuinely triggers** based on the checkable conditions above — do not apply a modifier on vibes alone.
4. **Sum** trait points and modifiers for the Final Score.
5. **Place the score in its band**, and use the band description — not just the number — when explaining the result to the student.

This methodology is intended to be copy-pasted into every quarter's report unchanged, with only
the evidence and resulting numbers varying.

---

## Crisis addendum (from `11-crisis-system.md`)

Additional modifiers that apply only in crisis quarters:

| Modifier | Trigger condition | Points |
|---|---|---|
| Crisis fully neutralized | The event's core mechanism (dampening, penalty, or capacity cut) reduced to zero net effect | +3 |
| Crisis-proofed by prior investment | Final Capacity Multiplier ≥ 0.90 without needing the expensive Choice A response | +3 |
| Structural improvement made | Choice B (Supply Shock) selected, converting a crisis into a permanent Supplier Reliability gain | +2 |
| Crisis ignored | ₹0 spent on the relevant response line when a severe event occurs | −4 |

## Q4 addendum (from `16-quarter-4-endgame.md`)

Q4 adds a dedicated **Exit & Growth Judgment** trait (15 pts, either replacing one standard
trait's weight or added as a Q4-only category), plus these modifiers:

| Modifier | Condition | Points |
|---|---|---|
| Covenant hit | Path A chosen AND covenant hit | +5 |
| Covenant missed | Path A chosen AND covenant missed | −8 |
| Correct rejection | Path B rejected with correct reasoning, by a company whose true continuation value exceeds the offer | +4 |
| Correct acceptance | Path B accepted by a company whose momentum was weak/flat, where the offer was actually fair or generous | +4 |
| Value left on table | Path B accepted by a company with strong momentum, leaving a large true-value gap unexamined | −3 |
| Deliberate independence | Path C chosen with explicit, stated reasoning for rejecting A and B | +2 |
