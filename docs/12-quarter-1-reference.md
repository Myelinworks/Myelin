# Quarter 1 Reference — Master Formula Document

> Source: `quarter_1.pdf` (Nadi Wear Pvt. Ltd. — Q1 Complete Report)

**This is the single most important file in `docs/`.** Every formula below is fully specified
(constant, exponent, units, floor/ceiling) and validated against a worked numeric example.
These are the formulas the decision engine must implement.

> **Units convention throughout: `x` = spend in ₹ lakhs.** Where a formula says `x^0.68`, a
> ₹4,00,000 spend means `x = 4.00`.

---

## 1. Starting position

| Item | Value | Reasoning |
|---|---|---|
| Seed Funding Raised | ₹4,00,00,000 | Realistic early-stage Indian D2C hardware round — creates genuine scarcity. (Reduced from an original ₹18 Cr, which removed all financial pressure and therefore all real trade-offs.) |
| Cash at Start of Q1 | ₹1,50,00,000 | ₹2.5 Cr already burned pre-sim (3 months of tooling, first production runs, early hires). Cash covers ~6 months while the simulation runs 12 — **that gap is the entire tension of the game.** |
| Fixed Costs / Quarter | ₹23,50,000 | See breakdown below |
| Working Capital Buffer | ₹10,00,000 | Covers the supplier-payment vs. marketplace-payout timing gap. **A rule, not a resource.** |
| MRP | ₹9,999 | Raised from ₹6,999 for viable unit economics |
| COGS | ₹3,250 | Unchanged — manufacturing cost doesn't change because pricing changed |
| Gross Margin | 67.5% (₹6,749/unit) | Realistic for mid-range D2C hardware owning its own pricing |
| Base Conversion Rate | 19% | Raised from 8%; realistic for a warmed, qualified lead in Indian D2C electronics |
| Market Ceiling | 2,50,000 potential buyers/quarter | Company reaches <2% of it — **internal capacity, not market size, is the real constraint** |
| Existing customers (start) | 4,000 | |
| Finished goods inventory (start) | 600 units | From pre-simulation production |
| Waitlist | 22,000 signups | Feeds Email Marketing channel |

### Fixed cost breakdown (₹23,50,000)

| Line | Amount | Basis |
|---|---|---|
| Core team salaries (14 people) | ₹14,50,000 | 14 × ~₹1,03,571/month blended × 3 months |
| Office rent & utilities | ₹5,00,000 | Modest Bengaluru office/warehouse hybrid |
| Software & cloud subscriptions | ₹2,50,000 | Design tools, CRM, hosting — scales with team size |
| Insurance & compliance minimums | ₹1,50,000 | Legal floor for a registered Pvt. Ltd. |
| **Total** | **₹23,50,000** | |

**Why it was cut from ₹36,00,000:** the original model had a 24-person centralised team, requiring
~534 units/quarter just to break even — a bar even optimal allocation could never clear. Hiring was
**decentralised** (every department funds its own headcount from its own spend), leaving fixed cost
to cover only a lean core team of 14.

```
Breakeven on fixed costs = ₹23,50,000 ÷ ₹6,749 per unit ≈ 348 units/quarter
                           (vs. 534 units under the old model)
```

---

## 2. Marketing formulas — **all 8 lines**

Every channel follows `Leads = Constant × Spend^Exponent`, but the constant and exponent were each
chosen to reflect a real difference in channel behaviour.

**Why every exponent is under 1.0:** in real digital marketing the first rupee reaches the
cheapest, most responsive audience segment; each additional rupee reaches a slightly less
responsive one. This is literally how ad auctions work. An exponent under 1.0 encodes "each
additional rupee buys slightly fewer leads than the rupee before it."

*(Exponents were raised from harsher original values — e.g. Google Ads 0.55 → 0.68 — because the
original values made even large budgets barely worth spending. Raising them doesn't remove
diminishing returns, it makes their severity more forgiving.)*

### 2.1 Google Ads

```
Leads = 375 × x^0.68
```

| Parameter | Value | Reasoning |
|---|---|---|
| Constant | 375 | Sets the efficiency ceiling at low spend — ₹1 lakh returns ~375 leads, plausible CPL for Indian search advertising on a mid-range consumer product |
| Exponent | 0.68 (**highest of any paid channel**) | Search intent is renewed constantly (new people search "smartwatch" daily) rather than being a fixed pool — least "audience exhaustion" at this scale |

**Q1 worked calculation:**
```
Spend = ₹4,00,000 → x = 4.00
4.00^0.68:  ln(4.00) = 1.3863;  × 0.68 = 0.9427;  e^0.9427 = 2.567
Leads = 375 × 2.567 = 962.6 → 963 leads
```

### 2.2 Meta Ads

```
Leads         = 200 × x^0.65
Impressions   = 40,000 × x
Brand Score  += 1.2 per lakh
```

