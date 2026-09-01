"""
Tests for Decision Intelligence PDF generation.

These tests verify:
1. PDF rendering produces valid output (byte-for-byte determinism)
2. Edge cases (long names, missing optional fields) don't break layout
3. All 12 pages are present in output
4. Docker environment compatibility (Chromium dependencies)
"""

import pytest
from datetime import datetime

from app.schemas.decision_intelligence_report import (
    AdaptabilityPage,
    AdaptabilityRow,
    CompanyMetric,
    CompanyOutcomePage,
    CoverPage,
    DecisionIntelligenceReport,
    DecisionSignaturePage,
    DecisionThatMatteredPage,
    DimensionScore,
    MissedOpportunitiesPage,
    MissedOpportunity,
    NextMovePage,
    ProfilePage,
    QuarterEntry,
    Recommendation,
    ReportMetadata,
    RiskPage,
    ScoreExplanationPage,
    ScoreModifier,
    StrengthPage,
    YearCreatedPage,
)
from app.services.pdf.decision_intelligence import render_decision_intelligence_pdf


# ─── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def reference_report_data() -> DecisionIntelligenceReport:
    """
    Reference report fixture matching myelin-decision-intelligence-report-RAFI.pdf.
    
    This fixture represents a "known good" report that should render consistently.
    Use this as the baseline for determinism testing.
    """
    return DecisionIntelligenceReport(
        metadata=ReportMetadata(
            company_name="NadiWear Technologies",
            ceo_name="Rafi Chowdhury",
            source="Simulation Run #1",
            generated_date=datetime(2026, 9, 1).strftime("%B %d, %Y"),
        ),
        page_01_cover=CoverPage(
            final_score=72.5,
            verdict_label="Competent",
            outcome_quote="You finished the year independent and hit the covenant.",
            decision_maker_profile=(
                "A pragmatic operator who prioritized capital efficiency and customer "
                "retention over aggressive growth. Demonstrated strong risk management "
                "through conservative cash allocation, but missed opportunities to scale "
                "product capabilities when market conditions were favorable."
            ),
        ),
        page_02_year_created=YearCreatedPage(
            quarters=[
                QuarterEntry(
                    quarter_number=1,
                    quarter_score=68.0,
                    verdict="Adequate",
                    decision_text=(
                        "Allocated heavily to sales and marketing (45% combined) while keeping "
                        "product investment minimal (12%). Prioritized customer acquisition."
                    ),
                    consequence_text=(
                        "Revenue grew 18% but customer churn increased to 24%. Product gaps "
                        "cited in 3 lost deals. Cash runway extended to 7 quarters."
                    ),
                    flagged=False,
                ),
                QuarterEntry(
                    quarter_number=2,
                    quarter_score=75.5,
                    verdict="Strong",
                    decision_text=(
                        "Shifted focus to product (30%) and CX (18%). Reduced marketing spend "
                        "to address retention issues flagged in Q1."
                    ),
                    consequence_text=(
                        "Churn dropped to 16%. NPS improved from 42 to 58. Revenue growth "
                        "slowed to 9% as lead pipeline cooled from reduced marketing."
                    ),
                    flagged=True,
                ),
                QuarterEntry(
                    quarter_number=3,
                    quarter_score=71.0,
                    verdict="Competent",
                    decision_text=(
                        "Balanced allocation: 22% product, 20% sales, 18% marketing. "
                        "Responded to competitor launch with defensive positioning."
                    ),
                    consequence_text=(
                        "Market share declined from 18% to 14%. Revenue flat. Competitor "
                        "captured 3 enterprise deals with feature parity + lower pricing."
                    ),
                    flagged=False,
                ),
                QuarterEntry(
                    quarter_number=4,
                    quarter_score=74.5,
                    verdict="Strong",
                    decision_text=(
                        "Aggressive product push (35%) to close feature gap. Raised pricing "
                        "8% to improve unit economics rather than chase volume."
                    ),
                    consequence_text=(
                        "Launched 4 high-value features. Revenue up 21%, driven by expansion "
                        "in existing accounts. Lost 2 price-sensitive prospects."
                    ),
                    flagged=False,
                ),
            ]
        ),
        page_03_profile=ProfilePage(
            dimensions=[
                DimensionScore(
                    dimension="long_term_thinking",
                    dimension_label="Long-Term Thinking",
                    score=78.0,
                    evidence_summary=(
                        "Consistently prioritized cash runway over short-term growth. "
                        "Q2 product investment showed willingness to sacrifice near-term "
                        "revenue for retention."
                    ),
                ),
                DimensionScore(
                    dimension="capital_allocation",
                    dimension_label="Capital Allocation",
                    score=82.0,
                    evidence_summary=(
                        "Strong discipline in spend allocation. Pivoted quickly in Q2 when "
                        "data signaled retention risk. Never over-indexed on single function."
                    ),
                ),
                DimensionScore(
                    dimension="leadership",
                    dimension_label="Leadership",
                    score=65.0,
                    evidence_summary=(
                        "Adequate but unexceptional. Team morale remained stable (68/100) "
                        "but never inspired. No evidence of proactive culture-building."
                    ),
                ),
                DimensionScore(
                    dimension="strategic_thinking",
                    dimension_label="Strategic Thinking",
                    score=58.0,
                    evidence_summary=(
                        "Reactive rather than anticipatory. Q3 competitor response was "
                        "defensive. Missed signals that market was shifting to platform plays."
                    ),
                ),
                DimensionScore(
                    dimension="risk_management",
                    dimension_label="Risk Management",
                    score=85.0,
                    evidence_summary=(
                        "Exceptional cash discipline. Never dropped below 5 quarters runway. "
                        "Q4 pricing increase showed comfort with calculated risk."
                    ),
                ),
                DimensionScore(
                    dimension="systems_thinking",
                    dimension_label="Systems Thinking",
                    score=62.0,
                    evidence_summary=(
                        "Recognized interdependencies between CX and retention in Q2, but "
                        "took 2 quarters to connect product gaps to competitive loss."
                    ),
                ),
                DimensionScore(
                    dimension="adaptability",
                    dimension_label="Adaptability",
                    score=71.0,
                    evidence_summary=(
                        "Pivoted effectively in Q2 when retention data emerged. Q4 pricing "
                        "shift showed willingness to change approach mid-year."
                    ),
                ),
            ]
        ),
        page_04_strength=StrengthPage(
            strength_dimension="Risk Management",
            strength_score=85.0,
            headline="Cash Discipline Under Pressure",
            evidence_bullets=[
                "Maintained 5+ quarters runway throughout the year despite revenue volatility",
                "Q2 decision to prioritize retention over growth preserved capital efficiency",
                "Q4 pricing increase showed comfort taking calculated risks when model supported it",
                "Never over-allocated to single function; kept reserves for unexpected pivots",
            ],
            narrative=(
                "Your strongest dimension is risk management, reflected in exceptional cash "
                "discipline throughout the year. You consistently prioritized runway extension "
                "over aggressive growth, a choice that proved critical when competitive pressure "
                "emerged in Q3. The Q2 pivot away from marketing spend—despite strong acquisition "
                "momentum—demonstrated rare willingness to sacrifice short-term wins for structural "
                "health. Your Q4 pricing increase, backed by unit economics data, showed that your "
                "risk management wasn't about avoidance but about taking informed, calculated bets "
                "when the model supported them."
            ),
        ),
        page_05_risk=RiskPage(
            risk_dimension="Strategic Thinking",
            risk_score=58.0,
            headline="Reactive Positioning in a Shifting Market",
            evidence_bullets=[
                "Q3 competitor response was defensive rather than anticipatory",
                "Missed early signals that market was consolidating around platform players",
                "No evidence of proactive market analysis driving allocation decisions",
                "Q1-Q2 strategy gap: prioritized sales before understanding product-market fit depth",
            ],
            narrative=(
                "Your most exposed dimension is strategic thinking, where you scored in the bottom "
                "quartile. The pattern across the year was reactive decision-making: you responded "
                "to retention data in Q2 and competitive threats in Q3, but rarely positioned ahead "
                "of market shifts. The Q1 heavy investment in sales and marketing, before validating "
                "that your product could retain customers at scale, is emblematic—you optimized for "
                "acquisition without a retention thesis. By Q3, when a competitor launched with "
                "feature parity, your response was defensive repositioning rather than a strategic "
                "counter. You regained footing in Q4, but the year overall shows a pattern of "
                "fighting the last quarter's fire rather than positioning for the next one."
            ),
        ),
        page_06_decision_that_mattered=DecisionThatMatteredPage(
            quarter=2,
            what_you_knew=(
                "Q1 revenue grew 18%, but churn spiked to 24% and NPS dropped to 42. "
                "3 enterprise deals cited product gaps as exit reasons. Sales pipeline "
                "remained strong from Q1 marketing push."
            ),
            what_you_decided=(
                "Shifted 30% of budget to product and 18% to CX, cutting marketing from "
                "28% to 12%. Prioritized retention over acquisition for the first time."
            ),
            what_you_risked=(
                "Near-term revenue growth. Marketing cuts would slow lead generation. "
                "If product investments didn't land, you'd have both retention problems "
                "AND a cooling pipeline."
            ),
            what_happened=(
                "Churn dropped from 24% to 16%. NPS recovered to 58. Revenue growth "
                "slowed to 9%, as predicted, but unit economics improved 14%. You traded "
                "volume for margin."
            ),
            why_it_mattered=(
                "This decision defined your year. By Q4, you were competing on product "
                "strength rather than sales aggression—a position that protected you when "
                "a competitor undercut on price. If you'd kept optimizing for acquisition "
                "through Q2, the Q3 competitive threat would have been existential rather "
                "than manageable."
            ),
            data_inconsistency_note=(
                "Note: Q2 closing cash balance ($2.8M) is $180K higher than opening balance "
                "($2.62M) plus reported net cash flow ($4K). Likely discrepancy in accrual "
                "vs. cash accounting for deferred revenue."
            ),
        ),
        page_07_missed_opportunities=MissedOpportunitiesPage(
            headline="Unused Capacity and Overlooked Leverage",
            opportunities=[
                MissedOpportunity(
                    label="Funding Never Deployed",
                    value="$1.2M",
                    explanation=(
                        "You ended the year with $3.1M in the bank, well above survival "
                        "needs. You could have deployed $1.2M more aggressively into product "
                        "or market expansion without material risk."
                    ),
                ),
                MissedOpportunity(
                    label="Headcount Unused",
                    value="8 FTE",
                    explanation=(
                        "Your hiring plan budgeted 32 FTE by year-end but you ended at 24. "
                        "The 8 unfilled roles (mostly eng + sales) represent missed execution "
                        "capacity."
                    ),
                ),
                MissedOpportunity(
                    label="Partnership Revenue",
                    value="$340K ARR",
                    explanation=(
                        "2 strategic partnership opportunities emerged in Q3 but you didn't "
                        "allocate BD resources to close them. Estimated loss: $340K ARR."
                    ),
                ),
            ],
        ),
        page_08_adaptability=AdaptabilityPage(
            rows=[
                AdaptabilityRow(
                    quarter=1,
                    allocation_focus="Sales & Marketing (45% combined)",
                    changed_from_prior=False,
                    adaptability_score=50.0,
                ),
                AdaptabilityRow(
                    quarter=2,
                    allocation_focus="Product & CX (48% combined)",
                    changed_from_prior=True,
                    adaptability_score=82.0,
                ),
                AdaptabilityRow(
                    quarter=3,
                    allocation_focus="Balanced (no single function >22%)",
                    changed_from_prior=True,
                    adaptability_score=68.0,
                ),
                AdaptabilityRow(
                    quarter=4,
                    allocation_focus="Product-Led (35% product)",
                    changed_from_prior=True,
                    adaptability_score=75.0,
                ),
            ],
            summary=(
                "You pivoted 3 times across 4 quarters—above-average adaptability. The Q2 shift "
                "from sales-led to retention-focused was your strongest strategic adjustment. Q3 "
                "diversification showed caution in response to competitive threat. Q4 return to "
                "product concentration suggests confidence that feature gap was the real constraint."
            ),
        ),
        page_09_decision_signature=DecisionSignaturePage(
            signature_headline="Data-Responsive Pragmatist",
            signature_bullets=[
                "You pivot quickly when data signals a problem, but rarely position ahead of trends",
                "Cash discipline is your guardrail—you optimize within a tight risk envelope",
                "You favor incremental iteration over big strategic bets",
                "Team morale and culture are stable but not a source of competitive advantage",
                "You're more comfortable defending existing position than capturing new market",
            ],
            overall_narrative=(
                "Your decision signature is that of a data-responsive pragmatist: you run a tight "
                "financial ship, respond quickly to performance signals, and rarely take unforced "
                "errors. Your strength is operational discipline—you don't chase shiny objects, you "
                "don't over-index on single bets, and you preserve optionality. Your limitation is "
                "strategic ambition: you're playing not to lose rather than playing to win. When the "
                "market gives you a clear signal (Q2 retention crisis), you adjust fast and effectively. "
                "But you don't often create your own opportunities—you optimize within the game as "
                "it's presented rather than reshaping the game itself. For a first-time founder in a "
                "resource-constrained environment, this is a defensible posture. For a repeat founder "
                "or a well-funded startup, it's a growth limiter."
            ),
        ),
        page_10_score_explained=ScoreExplanationPage(
            base_score=70.0,
            positive_modifiers=[
                ScoreModifier(label="Capital Efficiency Discipline", value=5.5, is_positive=True),
                ScoreModifier(label="Q2 Retention Pivot", value=4.0, is_positive=True),
                ScoreModifier(label="Q4 Pricing Courage", value=3.0, is_positive=True),
            ],
            negative_modifiers=[
                ScoreModifier(label="Reactive Strategic Positioning", value=-6.0, is_positive=False),
                ScoreModifier(label="Missed Partnership Opportunities", value=-2.5, is_positive=False),
                ScoreModifier(label="Underutilized Hiring Capacity", value=-1.5, is_positive=False),
            ],
            final_score=72.5,
            explanation=(
                "Your base mechanical score of 70.0 reflects competent but unexceptional execution "
                "across the seven dimensions. Positive modifiers (+12.5 total) recognize exceptional "
                "cash discipline, the pivotal Q2 retention decision, and the calculated Q4 pricing risk. "
                "Negative modifiers (−10.0 total) penalize reactive strategic positioning, missed BD "
                "opportunities, and underutilized hiring capacity. Net result: 72.5, placing you in the "
                "'Competent' band—you finished the year solvent and positioned for continuity, but not "
                "breakthrough growth."
            ),
        ),
        page_11_company_outcome=CompanyOutcomePage(
            outcome_headline="Finished Year Independent · Covenant Met",
            metrics=[
                CompanyMetric(label="Final Valuation", value="₹42 Cr", context="Post-money, internal"),
                CompanyMetric(label="Final Revenue (Q4)", value="₹1.18 Cr", context="+21% QoQ"),
                CompanyMetric(label="Closing Cash", value="₹3.1 Cr", context="6.8 quarters runway"),
                CompanyMetric(label="Customer Count", value="124", context="Net +8 from Q1"),
                CompanyMetric(label="Market Share", value="14%", context="Down from 18% in Q1"),
                CompanyMetric(label="NPS", value="58", context="Recovered from Q1 low of 42"),
                CompanyMetric(label="Headcount", value="24 FTE", context="8 below hiring plan"),
                CompanyMetric(label="Gross Margin", value="62%", context="Improved 7pp from Q1"),
            ],
        ),
        page_12_next_move=NextMovePage(
            recommendations=[
                Recommendation(
                    title="Develop a Forward-Looking Strategic Thesis",
                    body=(
                        "Your reactive decision pattern worked this year because the market gave you clear "
                        "feedback loops (Q2 churn spike, Q3 competitor launch). Next year, develop a 12-month "
                        "strategic hypothesis and run quarterly 'pre-mortems'—what could kill us that we're not "
                        "seeing yet? Allocate 10% of your time to scenario planning, not just performance review."
                    ),
                ),
                Recommendation(
                    title="Use Excess Capital as Strategic Optionality",
                    body=(
                        "Ending the year with ₹3.1 Cr (~7 quarters runway) is commendable discipline, but ₹1.2M "
                        "of that is over-reserved. Consider a 'strategic reserve' model: maintain 5Q runway as your "
                        "floor, then deploy excess capital into calculated bets (partnerships, M&A, product moonshots) "
                        "that could shift your market position rather than just sustain it."
                    ),
                ),
                Recommendation(
                    title="Invest in Leading Indicators, Not Just Lagging Data",
                    body=(
                        "Your Q2 pivot was triggered by churn (a lagging indicator). Build a dashboard of leading "
                        "indicators: support ticket sentiment, feature request frequency, time-to-value metrics, "
                        "competitive win/loss reasons. This will let you position ahead of crises rather than respond "
                        "to them."
                    ),
                ),
                Recommendation(
                    title="Close the Strategy-Execution Gap on Partnerships",
                    body=(
                        "You missed ₹340K ARR in partnership revenue because you didn't staff BD. Either commit to "
                        "partnerships as a growth channel (hire a BD lead, allocate 8% of budget) or explicitly decide "
                        "it's not your model and stop evaluating inbound partnership opportunities—the current 'yes in "
                        "principle, no in practice' stance is a leak."
                    ),
                ),
            ],
        ),
    )


