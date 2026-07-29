# Crisis System — Complete Reference

> Source: `CRISIS_SYSTEM_REFERENCE.pdf`
> *Why it was added, how it was built, and every calculation in full*

## 1. Why crisis events exist

**The gap they fill:** every quarter through Q2 tested the same underlying skill — allocate a
known budget against known, stable formulas to grow the company. That's only half of running a
company. Real businesses also face shocks nobody chose and nobody could fully plan for. How a
company responds to those moments is a genuinely different skill from how it grows in calm
conditions. Q1 and Q2 had no mechanism to test that at all.

**Why Q3 specifically:** by Q3 a company has two quarters of real, established numbers — a Brand
Score, a Supplier Reliability, an Innovation Score, an actual customer base. A crisis introduced
in Q1 would test a company that hasn't built anything yet. Introducing it in Q3 means the crisis
tests whether **prior quarters' decisions were sound**, not just this quarter's reaction.

> **Central design idea: a crisis should reward or punish decisions made one or two quarters ago,
> not just decisions made in response to the crisis itself.**

**Why 4 events instead of 1:** a single scripted crisis, faced identically by every team,
converges toward one "correct" answer that spreads through a classroom immediately. Four distinct
events, randomly distributed, mean different teams are actually solving different problems.

## 2. Architecture

### Two event categories

| Category | Events | Nature |
|---|---|---|
| **Competitive** | Price Warrior, Marketing Blitz, Feature Leapfrog | Same underlying narrative (competitor "Vantis" launches), but each stresses a different part of the business (price sensitivity, brand/attention, product credibility) |
| **Operational/external** | Global Supply Shock | Fundamentally different — nothing about it can be marketed or priced around; it must be operationally absorbed |

### The consistent 4-component pattern (every event)

1. A **narrative trigger** (what students are told)
2. One or more **automatic formula penalties** (what happens if nothing is done)
3. A one-time **Strategic Choice** (a small menu of qualitatively different postures, exactly one of which can be picked)
4. A **new budget line** that can partially or fully claw back the automatic penalties, scaled by how much is spent

### Randomization layer

A **1-in-4** random assignment splits the cohort, using `Team ID modulo 4`, a die roll, or
shuffled sealed cards. Students are told the narrative and the choices, but **never** the
underlying formula constants or thresholds — they must diagnose their specific situation from
their own quarter's results.

### The Choice D layer

Each of the 4 events also received a **4th Strategic Choice** — *rent temporary
external/contract capacity* instead of committing to any of the original A/B/C postures. This is
deliberately **crisis-only**, not a permanent standing feature, because the logic of "rent, don't
build" only makes sense when the need might be temporary.

---

## 3. Scenario A — Price Warrior

**Narrative:** Vantis launches at ₹6,999 (a ₹3,000 gap below Nadi Wear), competing almost
entirely on price.

### Automatic penalties (zero response)

| Penalty | Formula |
|---|---|
| Demand Dampening | `Raw Leads × 0.75` (flat 25% cut, applied **before** Brand/HR multipliers) |
| Conversion Penalty | `Final Conversion Rate − 8` percentage points |
| Brand Erosion | `Brand Score − 3` (one-time), **only if ₹0 spent** on Competitive Response |

**Worked example** (Brand Score 31.2 entering Q3; Q3 marketing would normally produce 5,000 raw leads):

```
Dampened Leads = 5,000 × 0.75 = 3,750   → 1,250 leads lost purely to the event
```

### Choice A — Cut Price to Match (₹9,999 → ₹7,999)

- Conversion Penalty removed entirely (0 instead of −8)
- Gross Margin falls from 67.5% to ≈55% for the whole quarter
- Margin per unit falls from ₹6,749 to roughly ₹4,900 (same COGS ₹3,250)

### Response budget lines and their recovery formulas

| Line | Formula |
|---|---|
| Price-Match Fund | `Dampening Recovery = MIN(1.0, 0.75 + 0.15 × x^0.5)` |
| Comparison Ads | `Conversion Recovery = MIN(8, 2 × x^0.5)` points |
| Retention Offers | `Customer Loss = MAX(0%, 8% − 1.5 × x^0.5)` |

*(x = spend in ₹ lakhs on that line)*

### Choice D — Contract Sales/Promo Surge

```
Dampening Recovery = 0.75 + 0.20 × x^0.5    (stronger than the standard Price-Match Fund)
```

### Full worked recovery — ₹5,00,000 across Competitive Response (₹3L Price-Match, ₹1L Comparison Ads, ₹1L Retention)

```
Price-Match Fund (x=3.0):
  Dampening Recovery = MIN(1.0, 0.75 + 0.15 × 3.0^0.5) = MIN(1.0, 1.01) = 1.00
  → Recovered Leads = 5,000 × 1.00 = 5,000
  → FULL demand recovery; the event's lead-volume damage is entirely clawed back

Comparison Ads (x=1.0):
  Conversion Recovery = MIN(8, 2 × 1.0^0.5) = 2.0 points
  → Net Conversion Penalty remaining = 8 − 2 = 6 points (still a real, unrecovered hit)

Retention Offers (x=1.0):
  Customer Loss = MAX(0%, 8% − 1.5 × 1.0^0.5) = 6.5%
  → 6.5% of the existing 6,433-customer base (≈418 customers) still churns to Vantis
```