| Parameter | Reasoning |
|---|---|
| Leads constant 200 (< Google's 375) | Interrupting someone mid-scroll converts to a lead less reliably than catching someone who already typed "smartwatch" into a search bar |
| Impressions as a second output | Meta's real value isn't fully captured by leads — much of its worth is pure brand exposure. Dashboard-visible so this "invisible" value isn't lost |
| Brand rate between Social's and Events' | Paid, scaled awareness — more brand-building than pure-performance Google, less than organic/influencer content which people trust more |

**Q1 worked calculation:**
```
Spend = ₹1,92,000 → x = 1.92
1.92^0.65:  ln(1.92) = 0.6523;  × 0.65 = 0.4240;  e^0.4240 = 1.528
Leads = 200 × 1.528 = 305.6 → 306 leads
Brand Score contribution = 1.2 × 1.92 = 2.30
```

### 2.3 Social & Influencer

```
Leads        = 225 × x^0.72
Brand Score += 2.5 per lakh
```

| Parameter | Reasoning |
|---|---|
| Exponent 0.72 (**highest of any channel**) | Unlike a paid-ads auction, influencer costs don't rise as sharply with scale — a bigger budget secures a bigger-audience creator rather than bidding up against competitors for the same audience |
| Brand rate +2.5/lakh (**highest of any channel**) | Genuine third-party endorsement carries far more trust-building weight per rupee than a company's own paid advertisement |

**Q1 worked calculation:**
```
Spend = ₹2,08,000 → x = 2.08
2.08^0.72:  ln(2.08) = 0.7324;  × 0.72 = 0.5273;  e^0.5273 = 1.694
Leads = 225 × 1.694 = 381.2 → 381 leads
Brand Score contribution = 2.5 × 2.08 = 5.20
```

### 2.4 Content / SEO

```
Leads        = 75 × x^0.62         (immediate — deliberately weak)
SEO Asset   += 3.5 per lakh        (compounding)
Free leads next quarter = SEO Asset × 25
```

**Why immediate leads are deliberately weak (constant 75, lowest of any paid channel):** SEO is a
real-world slow-build channel — content published today doesn't rank overnight. It's meant to look
like a bad short-term bet in the raw numbers, which is realistic, while its true value shows up
entirely through the SEO Asset mechanic.

**Why SEO Asset is a separate score:** if Content/SEO's entire value were captured in the same
quarter it was spent, there'd be no way to distinguish it mechanically from Google Ads. In reality
the whole point of SEO is that it pays off later, for free, without additional spend.

**Q1 worked calculation:**
```
Spend = ₹1,28,000 → x = 1.28
1.28^0.62:  ln(1.28) = 0.2469;  × 0.62 = 0.1531;  e^0.1531 = 1.1655
Leads = 75 × 1.1655 = 87.4 → 87 leads
SEO Asset built = 3.5 × 1.28 = 4.48 ≈ 4.5  → worth 4.5 × 25 ≈ 113 free leads in Q2
```

### 2.5 Events / PR

```
Leads        = 90 × x^0.62
Brand Score += 1.5 per lakh
```

Both direct-lead output and Brand contribution sit in the middle of the pack: Events/PR is a real
but secondary lever compared to Social's stronger brand-building role — it matters, but shouldn't
out-perform the channel whose entire purpose is brand-building.

**Q1 worked calculation:**
```
Spend = ₹80,000 → x = 0.80
0.80^0.62:  ln(0.80) = −0.2231;  × 0.62 = −0.1383;  e^−0.1383 = 0.8708
Leads = 90 × 0.8708 = 78.4 → 78 leads
Brand Score contribution = 1.5 × 0.80 = 1.20
```

### 2.6 Email Marketing

```
Leads                 = 80 × x^0.55
Repeat Purchase Rate += 3 × x^0.5   (percentage points)
```

**Why it was added:** none of the original 5 channels touched the company's own 22,000-signup
waitlist or past leads — a real gap, since re-engaging people who already showed interest is
typically the cheapest lead generation available.

**Why it also feeds Repeat Purchase Rate, uniquely among Marketing channels:** email is the one
channel that speaks directly to people who already know the brand — inherently a retention tool as
much as an acquisition one. **Email Marketing (a Marketing spend) and Sales' Onboarding (a Sales
spend) both build the same Repeat Purchase Rate number** — two different departments must both
invest for this metric to reach full potential.

**Q1 worked calculation:**
```
Spend = ₹1,60,000 → x = 1.60
1.60^0.55:  ln(1.60) = 0.4700;  × 0.55 = 0.2585;  e^0.2585 = 1.295
Leads = 80 × 1.295 = 103.6 → 104 leads
Repeat Rate contribution = 3 × 1.60^0.5 = 3 × 1.265 = 3.795 ≈ +3.8 percentage points
```

### 2.7 Referral Program — **the only channel with no exponent**

```
Lead Cap      = 0.20 × existing customers
Cost per lead = ₹300 flat
Cost to cap   = Lead Cap × ₹300
```

**Why this shape is different:** every other channel scales against an effectively unlimited
outside population. Referral scales against something small and finite — the company's own
existing customers. That's a **hard cap, not a diminishing curve.**

**Why 0.20 (raised from 0.15):** with modern referral tooling, closer to 1-in-5 customers referring
someone is achievable for a product people are genuinely excited about.

**Why the cost is flat:** referring a friend costs roughly the same incentive regardless of how
many referrals have already happened — there's no auction-style competition driving cost up.

**Why it's the best long-term channel:** its cost-per-lead never rises no matter how large the
customer base gets. As the customer base compounds quarter over quarter, Referral becomes
proportionally more valuable.

**Q1 worked calculation:**
```
Existing customers (start of Q1) = 4,000
Cap  = 0.20 × 4,000 = 800 leads maximum, no matter how much is spent
Cost to reach the cap = 800 × ₹300 = ₹2,40,000
Budget allocated = ₹2,40,000 → exact match, zero rupees wasted, full 800 leads captured
```

### 2.8 Pre-Launch Buzz — the 2-quarter mechanic