@pytest.fixture
def edge_case_report_data() -> DecisionIntelligenceReport:
    """
    Edge case report with long names, missing optional fields, and boundary values.
    
    Tests layout robustness when data exceeds typical bounds.
    """
    return DecisionIntelligenceReport(
        metadata=ReportMetadata(
            company_name="A Very Long Company Name That Should Wrap Gracefully Across Multiple Lines",
            ceo_name="Dr. Firstname Middlename Lastname-Hyphenated III",
            source="Extended Simulation with Additional Context",
            generated_date="September 1, 2026",
        ),
        page_01_cover=CoverPage(
            final_score=100.0,  # Boundary: max score
            verdict_label="Exceptional",
            outcome_quote="You achieved every goal and exceeded all expectations.",
            decision_maker_profile="Minimal profile text.",
        ),
        page_02_year_created=YearCreatedPage(
            quarters=[
                QuarterEntry(
                    quarter_number=i,
                    quarter_score=25.0 * i,  # 25, 50, 75, 100
                    verdict="Varies",
                    decision_text="Short decision.",
                    consequence_text="Short consequence.",
                    flagged=i % 2 == 0,
                )
                for i in range(1, 5)
            ]
        ),
        page_03_profile=ProfilePage(
            dimensions=[
                DimensionScore(
                    dimension=dim,
                    dimension_label=dim.replace("_", " ").title(),
                    score=0.0 if i == 0 else 100.0,  # Test boundary: 0% and 100%
                    evidence_summary="Minimal evidence.",
                )
                for i, dim in enumerate(
                    [
                        "long_term_thinking",
                        "capital_allocation",
                        "leadership",
                        "strategic_thinking",
                        "risk_management",
                        "systems_thinking",
                        "adaptability",
                    ]
                )
            ]
        ),
        page_04_strength=StrengthPage(
            strength_dimension="All Dimensions",
            strength_score=100.0,
            headline="Perfect Execution",
            evidence_bullets=["First bullet", "Second bullet"],
            narrative="Minimal narrative.",
        ),
        page_05_risk=RiskPage(
            risk_dimension="None",
            risk_score=0.0,
            headline="No Risks Identified",
            evidence_bullets=["Single bullet"],
            narrative="No risks.",
        ),
        page_06_decision_that_mattered=DecisionThatMatteredPage(
            quarter=1,
            what_you_knew="Minimal context.",
            what_you_decided="Minimal decision.",
            what_you_risked="Nothing.",
            what_happened="Nothing.",
            why_it_mattered="It didn't.",
            data_inconsistency_note=None,  # Test missing optional field
        ),
        page_07_missed_opportunities=MissedOpportunitiesPage(
            headline="Nothing Missed",
            opportunities=[
                MissedOpportunity(
                    label="Perfect Execution",
                    value="$0",
                    explanation="No opportunities missed.",
                )
            ],
        ),
        page_08_adaptability=AdaptabilityPage(
            rows=[
                AdaptabilityRow(
                    quarter=i,
                    allocation_focus="Same every quarter",
                    changed_from_prior=False,
                    adaptability_score=50.0,
                )
                for i in range(1, 5)
            ],
            summary="No adaptation needed.",
        ),
        page_09_decision_signature=DecisionSignaturePage(
            signature_headline="Unchanging Approach",
            signature_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
            overall_narrative="Consistent throughout.",
        ),
        page_10_score_explained=ScoreExplanationPage(
            base_score=100.0,
            positive_modifiers=[],  # Test empty lists
            negative_modifiers=[],
            final_score=100.0,
            explanation="Perfect score, no modifiers.",
        ),
        page_11_company_outcome=CompanyOutcomePage(
            outcome_headline="Total Success",
            metrics=[
                CompanyMetric(label="Metric", value="Value", context=None)  # Test missing context
            ],
        ),
        page_12_next_move=NextMovePage(
            recommendations=[
                Recommendation(
                    title="Keep Doing What You're Doing",
                    body="No changes needed.",
                )
            ],
        ),
    )


