# Quarter 4 — Endgame, Momentum Score & Term Sheets

> Source: `q4.pdf`

Q4 is structurally different from Q1–Q3. It doesn't just run one more quarter of formulas — it
**evaluates the entire 4-quarter arc** and forces a final strategic decision about the company's
future.

---

## 1. The Momentum Score — the Q4 gating mechanism

Q4's available options are not the same for every company. What a team is *offered* in Q4 depends
on what they built across Q1–Q3, measured by a single composite:

```
Momentum Score = weighted composite of:
    Brand Score
    Innovation Score
    Quality Score
    Supplier Reliability
    Repeat Purchase Rate
    Cash Balance
    Net Cash Flow trend across Q1 → Q3
```

> ⚠️ **Gap:** the source names the seven inputs but **does not specify their weights**, their
> normalisation, or the exact tier cut-off values. This is the single most important missing
> formula for Q4 implementation. Tracked in `10-implementation-gaps.md`.

## 2. Tier assignment

The Momentum Score assigns the company to one of three tiers, and the tier determines **which
term sheets appear**:

| Tier | Meaning | What Q4 offers |
|---|---|---|
| **Strong momentum** | Compounding assets built and still growing | The full menu, including the most favourable terms |
| **Flat momentum** | Company survived but didn't compound | A reduced menu; the best options are withheld |
| **Weak momentum** | Assets neglected or eroded | The most constrained menu; some paths unavailable entirely |

**Design intent:** a team cannot decide in Q4 to have been a good company. The endgame options are
a *consequence* of Q1–Q3, not a fresh decision — which is what makes the earlier quarters'
"boring" compounding investments matter retroactively.

---

## 3. The three paths

Q4 presents three qualitatively different strategic postures. Each has its own term-sheet menu,
and each is scored differently.

### Path A — Debt-funded aggressive growth

Take on debt against a **covenant**: a specific, contractually-required performance threshold the
company must hit by end of Q4.

| Outcome | Scoring |
|---|---|
| Covenant hit | **+5** |
| Covenant missed | **−8** |

**Why the asymmetry:** the penalty is larger than the reward because a missed covenant in a real
company isn't just a bad quarter — it triggers lender control, forced asset sales, or insolvency.
The scoring is deliberately shaped so that taking Path A without a genuine, calculated basis for
hitting the covenant is a bad expected-value decision.

### Path B — Acquisition / exit

Accept an acquisition offer. The offer's size is set by the Momentum tier, but the **true
continuation value** of the company may be higher or lower than the offer.

| Outcome | Scoring |
|---|---|
| Correct rejection — rejected with correct reasoning by a company whose true continuation value exceeds the offer | **+4** |
| Correct acceptance — accepted by a company whose momentum was weak/flat, where the offer was actually fair or generous | **+4** |
| Value left on the table — accepted by a company with strong momentum, leaving a large true-value gap unexamined | **−3** |

**Why both accepting and rejecting can score +4:** there is no universally correct answer to an
exit offer. The skill being tested is whether the student **calculated their own continuation
value** and compared it against the offer — not which choice they landed on. A weak-momentum
company accepting a fair offer is making exactly as good a decision as a strong-momentum company
rejecting a lowball one.

### Path C — Deliberate independence

Reject both the debt and the acquisition, and continue operating on internally generated cash.

| Outcome | Scoring |
|---|---|
| Chosen with explicit, stated reasoning for rejecting A and B | **+2** |

**Why the reward is smaller:** Path C is the default outcome of doing nothing, so it only earns
points when it's an *articulated* choice rather than a passive one. The requirement for stated
reasoning is what separates deliberate independence from indecision.

---

## 4. The Exit & Growth Judgment trait

Q4 adds a **dedicated eighth trait** worth **15 points**, either replacing one standard trait's
weight or added as a Q4-only category.

This exists because the seven standard traits (`10-scoring-methodology.md`) all measure decisions
about *running* a company. None of them measure the distinct skill of deciding **what the company
should become** — whether to lever up, sell, or stay independent. That's a different judgment, and
Q4 is the only quarter where it can be tested.

---

## 5. Complete Q4 scoring modifier set

| Modifier | Condition | Points |
|---|---|---|
| Covenant hit | Path A chosen AND covenant hit | **+5** |
| Covenant missed | Path A chosen AND covenant missed | **−8** |
| Correct rejection | Path B rejected with correct reasoning, by a company whose true continuation value exceeds the offer | **+4** |
| Correct acceptance | Path B accepted by a company whose momentum was weak/flat, where the offer was actually fair or generous | **+4** |
| Value left on table | Path B accepted by a company with strong momentum, leaving a large true-value gap unexamined | **−3** |
| Deliberate independence | Path C chosen with explicit, stated reasoning for rejecting A and B | **+2** |

These apply **in addition to** the standard modifier set in `10-scoring-methodology.md` §
*Standard modifier triggers* — profitability, channel match, capacity waste, supply waste,
compounding asset cuts, ceiling under-shoot, buffer breach, and unjustified debt all still apply
in Q4.

> Note that "debt taken without justification (−2)" from the standard set can stack with Path A's
> covenant outcomes: a student who takes Path A **without** a stated growth plan tied to the
> covenant can incur both the −2 and, if they miss, the −8.

---

## 6. Brand multiplier at Q4

```
Brand Score 34.0 → lead multiplier ×1.68
```

Consistent with the proposed `Brand Multiplier = 1 + 0.02 × Brand Score` fit documented in
`13-quarter-2-reference.md` § 2.1 (`1 + 0.02 × 34.0 = 1.68` ✓).

---

## 7. What Q4 is actually testing

Q1 tested whether departments could be coordinated. Q2 tested whether compounding was understood
and whether scale was recognised as still-profitable. Q3 tested whether prior investment could
absorb a shock, and whether the right problem could be diagnosed under pressure.

Q4 tests something none of those did: **whether the student understands what the company they
built is actually worth**, and can act on that understanding when offered money, leverage, or the
option to walk away. The Momentum Score exists specifically so that this final question is asked
against the real company the student built — not a hypothetical one.

---

## Implementation checklist for Q4

- [ ] Define Momentum Score weights and normalisation for all 7 inputs *(blocked — not specified)*
- [ ] Define the three tier cut-off thresholds *(blocked — not specified)*
- [ ] Define each tier's term-sheet menu contents *(blocked — not specified)*
- [ ] Define the covenant threshold formula for Path A *(blocked — not specified)*
- [ ] Define "true continuation value" calculation for Path B scoring *(blocked — not specified; presumably derived from the blended valuation model in `12-quarter-1-reference.md` § 11)*
- [ ] Implement the Exit & Growth Judgment trait and its 3 sub-criteria *(sub-criteria not specified)*
- [ ] Implement the 6 Q4 modifiers *(fully specified ✓)*
- [ ] Implement Brand multiplier ×1.68 at Brand Score 34.0 *(consistent with proposed formula ✓)*