```
Q1 (invest):  Buzz Score = 4 × x^0.5,  ZERO leads this quarter
Q2 (release): Free leads = Buzz Score × 15
Q3 (pent-up): Free leads = Buzz Score × 25
              one-time Conversion Rate bonus = Buzz Score × 0.3 points
```

**Why it exists:** every other Marketing channel pays off the same quarter it's spent (or, for SEO,
the very next). Nothing rewarded thinking **two** quarters ahead. Pre-Launch Buzz was built
specifically to test whether a student would sacrifice a full quarter of zero visible payoff for a
bigger return later.

**Why the payoff splits across two future quarters:** mirrors a real product launch — an initial
wave of interest at release (Q2), then a second, larger wave once word-of-mouth and reviews catch
up (Q3).

**Q1 worked calculation:**
```
Spend = ₹1,92,000 → x = 1.92
Buzz Score = 4 × 1.92^0.5 = 4 × 1.386 = 5.54 ≈ 5.5
Q2 free leads = 5.5 × 15 ≈ 83
Q3 free leads = 5.5 × 25 ≈ 138, plus a one-time +1.65 conversion-point bonus in Q3 only
```

**Zero leads in Q1 is not a bug — it's the mechanic working as intended.**

### 2.9 Q1 Marketing summary

| Channel | Spend | Formula | Leads |
|---|---|---|---|
| Google Ads | ₹4,00,000 | `375 × x^0.68` | 963 |
| Meta Ads | ₹1,92,000 | `200 × x^0.65` | 306 |
| Social & Influencer | ₹2,08,000 | `225 × x^0.72` | 381 |
| Content/SEO | ₹1,28,000 | `75 × x^0.62` | 87 |
| Events/PR | ₹80,000 | `90 × x^0.62` | 78 |
| Email Marketing | ₹1,60,000 | `80 × x^0.55` | 104 |
| Referral | ₹2,40,000 | cap-matched | 800 |
| Pre-Launch Buzz | ₹1,92,000 | `Buzz = 4 × x^0.5` | 0 (by design) |
| **Total** | **₹16,00,000** | | **2,719 raw leads** |

| Side effect | Calculation | Result |
|---|---|---|
| Brand Score built | `1.2×1.92 + 2.5×2.08 + 1.5×0.80` | **8.7** (applies as a lead multiplier from Q2, not Q1) |
| SEO Asset built | `3.5 × 1.28` | **4.5** → 113 free Q2 leads |
| Buzz Score built | `4 × 1.92^0.5` | **5.5** → 83 free Q2 leads, 138 + conv. bonus in Q3 |
| Repeat Rate (Email) | `3 × 1.60^0.5` | **+3.8 pts** |

---

## 3. Sales formulas

Sales exists to answer a question Marketing's formulas deliberately don't: **a lead is interest,
not a sale.** Something has to convert that interest, and something has to have the bandwidth to
handle the volume. Those are two different jobs.

### 3.1 Sales Reps & Commissions — the only line that buys hard capacity

```
Capacity         = 500 × x          (leads/quarter — LINEAR, no exponent)
Conversion Bonus = 2 × x^0.5        (percentage points)
```

**Why capacity is linear but the conversion bonus diminishes:** hiring reps to handle volume scales
roughly linearly — twice the budget buys close to twice the bandwidth. But making each individual
rep *better* at closing (training, incentives, experience) has the same diminishing-returns logic
as any skill investment.

**Why this is the ONLY line that builds hard Sales Capacity:** deliberate — it means the Sales
budget's split between "more bandwidth" (Reps) and "better tools" (CRM) is a genuine trade-off,
not something optimised away by spreading money everywhere.

**Q1 worked calculation:**
```
Spend = ₹5,45,000 → x = 5.45
Capacity         = 500 × 5.45 = 2,725 leads/quarter
Conversion Bonus = 2 × 5.45^0.5 = 2 × 2.334 = 4.669 ≈ +4.7 percentage points
```

### 3.2 CRM & Sales Tools

```
Conversion Bonus = 1.5 × x^0.4
```

**Why the exponent (0.4) is lower than Reps' (0.5):** software tools hit their useful ceiling
faster than human skill development. There's only so much a CRM can improve close rates before
you've captured essentially all the efficiency it can offer.

**Q1 worked calculation:**
```
Spend = ₹1,30,000 → x = 1.30
1.30^0.4:  ln(1.30) = 0.2624;  × 0.4 = 0.1050;  e^0.1050 = 1.1106
Bonus = 1.5 × 1.1106 = 1.666 ≈ +1.7 percentage points
```

### 3.3 Customer Onboarding / Retention

```
Satisfaction Score   += 3 × x^0.5
Repeat Purchase Rate += 3 × x^0.4
```

**Why the payoff is entirely next quarter:** onboarding investment doesn't make today's sale more
likely — the customer already bought by the time onboarding happens. What it affects is whether
that customer is satisfied enough to buy again or refer a friend.

**Cross-functional links:** Satisfaction is shared with Operations' Logistics line; Repeat Rate is
shared with Marketing's Email line. **No single department can max out either score alone.**

**Q1 worked calculation:**
```
Spend = ₹1,25,000 → x = 1.25
Satisfaction contribution = 3 × 1.25^0.5 = 3 × 1.118 = 3.354 ≈ +3.4 points
Repeat Rate contribution  = 3 × 1.25^0.4
  1.25^0.4:  ln(1.25) = 0.2231;  × 0.4 = 0.0893;  e^0.0893 = 1.0934
  = 3 × 1.0934 = 3.28 ≈ +3.3 percentage points
```