**Why full lead recovery was achievable but conversion wasn't:** the Price-Match Fund's formula
recovers faster (0.15 per √lakh) than Comparison Ads' formula (2 points per √lakh against an
8-point penalty). This is deliberate — getting people back to your storefront is mechanically
easier than getting them to choose you once they've seen a cheaper alternative, which is a
realistic asymmetry in real pricing wars.

---

## 4. Scenario B — Marketing Blitz

**Narrative:** Vantis launches at a comparable ₹9,499, backed by a massive awareness campaign —
the threat is entirely about **attention**, not price or product.

### Automatic penalties

| Penalty | Formula |
|---|---|
| Demand Dampening | `Raw Leads × 0.60` (40% cut — **steepest of any variant**) |
| Conversion Penalty | `−3` percentage points (mild) |
| Brand Erosion | `Brand Score − 8` (one-time), if ₹0 spent — **steepest of any variant** |

**Worked example** (same 5,000-lead baseline):

```
Dampened Leads = 5,000 × 0.60 = 3,000  → 2,000 leads lost
                                        (750 more than Scenario A for the identical baseline)
```

### Why Choice A (Cut Price) does almost nothing here

The Conversion Penalty is only −3 to begin with. Even fully removing it recovers far less than
recovering the 2,000 lost leads would. Cutting price sacrifices ~₹1,850/unit of margin to fix a
problem that was never the dominant one in this variant.

### Choice D — Contract Marketing Agency Surge

```
Dampening Recovery = 0.60 + 0.25 × x^0.5     (recovers FASTER per rupee than in-house scaling)
BUT: Brand Score contribution from this spend is capped at HALF the normal in-house rate
```

**Worked example — ₹4,00,000 on Contract Agency Surge:**

```
Dampening Recovery = MIN(1.0, 0.60 + 0.25 × 4.0^0.5) = MIN(1.0, 1.10) = 1.00
  → Full demand recovery — and here it's the CORRECT primary lever, since demand
    dampening (not conversion) was this variant's dominant penalty

Brand Score recovery is capped at half of what equivalent in-house Social & Influencer
spend would have built — the −8 Brand erosion risk is avoided (since spend > ₹0), but
this variant's long-term Brand cost isn't fully offset by a fast agency surge alone
```

---

## 5. Scenario C — Feature Leapfrog

**Narrative:** Vantis launches at ₹10,499 (pricier than Nadi Wear) but with genuinely superior
specs — the threat is entirely about **product credibility**.

### Automatic penalties

| Penalty | Formula |
|---|---|
| Demand Dampening | `Raw Leads × 0.80` (**mildest** of the 3 competitor variants) |
| Conversion Penalty | `−6` points, **UNLESS** `Innovation Score ≥ 20` (then only `−2`) |
| Conversion Ceiling Penalty | An **ADDITIONAL** `−2` points off R&D's Ceiling, **UNLESS** `Innovation Score ≥ 20` |

**Worked example** (actual carried-in Innovation Score of 17.5 from the Q2 Growth version):

```
Current Innovation Score = 17.5 — BELOW the 20 threshold
→ Without any response: Conversion Penalty = −6, AND Ceiling Penalty = −2 (a double hit)
```

### Choice D — Contract R&D Sprint (highest-leverage Choice D of all 4 scenarios)

```
Innovation Score += 3 × x^0.5    (this quarter only; weaker per rupee than in-house's 5 × x^0.5)
```

**Worked example — ₹3,00,000 spent:**

```
Innovation Boost    = 3 × 3.0^0.5 = 3 × 1.732 = 5.20
New Innovation Score = 17.5 + 5.20 = 22.70
Crosses the 20 threshold? YES (22.70 ≥ 20)
  → Conversion Penalty reduces from −6 to −2
  → Ceiling Penalty is WAIVED entirely (0 instead of −2)
```

**Why this is the clearest "second chance" mechanic in the whole crisis system:** a team that
spent too little on R&D across Q1 and Q2 (ending at 17.5, just short of the threshold) would, in
every other scenario, simply have to live with the consequences of that prior neglect. Here a
single well-timed ₹3,00,000 contract spend genuinely rescues the situation — but only because the
shortfall was small (2.5 points). A team that neglected R&D far more severely would need
proportionally more contract spend, following the same square-root formula, to close a larger gap.

---

## 6. Scenario D — Global Supply Shock

**Narrative:** a global disruption cuts component availability and freight capacity — an
operational, not competitive, threat.

### The core formula — the most important single formula in the entire crisis system

```
Capacity Penalty Multiplier = MIN(1.0, MAX(0.10,
    0.50                                         [base cut]
  + 0.005 × (Supplier Reliability − 50)          [existing investment offset]
  + Strategic Choice offset                      [0, +0.25, or +0.50]
  + 0.10 × (Emergency Fund spend in lakhs)^0.5   [this quarter's reactive spend]
))

Effective New Production Capacity = [Normal formula result] × Capacity Penalty Multiplier
```