# ─── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_render_reference_report_produces_valid_pdf(
    reference_report_data: DecisionIntelligenceReport,
):
    """Test that the reference report renders to a valid PDF."""
    pdf_bytes = await render_decision_intelligence_pdf(reference_report_data)
    
    # Basic validation: PDF magic number
    assert pdf_bytes[:4] == b"%PDF", "Output should start with PDF magic number"
    assert len(pdf_bytes) > 10_000, "PDF should be >10KB (realistic minimum for 12-page report)"
    assert len(pdf_bytes) < 5_000_000, "PDF should be <5MB (sanity check for bloat)"
    
    # PDF should end with %%EOF
    assert b"%%EOF" in pdf_bytes[-100:], "PDF should end with %%EOF marker"


@pytest.mark.asyncio
async def test_render_edge_case_report_does_not_crash(
    edge_case_report_data: DecisionIntelligenceReport,
):
    """Test that edge case data (long names, boundary values) renders without error."""
    pdf_bytes = await render_decision_intelligence_pdf(edge_case_report_data)
    
    # Should still produce valid PDF
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 5_000  # Smaller than reference due to minimal content


@pytest.mark.asyncio
async def test_render_determinism(reference_report_data: DecisionIntelligenceReport):
    """
    Test that rendering the same data twice produces identical output.
    
    This is critical for caching and regression detection. If this test fails,
    it suggests non-deterministic rendering (font loading races, timestamps in PDF metadata, etc.)
    """
    pdf_1 = await render_decision_intelligence_pdf(reference_report_data)
    pdf_2 = await render_decision_intelligence_pdf(reference_report_data)
    
    # Note: Playwright PDF generation *may* include timestamps or other metadata that varies.
    # If this assertion fails consistently, we may need to strip metadata or accept
    # "functional equivalence" instead of byte-for-byte identity.
    # For now, we assert strict equality as the ideal.
    assert pdf_1 == pdf_2, "Rendering should be deterministic (byte-for-byte identical)"