### 3.4 Why Capacity (2,725) and Raw Leads (2,719) landed so close

**Not a coincidence.** The Reps spend (₹5,45,000) was deliberately sized against Marketing's
expected lead output *before either number was finalised*, to avoid the capacity-mismatch problem
an earlier un-coordinated allocation produced (where Marketing generated far more leads than Sales
could handle, wasting a large share of paid-for demand).

---

## 4. R&D formulas

### Variable curation reasoning

The original list proposed 11 items. **4 were cut:**

| Cut variable | Why |
|---|---|
| Products Live / Products Under Development | A multi-SKU portfolio tracker belongs to a company with several products. Nadi Wear has exactly one — tracking a "portfolio of one" adds bookkeeping without decision value. Folded into Feature Completeness |
| Technology Readiness | Conceptually near-identical to Feature Completeness. Two meters tracking the same idea creates one decision measured twice |
| Product Reliability | Mathematically the inverse of Defect Rate. Computing the same relationship from two directions adds no insight |
| Product Lifecycle (Growth/Maturity/Decline) | Real, but plays out over multiple years, not within one product's first 12 months — a variable that literally cannot move within the simulation's timeframe |

**Product Rating** became a *derived* metric: a star rating is something customers give based on
how good the product actually is (Quality Score) and how well the company treats them (Defect Rate,
Satisfaction) — it isn't something a company can buy directly.

**Warranty Period** became a *strategic decision* rather than a spend line: a warranty doesn't cost
anything to offer; the cost materialises later, in proportion to how many units fail. Modelling it
as a decision with a contingent cost reflects how warranty liabilities actually work.

### 4.1 Quality / QA Engineering

```
Quality Score += 6 × x^0.5                        (CUMULATIVE — never resets)
Defect Rate    = max(2%, 8% − 1.2 × x^0.5)        (2% floor)
```

**Why Quality Score is cumulative but Defect Rate has a floor:** Quality Score represents
accumulated engineering knowledge and process maturity — once learned, it doesn't disappear.
Defect Rate floors at 2% because even world-class manufacturing has an irreducible failure rate;
modelling a path to literally zero defects would be unrealistic for hardware.

**Q1 worked calculation:**
```
Spend = ₹2,75,000 → x = 2.75
Quality Score = 6 × 2.75^0.5 = 6 × 1.658 = 9.95
Defect Rate   = max(2%, 8% − 1.2 × 1.658) = max(2%, 8% − 1.99) = 6.01% ≈ 6.0%
```

### 4.2 Innovation / Feature Development

```
Feature Completeness += 8 × x^0.5     (resets at 100)
Innovation Score     += 5 × x^0.5     (NEVER decays or resets)
```

**Why tracked separately from Quality Score:** Quality Score answers "how well-built is the current
product" — a fixable, improvable-but-plateauing number. Innovation Score answers "how much genuine
forward-looking capability has this company built" — designed to never decay, representing R&D
knowledge and IP that compounds permanently.

**Why Feature Completeness resets at 100:** it represents work toward one specific feature or
product variant at a time. Once that ships (the "launch event" at 100%), the next round of feature
work starts from zero, exactly like a real product roadmap.

**Q1 worked calculation:**
```
Spend = ₹2,25,000 → x = 2.25
Feature Completeness += 8 × 2.25^0.5 = 8 × 1.5 = 12.0 (toward 100)
Innovation Score     += 5 × 2.25^0.5 = 5 × 1.5 = 7.5
```

### 4.3 The Conversion Rate Ceiling — **the most important formula in the redesign**

```
Conversion Ceiling = 15% + (Quality Score + 0.5 × Innovation Score) × 0.3%
```

**Why the ceiling starts at 15% even with zero R&D spend:** a product needs baseline functional
quality just to be sellable. 15% represents the company's already-built pre-simulation product
development (the ₹50,00,000 spent on tooling/certification in the 3 months before Q1).

**Why Innovation Score counts at half weight:** Quality Score is a direct measure of the current
product's fitness; Innovation Score is a broader, longer-term capability that only partially
translates into this quarter's conversion. Full weighting would double-count the same R&D effort.

**Why this is a CEILING, not a bonus:** this is the single change that fixed the core problem that
Marketing alone could win the whole game. If Quality Score has no effect on how many of Sales'
leads can actually convert, R&D becomes optional. **Making it a ceiling means no amount of
Marketing or Sales spend can ever fully compensate for skipping R&D.**

**Q1 worked calculation:**
```
Ceiling = 15% + (9.95 + 0.5 × 7.5) × 0.3%
        = 15% + (9.95 + 3.75) × 0.3%
        = 15% + 13.70 × 0.3%
        = 15% + 4.11%
        = 19.11% ≈ 19.1%
```

### 4.4 Warranty (strategic decision, not a spend line)

```
Final Conversion Rate = Conversion Ceiling + Warranty Bonus     (ADDITIVE, applied AFTER the ceiling)
Warranty Cost = Units Sold × Defect Rate × ₹1,500
```

| Warranty | Conversion Bonus |
|---|---|
| 1 year | +1.5 points |
| 2 years | +3.0 points |