### Worked example — actual carried-in Supplier Reliability 79.8, Choice B + ₹2,00,000 Emergency Fund

```
Base                        = 0.50
Supplier Reliability offset = 0.005 × (79.8 − 50) = 0.005 × 29.8 = 0.149
Choice B offset             = 0.25
Emergency Fund offset       = 0.10 × 2.0^0.5 = 0.10 × 1.414 = 0.141
Final Multiplier            = MIN(1.0, MAX(0.10, 0.50 + 0.149 + 0.25 + 0.141))
                            = MIN(1.0, 1.040) = 1.00
→ FULL capacity retained
```

### The comparison that proves the design thesis

| Team's Supplier Reliability | Offset | Final Multiplier | Outcome |
|---|---|---|---|
| **79.8** (invested since Q1) | 0.149 | **1.00** | Full capacity — barely feels the crisis |
| **70** (never invested; baseline) | 0.100 | **0.991** | Still very good; gap entirely attributable to the ~10-point Reliability difference |
| **50** (badly neglected; floor) | 0.000 | **0.891** | Nearly 11% of production capacity lost — entirely avoidable, with the same Choice B and Fund spend |

### Choice D — Contract Manufacturing (Diversified Third-Party) — the strongest Choice D of all 4

```
Contract-specific penalty  = 0.25   (instead of 0.50 — only HALF the base cut applies)
Contract Capacity Formula  = 320 × x^0.7
Effective Contract Capacity = Contract Capacity × (1 − 0.25) = Contract Capacity × 0.75
Manufacturing Cost/Unit for these units = base formula + ₹350 premium
```

**Why this Choice D is mechanically different from every other:** in Scenarios A, B, and C,
Choice D trades effectiveness for flexibility — it's genuinely worse per rupee, just faster and
reversible. Here, because the crisis is specifically domestic/regional, a genuinely diversified
contract manufacturer in a different location is **structurally less exposed to the same shock**.
This is the one Choice D that isn't a compromise — it's close to a strictly better answer once a
student understands *why* this particular crisis is geographic in nature.

---

## 7. Crisis scoring modifiers

| Modifier | Trigger condition | Points |
|---|---|---|
| Crisis fully neutralized | The event's core mechanism (dampening, penalty, or capacity cut) reduced to zero net effect | **+3** |
| Crisis-proofed by prior investment | Final Capacity Multiplier ≥ 0.90 without needing the expensive Choice A response | **+3** |
| Structural improvement made | Choice B (Supply Shock) selected, converting a crisis into a permanent Supplier Reliability gain | **+2** |
| Crisis ignored | ₹0 spent on the relevant response line when a severe event occurs | **−4** |

---

## 8. The finding that ties all 4 scenarios together

> The size of the crisis a team actually experiences is **never just the crisis itself** — it's
> the crisis, filtered through whatever that team built in the two quarters before it arrived.

- A strong **Brand Score** softens Marketing Blitz.
- A strong **Innovation Score** neutralizes Feature Leapfrog entirely.
- A strong **Supplier Reliability** can make a "severe" Global Supply Shock barely register.

The crisis system doesn't really test crisis management in isolation — it tests whether two
quarters of "boring," unglamorous investment (in brand, in R&D, in supplier relationships) was
real or superficial, and reveals the answer at the exact moment it matters most.

---

## Implementation summary — all crisis constants in one table

| Scenario | Dampening ×  | Conversion Penalty | Brand Erosion (if ₹0) | Choice D recovery |
|---|---|---|---|---|
| A: Price Warrior | 0.75 | −8 pts | −3 | `0.75 + 0.20 × x^0.5` |
| B: Marketing Blitz | 0.60 | −3 pts | −8 | `0.60 + 0.25 × x^0.5` |
| C: Feature Leapfrog | 0.80 | −6 pts (−2 if Innovation ≥ 20) | — | `Innovation += 3 × x^0.5` |
| D: Supply Shock | see Capacity Multiplier | — | — | `320 × x^0.7 × 0.75`, +₹350/unit |

| Standard response line | Formula |
|---|---|
| Price-Match Fund | `MIN(1.0, 0.75 + 0.15 × x^0.5)` |
| Comparison Ads | `MIN(8, 2 × x^0.5)` conversion points |
| Retention Offers | `MAX(0%, 8% − 1.5 × x^0.5)` customer loss |
| Emergency Supply Chain Fund | `+0.10 × x^0.5` to Capacity Multiplier |

| Strategic Choice offsets (Scenario D) | Value |
|---|---|
| Choice A / C | 0 |
| Choice B (Diversify Suppliers) | +0.25 |
| (highest tier) | +0.50 |

> ⚠️ **Gap:** the source specifies the Strategic Choice offset set as `[0, +0.25, or +0.50]` but
> only explicitly names Choice B as +0.25. Which choice carries +0.50 is not stated.
> Tracked in `10-implementation-gaps.md`.