@pytest.mark.asyncio
async def test_page_count_is_exactly_12(reference_report_data: DecisionIntelligenceReport):
    """
    Test that output is always exactly 12 pages.
    
    This is a design requirement: content should be sized/truncated to fit 12 pages,
    never more, never fewer.
    """
    pdf_bytes = await render_decision_intelligence_pdf(reference_report_data)
    
    # Count pages by looking for page objects in PDF structure
    # This is a heuristic (not a full PDF parser), but should work for Playwright output
    page_count = pdf_bytes.count(b"/Type /Page")
    
    assert page_count == 12, f"PDF should have exactly 12 pages, got {page_count}"


@pytest.mark.asyncio
async def test_company_name_in_footer(reference_report_data: DecisionIntelligenceReport):
    """Test that company name appears in PDF footer on every page."""
    pdf_bytes = await render_decision_intelligence_pdf(reference_report_data)
    
    # Company name should appear in PDF content streams
    # This is a weak test (doesn't verify positioning), but catches complete omission
    company_name_encoded = reference_report_data.metadata.company_name.encode("utf-8")
    assert company_name_encoded in pdf_bytes, "Company name should appear in PDF content"


@pytest.mark.asyncio
async def test_missing_optional_fields_does_not_crash(reference_report_data: DecisionIntelligenceReport):
    """Test that missing optional fields (e.g., data_inconsistency_note) render gracefully."""
    # Remove optional field
    reference_report_data.page_06_decision_that_mattered.data_inconsistency_note = None
    
    pdf_bytes = await render_decision_intelligence_pdf(reference_report_data)
    assert pdf_bytes[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_empty_modifier_lists(reference_report_data: DecisionIntelligenceReport):
    """Test that empty positive/negative modifier lists don't break score page."""
    reference_report_data.page_10_score_explained.positive_modifiers = []
    reference_report_data.page_10_score_explained.negative_modifiers = []
    
    pdf_bytes = await render_decision_intelligence_pdf(reference_report_data)
    assert pdf_bytes[:4] == b"%PDF"


def test_sync_wrapper(reference_report_data: DecisionIntelligenceReport):
    """Test that the synchronous wrapper works for non-async contexts."""
    from app.services.pdf.decision_intelligence.render import render_decision_intelligence_pdf_sync
    
    pdf_bytes = render_decision_intelligence_pdf_sync(reference_report_data)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 10_000


# ─── Performance Benchmarks (informational, not hard failures) ──────────────────


@pytest.mark.asyncio
async def test_render_performance_baseline(reference_report_data: DecisionIntelligenceReport):
    """
    Benchmark rendering time (informational, not a hard assertion).
    
    Expected performance:
    - First render (cold browser): ~1-2s
    - Subsequent renders (warm browser): <500ms
    
    This test runs twice and logs timings. It doesn't fail on slow renders
    (CI environments can be unpredictable), but provides a baseline for regression detection.
    """
    import time
    
    # First render (cold browser startup)
    start = time.time()
    await render_decision_intelligence_pdf(reference_report_data)
    cold_duration = time.time() - start
    
    # Second render (browser already running)
    start = time.time()
    await render_decision_intelligence_pdf(reference_report_data)
    warm_duration = time.time() - start
    
    print(f"\nRender performance (informational):")
    print(f"  Cold (first render): {cold_duration:.2f}s")
    print(f"  Warm (reuse browser): {warm_duration:.2f}s")
    
    # Informational assertions (loose bounds to avoid CI flakiness)
    assert cold_duration < 10.0, "Cold render should complete within 10s (even on slow CI)"
    assert warm_duration < 5.0, "Warm render should complete within 5s"