**Why Warranty is additive AFTER the ceiling, not subject to it:** the Conversion Rate Ceiling
represents the product's underlying build quality — a hard technical limit. Warranty is a **trust
and risk-transfer signal**, a fundamentally different kind of persuasion than "the product is
well-built." It layers on top of whatever rate the product's actual quality allows.

**Q1:** `Final Conversion Rate = 19.1% + 1.5% = 20.6%`
`Warranty Cost = 562 × 6.0% × ₹1,500 = ₹50,630`

---

## 5. Operations formulas

### Variable curation reasoning

The original list proposed 12 items. **5 were cut:**

| Cut variable | Why |
|---|---|
| Raw Material Inventory | A second inventory layer adds supply-chain realism but no new decision at this scale — its entire practical effect (parts might not arrive) is better represented as a single risk variable. Folded into Supplier Reliability |
| Assembly Time/Unit | An input to how many units get built, not a separate decision — already implicit in the Production Capacity formula |
| Production Efficiency | After folding in Assembly Time, this became a second name for the same "capacity per rupee spent" concept |
| Warehouse Capacity / Utilization | A hard storage cap is real for a much larger company, but at a few hundred to low-thousand units/quarter it would never actually bind. Replaced with **Inventory Holding Cost**, which discourages overproduction through cost rather than an inert cap |

**On-Time Delivery** and **Current Utilization** became derived metrics — both are genuinely
outcomes of other decisions (Supplier Reliability + Logistics Efficiency; Units Sold ÷ Available to
Sell). There's no real-world lever a company pulls to buy "on-time delivery" directly.

### 5.1 Manufacturing & Production — two outputs from one spend

```
Production Capacity      = 400 × x^0.7
Manufacturing Cost/Unit  = max(₹2,600, ₹3,250 − 90 × x^0.5)      (₹2,600 floor)
```

**Why one spend produces two outputs:** in a real factory, investment in production lines both lets
you build more units *and* lowers the cost of building each one (economies of scale). Splitting
these into two spend lines would imply a company could buy capacity without any effect on unit
cost, which isn't how manufacturing investment works.

**Why the ₹2,600 floor:** components and raw materials set a real physical floor on how cheap a
unit can ever be built, regardless of assembly efficiency.

**Q1 worked calculation:**
```
Spend = ₹3,30,000 → x = 3.30
3.30^0.7:  ln(3.30) = 1.1939;  × 0.7 = 0.8358;  e^0.8358 = 2.307
Production Capacity = 400 × 2.307 = 922.6 ≈ 923 new units

3.30^0.5 = 1.817;  90 × 1.817 = 163.5
Manufacturing Cost/Unit = max(2,600, 3,250 − 163.5) = ₹3,086.5 ≈ ₹3,087
```

### 5.2 Supplier & Quality Control — a risk multiplier, not an output

```
Supplier Reliability += 4 × x^0.5           (0–100 scale, baseline 70)
Effective Capacity    = Production Capacity × (Supplier Reliability / 100)
```

**Why it's a multiplier that only reduces:** unlike Manufacturing spend, which directly buys
physical capacity, supplier relationship investment doesn't build anything new — it **protects the
capacity you've already built** from parts shortages, late shipments, or component quality issues.

**Why baseline 70, not 0 or 100:** a brand-new company has some supplier relationships already
(from the pre-simulation production run) but hasn't had time to build a proven, resilient supply
chain. 70 = "decent but unproven," leaving real room to move in either direction.

**Q1 worked calculation:**
```
Spend = ₹1,50,000 → x = 1.50
Supplier Reliability = 70 + 4 × 1.50^0.5 = 70 + 4 × 1.225 = 70 + 4.90 = 74.9
```

### 5.3 Logistics & Fulfillment

```
Logistics Efficiency += 5 × x^0.5            (baseline 60)
Satisfaction Score   += 0.05 × Logistics Efficiency
```

**Why it feeds Satisfaction directly:** delivery speed and packaging quality are things a customer
experiences directly and immediately — one of the clearest real-world links between an operational
decision and how a customer feels.

**Q1 worked calculation:**
```
Spend = ₹1,20,000 → x = 1.20
Logistics Efficiency      = 60 + 5 × 1.20^0.5 = 60 + 5 × 1.095 = 65.5
Satisfaction contribution = 0.05 × 65.5 = 3.27 ≈ +3.3 points
```

### 5.4 Available to Sell — the hard supply gate

```
Available to Sell = (Production Capacity × Supplier Reliability / 100)
                  + Finished Goods Inventory carried in
```

**Why this is a strict ceiling on Units Sold with no exceptions:** the second of two
department-level hard gates introduced to fix the "Marketing wins alone" problem. No matter how
many leads exist or how favourable the conversion rate is, a company **physically cannot sell
watches it hasn't built or doesn't have in stock.** The most literal, physical constraint in the
entire model.

**Q1 worked calculation:**
```
Effective Production Capacity = 923 × (74.9/100) = 691.0 ≈ 691 units
Available to Sell             = 691 + 600 (carried from pre-simulation) = 1,291 units
```

Did NOT bind this quarter (demand landed at 562 units, well under 1,291) — but the formula, and
the 729 units of resulting carried-forward inventory, matter directly for Q2's starting position
and its Inventory Holding Cost.

**Inventory Holding Cost: ₹150 per unsold unit per quarter.**

---

## 6. HR formulas

**Nothing was cut** — the original HR list was already well-differentiated. The design work was
making sure Employee Satisfaction and Employee Engagement drove *different* mechanics rather than
both being generic "morale" numbers.

| Metric | Drives | Rationale |
|---|---|---|
| **Satisfaction** (content with pay, benefits, culture) | **Productivity Multiplier** | Happier people work more effectively, company-wide, right now |
| **Engagement** (invested in staying and growing) | **Attrition Rate** | Engaged people don't leave — matters for retaining capacity already built, not boosting it further |

**Total Employees, Leadership, and team headcounts** became derived read-outs rather than spend
decisions, since hiring was decentralised: they're informational math (`spend ÷ ₹2,00,000 per
hire`) rather than new decisions layered on decisions made elsewhere.

### 6.1 Culture & Benefits

```
Employee Satisfaction += 5 × x^0.5                          (baseline 65)
Productivity Multiplier = 1 + (Satisfaction − 50) × 0.004
```

**Why the multiplier is centered on 50:** 50 represents a neutral, "adequate but unremarkable"
baseline — the multiplier only meaningfully helps once satisfaction rises clearly above
bare-adequate, and actively hurts if it falls below.

**Q1 worked calculation:**
```
Spend = ₹1,20,000 → x = 1.20
Employee Satisfaction   = 65 + 5 × 1.20^0.5 = 65 + 5 × 1.095 = 70.5
Productivity Multiplier = 1 + (70.5 − 50) × 0.004 = 1 + 0.082 = 1.082
```

### 6.2 Training & Development

```
Employee Engagement += 6 × x^0.5                            (baseline 60)
Attrition Rate       = max(3%, 15% − 0.12 × Engagement)     (3% floor)
```

**Why the 3% floor:** some turnover is normal and unavoidable in any real company (people move
cities, change careers, retire).

**Why Attrition "had no bite" in Q1:** the mechanic erodes capacity **already built in a previous
quarter**. Since Q1 is the first quarter, there's no prior capacity to erode. This becomes a real,
active risk starting in Q2.

**Q1 worked calculation:**
```
Spend = ₹90,000 → x = 0.90
Employee Engagement = 60 + 6 × 0.90^0.5 = 60 + 6 × 0.949 = 65.7
Attrition Rate      = max(3%, 15% − 0.12 × 65.7) = max(3%, 15% − 7.88) = 7.12% ≈ 7.1%
```

**Application in later quarters:** `Effective Capacity = Capacity × (1 − Attrition Rate)`.
In Q2, `500 × x × 0.929`; in Q3, `× 0.939`.

### 6.3 Customer Experience Team

```
Satisfaction Score   += 4 × x^0.5
Repeat Purchase Rate += 2 × x^0.4
```

**The third leg of the Repeat Rate stool**, alongside Marketing's Email line and Sales'
Onboarding line — making Repeat Rate the single most cross-functional number in the entire model.

**Q1 worked calculation:**
```
Spend = ₹90,000 → x = 0.90
Satisfaction contribution = 4 × 0.90^0.5 = 4 × 0.949 = 3.79 ≈ +3.8 points
Repeat Rate contribution  = 2 × 0.90^0.4
  0.90^0.4:  ln(0.90) = −0.1054;  × 0.4 = −0.0421;  e^−0.0421 = 0.9587
  = 2 × 0.9587 = 1.92 ≈ +1.9 percentage points
```

### 6.4 Total Employees (derived)

```
Cost per hire = ₹2,00,000
Total Employees = 14 (core fixed)
                + Marketing spend ÷ ₹2,00,000
                + Sales Reps spend ÷ ₹2,00,000
                + R&D spend ÷ ₹2,00,000
                + Operations spend ÷ ₹2,00,000
                + Customer Experience spend ÷ ₹2,00,000
```

**Q1:**
```
14 + (16,00,000÷2,00,000 = 8.0) + (5,45,000÷2,00,000 = 2.7) + (5,00,000÷2,00,000 = 2.5)
   + (6,00,000÷2,00,000 = 3.0) + (90,000÷2,00,000 = 0.45)
= 30.65 ≈ 31 employees   (up from a pre-simulation baseline of 24)
```

---

## 7. Finance/Admin formulas

**Why Finance/Admin is fundamentally different:** every other department's spend affects this
quarter's Units Sold. Finance/Admin's spend affects almost nothing about this quarter's sales —
its entire value is in **reducing future risk and future cost.** This is intentional: it
represents the genuinely unglamorous work (compliance filings, financial forecasting, audit
preparation) that doesn't show up as growth but that a company skips at its own peril.

### 7.1 Compliance & Legal

```
Compliance Score += 5 × x^0.5      (baseline 50)
```

**Q1:** `50 + 5 × 2.80^0.5 = 50 + 5 × 1.673 = 58.4` (spend ₹2,80,000)

### 7.2 Financial Planning & Tools

```
Forecast Accuracy    += 6 × x^0.5                         (baseline 55)
Cash Efficiency Bonus = (Forecast Accuracy − 50) × 0.1%   → discount to NEXT quarter's Fixed Costs
```

**Why the payoff is a lower future Fixed Cost rather than more revenue:** better forecasting and
financial tooling don't sell more watches — they help a company spend its existing money more
efficiently, catching waste and improving cash-timing decisions.

**Q1:**
```
Spend = ₹2,10,000 → x = 2.10
Forecast Accuracy     = 55 + 6 × 2.10^0.5 = 55 + 6 × 1.449 = 63.7
Cash Efficiency Bonus = (63.7 − 50) × 0.1% = 1.37%
Q2 Fixed Costs = ₹23,50,000 × (1 − 0.0137) = ₹23,50,000 − ₹32,195 = ₹23,17,805
```

### 7.3 Audit & Reporting Prep

```
Audit Readiness += 5 × x^0.5       (baseline 50)
```

**Q1:** `50 + 5 × 2.10^0.5 = 50 + 5 × 1.449 = 57.2` (spend ₹2,10,000)

### 7.4 Combined Penalty Risk (relevant from Q3 onward)

```
Risk % = max(5%, 40% − 0.25 × Compliance Score − 0.10 × Audit Readiness)
```

**Why Compliance is weighted more heavily (0.25) than Audit Readiness (0.10):** compliance
failures (missed filings, expired certifications) are the more direct, more common trigger for a
real penalty event. Strong audit prep mainly reduces the *severity* and likelihood of escalation
once something goes wrong — a genuinely secondary line of defence.

**Q1:**
```
Risk % = max(5%, 40% − 0.25 × 58.4 − 0.10 × 57.2)
       = max(5%, 40% − 14.6 − 5.72)
       = 19.68% ≈ 19.7%
```
Down from ~40% baseline if Finance/Admin were skipped entirely.

---

## 8. The full calculation chain — order of operations

**Why the departments must be combined in a specific sequence:** each department produces a number
that becomes an input to another department's formula. Marketing's leads feed Sales' capacity
check; Sales' raw conversion rate gets capped by R&D's ceiling; R&D and HR both feed the same
conversion calculation; Operations' Available to Sell is checked against whatever demand survives.
Calculating these out of order is exactly how two real errors happened (see §9).

```
1.  Raw Leads (sum all Marketing channels)
2.  × Brand Score multiplier            [Q2+ only; Brand built in Q1 applies from Q2]
3.  × HR Productivity Multiplier
    → Effective Leads
4.  MIN(Effective Leads, Sales Capacity × (1 − Attrition Rate))
    → Leads Actually Used                          ← HARD GATE 1
5.  Conversion Rate = R&D Conversion Ceiling + Warranty Bonus
                                                   ← HARD GATE 2
6.  Units from funnel = Leads Used × Conversion Rate
7.  + Free repeat units (prior quarter Repeat Rate × prior quarter Units Sold)
8.  MIN(Total Units, Available to Sell)
    → UNITS SOLD                                   ← HARD GATE 3
9.  Revenue = Units Sold × Selling Price
10. COGS    = Units Sold × Manufacturing Cost/Unit
11. Gross Profit = Revenue − COGS
12. − Warranty Cost   = Units Sold × Defect Rate × ₹1,500
13. − Holding Cost    = (Available to Sell − Units Sold) × ₹150
    → Adjusted Gross Profit
14. − Fixed Costs
15. − Total Discretionary Spend
    → NET CASH FLOW
```

### Q1 fully-corrected chain

```
Raw Leads (all 7 Marketing channels)                            2,719
× HR Productivity Multiplier (1.082)                          → 2,941 Effective Leads
MIN against Sales Capacity (2,725)                            → 2,725 Leads Actually Used
    [Sales Capacity is the binding constraint — 216 leads' worth of
     HR-boosted demand exists but cannot physically be handled]

Conversion Rate = R&D Ceiling (19.1%) + Warranty Bonus (1.5%)  = 20.6%
    [R&D's Ceiling is what makes 20.6% the ceiling rather than the much
     higher raw rate Marketing+Sales spend alone would imply]

UNITS SOLD = 2,725 × 20.6%                                     = 562
Revenue    = 562 × ₹9,999                                      = ₹56,15,653
COGS       = 562 × ₹3,087                                      = ₹17,33,449
Gross Profit                                                   = ₹38,82,205
− Warranty Cost (562 × 6.0% × ₹1,500)                          = ₹50,630
− Inventory Holding Cost (729 unsold units × ₹150)             = ₹1,09,411
    [729 = Available to Sell (1,291) − Units Sold (562)]
Adjusted Gross Profit                                          = ₹37,22,163
− Fixed Costs                                                  = ₹23,50,000
− Total Discretionary Spend                                    = ₹45,00,000
────────────────────────────────────────────────────────────────
NET CASH FLOW                                                  = −₹31,27,837
Cash Balance: ₹1,50,00,000 − ₹31,27,837                        = ₹1,18,72,163
```

---

## 9. The two audit errors — implement these as regression tests

### Error 1: The Warranty Bonus was decided but never applied

The Warranty decision (1-year, +1.5 conversion points) was made inside the R&D workspace step, but
the final combined calculation only referenced R&D's Ceiling (19.1%) and didn't add the Warranty
bonus on top, nor subtract its cost from the P&L.

**Fix:** Warranty is additive **after** the ceiling, not subject to it.

### Error 2: HR's Productivity Multiplier was applied to leads without re-checking Sales Capacity

HR's multiplier was correctly applied to Raw Leads (2,719 × 1.082 = 2,941), but the calculation
then used this boosted number directly against the conversion rate **without re-verifying it
against Sales' hard Capacity limit of 2,725**, which had been calculated and locked in several
steps earlier, before HR's multiplier existed in the chain.

**Why re-checking matters:** Sales Capacity represents genuine human bandwidth — a fixed number of
leads a team can handle, no matter how "effective" those leads have become through other
departments' multipliers. A productivity multiplier can make each lead easier to convert, but it
can't make Sales' phones ring for more hours in the day.

**Fix:** `Leads Actually Usable = MIN(Effective Leads, Sales Capacity)` — applied **after** all
multipliers.

### Why the two errors nearly cancelled out — and why that's a coincidence, not validation

The Warranty fix pushed Units Sold up; the Capacity fix pushed it down. They landed very close to
the originally reported figure. **This was a coincidence of this specific quarter's numbers.** In a
different quarter these same two errors could easily compound in the same direction — which is
exactly why re-auditing the full chain before every major report matters.

---

## 10. Q1 closing KPIs

| KPI | Value | Why this KPI |
|---|---|---|
| Net Cash Flow | −₹31,27,837 | The most direct answer to "did this quarter make or lose money" |
| Cash Balance | ₹1,18,72,163 | The most direct answer to "can the company still pay its bills" |
| Cash Runway | ≈3.8 quarters | Converts cash into **time** — the unit that actually matters for a 4-quarter simulation |
| Units Sold | 562 | The ground-truth output every department's spend was trying to influence |
| Gross Margin | 67.5% | Isolates whether the pricing/COGS relationship is healthy, independent of volume |
| CEO Score | 82/100 | Answers "were this quarter's decisions actually good," separate from "did this quarter make money" |

**Why Cash Runway rather than just Cash Balance:** ₹1,18,72,163 sounds like a lot of money in
isolation, but converting it into "3.8 quarters at the current burn rate" makes the actual stakes
immediately legible against the simulation's real 4-quarter horizon.

---

## 11. Valuation model — three methods, blended

**Why blend:** no single method alone is trustworthy for a pre-profit hardware startup after one
quarter.

```
1. Revenue Multiple (Market Approach)   — weighted 70%
   = Annualized Revenue × Multiple
   = (Quarterly Revenue × 4) × 3.0x

2. Asset-Based (Book Value Floor)       — weighted 20%
   = Total Assets − Liabilities

3. Intangible Score Premium              — added IN FULL, not weighted
   = (Brand Score + Innovation Score + Quality Score) × ₹20,000/pt
   + Customers × ₹300

Blended Valuation = 0.70 × Method1 + 0.20 × Method2 + Method3
```

| Method | Reasoning |
|---|---|
| Revenue Multiple, 3.0x | Standard VC approach for growth-stage companies. **3x (not the 8–10x common in SaaS)** reflects hardware's lower margins and higher execution risk. Weighted 70% — the primary story for a growth-stage startup |
| Asset-Based | The "if operations stopped today" floor: cash, inventory, equipment, IP, receivables minus what's owed. Weighted 20% — a sanity check, not the main driver |
| Intangible Premium | Captures goodwill the other two miss — brand recognition, IP, an actual paying customer base. Added in full since it's a pure addition on top |

**Q1 worked calculation:**
```
1. Revenue Multiple  = (₹56,15,653 × 4) × 3.0 = ₹6,73,87,836
2. Asset-Based       = ₹1,84,22,586 − ₹12,00,000 = ₹1,72,22,586
3. Intangible        = (8.7 + 7.5 + 9.95) × ₹20,000 + 4,562 × ₹300 = ₹18,91,600

Blended = (0.70 × ₹6,73,87,836) + (0.20 × ₹1,72,22,586) + ₹18,91,600
        = ₹4,71,71,485 + ₹34,44,517 + ₹18,91,600
        = ₹5,25,07,602 ≈ ₹5.25 crore
```

**Why valuation went UP despite a loss-making quarter:** valuation isn't the same as profit. The
company raised ₹4 crore and, after a tough Q1, is worth ~₹5.25 crore — driven by real revenue
traction, a growing customer base, and the Brand/Innovation/Quality scores built this quarter,
none of which show up in Net Cash Flow. **A company can lose cash and still build enterprise value
in the same quarter, provided the losses are buying something durable.**

Implied return: ₹5.25 Cr vs. ₹4 Cr raised = **1.31x markup after one quarter.**

---

## 12. Q1 allocation summary (for reference)

| Department | Spend | Rationale |
|---|---|---|
| Marketing | ₹16,00,000 | Largest share (35.6%) — the only department that can generate net-new demand from zero |
| Sales | ₹8,00,000 | Sized specifically to match Marketing's projected lead volume (capacity coordination) |
| Operations | ₹6,00,000 | Sized above expected demand, cushioned by the existing 600-unit inventory |
| R&D | ₹5,00,000 | Ended up the most underfunded — its Conversion Ceiling bound tightly |
| HR | ₹3,00,000 | Smallest by design — a multiplier, not a hard gate, so lower ROI per rupee at this scale |
| Finance/Admin | ₹7,00,000 | Above the recommended floor — defensive, reduces future risk |
| **Total Discretionary** | **₹45,00,000** | 39% of the ₹1,16,50,000 ceiling — deliberately moderate-lean in the least-informed quarter |

### Non-allocation financial decisions

| Decision | Choice | Why |
|---|---|---|
| Pricing | Keep ₹9,999 | Changing price and every department's spend in the same quarter would make it impossible to tell which change caused which effect. Establishes a clean baseline |
| External loan | No | Borrowing against an unproven business model before any formula had been tested even once |
| Supplier terms | Extended 60 days | Middle ground: 30 days keeps zero cash-flow benefit; 90 days risks straining a brand-new supplier relationship |
| Buffer stance | Protect strictly | Q1 is the least-informed quarter, and every compounding benefit is designed to pay off in Q2/Q3 |
| Warranty | 1 year (+1.5 pts) | |
