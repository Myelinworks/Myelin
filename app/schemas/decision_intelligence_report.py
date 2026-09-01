"""
Pydantic schemas for Decision Intelligence Report PDF generation.

This schema models the complete 12-page Decision Intelligence report template,
structured to match myelin-decision-intelligence-report-RAFI.pdf.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ─── Core metadata ──────────────────────────────────────────────────────────────

class ReportMetadata(BaseModel):
    """Report header and footer metadata."""
    
    company_name: str = Field(..., description="Company name for header and footer")
    ceo_name: str = Field(..., description="CEO/decision-maker name")
    source: str = Field(..., description="Source label (e.g., 'Simulation', 'Live Run')")
    generated_date: str = Field(..., description="Report generation date (formatted)")


# ─── Page 1: Cover + Decision Maker Profile ────────────────────────────────────

class CoverPage(BaseModel):
    """Cover page with final score and outcome."""
    
    final_score: float = Field(..., ge=0, le=100, description="Overall decision intelligence score")
    verdict_label: str = Field(..., description="Score band label (e.g., 'Strong', 'Competent')")
    outcome_quote: str = Field(..., description="One-sentence outcome statement")
    decision_maker_profile: str = Field(
        ...,
        description="Paragraph describing the decision-maker's style and approach",
    )


# ─── Page 2: Year You Created (Quarterly Timeline) ─────────────────────────────

class QuarterEntry(BaseModel):
    """Single quarter decision and consequence entry."""
    
    quarter_number: int = Field(..., ge=1, le=4, description="Quarter number (1-4)")
    quarter_score: float = Field(..., ge=0, le=100, description="Quarter score")
    verdict: str = Field(..., description="Quarter verdict label")
    decision_text: str = Field(..., description="What you decided this quarter")
    consequence_text: str = Field(..., description="What happened as a result")
    flagged: bool = Field(default=False, description="Whether this quarter is flagged as notable")


class YearCreatedPage(BaseModel):
    """Timeline of quarterly decisions and consequences."""
    
    quarters: list[QuarterEntry] = Field(..., min_length=4, max_length=4)


# ─── Page 3: Seven-Dimension Profile ───────────────────────────────────────────

class DimensionScore(BaseModel):
    """Score for one of seven decision-making dimensions."""
    
    dimension: Literal[
        "long_term_thinking",
        "capital_allocation",
        "leadership",
        "strategic_thinking",
        "risk_management",
        "systems_thinking",
        "adaptability",
    ]
    dimension_label: str = Field(..., description="Human-readable dimension name")
    score: float = Field(..., ge=0, le=100, description="Dimension score (0-100)")
    evidence_summary: str = Field(..., description="Brief evidence/explanation")


class ProfilePage(BaseModel):
    """Seven-dimension decision-making profile."""
    
    dimensions: list[DimensionScore] = Field(..., min_length=7, max_length=7)


# ─── Page 4: Biggest Strength Deep-Dive ────────────────────────────────────────

class StrengthPage(BaseModel):
    """Deep-dive into the decision-maker's biggest strength."""
    
    strength_dimension: str = Field(..., description="Which dimension is the strength")
    strength_score: float = Field(..., ge=0, le=100)
    headline: str = Field(..., description="Strength headline/title")
    evidence_bullets: list[str] = Field(..., min_length=1, description="Evidence bullet points")
    narrative: str = Field(..., description="Narrative paragraph explaining the strength")


# ─── Page 5: Biggest Decision Risk ─────────────────────────────────────────────

class RiskPage(BaseModel):
    """Deep-dive into the decision-maker's biggest risk/weakness."""
    
    risk_dimension: str = Field(..., description="Which dimension is most exposed")
    risk_score: float = Field(..., ge=0, le=100)
    headline: str = Field(..., description="Risk headline/title")
    evidence_bullets: list[str] = Field(..., min_length=1, description="Evidence bullet points")
    narrative: str = Field(..., description="Narrative paragraph explaining the risk")


# ─── Page 6: Decision That Mattered Most ───────────────────────────────────────

class DecisionThatMatteredPage(BaseModel):
    """Breakdown of the single most consequential decision."""
    
    quarter: int = Field(..., ge=1, le=4, description="Quarter when decision was made")
    what_you_knew: str = Field(..., description="Context available at the time")
    what_you_decided: str = Field(..., description="The decision made")
    what_you_risked: str = Field(..., description="What was at stake")
    what_happened: str = Field(..., description="Actual outcome")
    why_it_mattered: str = Field(..., description="Impact explanation")
    data_inconsistency_note: Optional[str] = Field(
        None,
        description="Optional callout for data gaps or reporting inconsistencies",
    )


# ─── Page 7: What You Missed ───────────────────────────────────────────────────

class MissedOpportunity(BaseModel):
    """Unused capability stat callout."""
    
    label: str = Field(..., description="What was unused (e.g., 'Funding never deployed')")
    value: str = Field(..., description="Quantified missed opportunity")
    explanation: str = Field(..., description="Why it was missed and the cost")


class MissedOpportunitiesPage(BaseModel):
    """What the decision-maker failed to leverage."""
    
    headline: str = Field(..., description="Overall missed opportunity theme")
    opportunities: list[MissedOpportunity] = Field(..., min_length=1)


# ─── Page 8: Adaptability Table ────────────────────────────────────────────────

class AdaptabilityRow(BaseModel):
    """Single row in the adaptability tracking table."""
    
    quarter: int = Field(..., ge=1, le=4)
    allocation_focus: str = Field(..., description="Where effort was allocated")
    changed_from_prior: bool = Field(..., description="Whether strategy shifted")
    adaptability_score: float = Field(..., ge=0, le=100)


class AdaptabilityPage(BaseModel):
    """Quarterly adaptability analysis table."""
    
    rows: list[AdaptabilityRow] = Field(..., min_length=4, max_length=4)
    summary: str = Field(..., description="Summary interpretation of adaptability pattern")


# ─── Page 9: Decision Signature ────────────────────────────────────────────────

class DecisionSignaturePage(BaseModel):
    """Narrative characterization of decision-making pattern."""
    
    signature_headline: str = Field(..., description="Decision signature title")
    signature_bullets: list[str] = Field(
        ...,
        min_length=3,
        description="Key characteristics of decision-making style",
    )
    overall_narrative: str = Field(
        ...,
        description="Cohesive narrative explaining the decision signature",
    )


# ─── Page 10: Final Score Explained ────────────────────────────────────────────

class ScoreModifier(BaseModel):
    """Single modifier that adjusted the final score."""
    
    label: str = Field(..., description="Modifier name")
    value: float = Field(..., description="Points added or subtracted")
    is_positive: bool = Field(..., description="Whether this is a boost or penalty")


class ScoreExplanationPage(BaseModel):
    """Score math breakdown with all modifiers."""
    
    base_score: float = Field(..., ge=0, le=100, description="Starting mechanical score")
    positive_modifiers: list[ScoreModifier] = Field(default_factory=list)
    negative_modifiers: list[ScoreModifier] = Field(default_factory=list)
    final_score: float = Field(..., ge=0, le=100, description="Final computed score")
    explanation: str = Field(..., description="How the score was calculated")


# ─── Page 11: What Happened to the Company ─────────────────────────────────────

class CompanyMetric(BaseModel):
    """Single company outcome metric."""
    
    label: str = Field(..., description="Metric name")
    value: str = Field(..., description="Formatted metric value")
    context: Optional[str] = Field(None, description="Optional comparison or context")


class CompanyOutcomePage(BaseModel):
    """Final company state metrics grid."""
    
    outcome_headline: str = Field(..., description="Overall company outcome (sold, failed, independent)")
    metrics: list[CompanyMetric] = Field(..., min_length=1, description="Final metrics grid")


# ─── Page 12: Your Next Move ───────────────────────────────────────────────────

class Recommendation(BaseModel):
    """Single actionable recommendation."""
    
    title: str = Field(..., description="Recommendation title")
    body: str = Field(..., description="Detailed recommendation text")


class NextMovePage(BaseModel):
    """Recommendations for improving decision-making."""
    
    recommendations: list[Recommendation] = Field(..., min_length=1, max_length=4)


# ─── Top-Level Report Schema ───────────────────────────────────────────────────

class DecisionIntelligenceReport(BaseModel):
    """
    Complete 12-page Decision Intelligence Report.
    
    This schema represents all data required to render the full report template.
    Every page's content is explicitly modeled to ensure nothing is left implicit.
    """
    
    metadata: ReportMetadata
    page_01_cover: CoverPage
    page_02_year_created: YearCreatedPage
    page_03_profile: ProfilePage
    page_04_strength: StrengthPage
    page_05_risk: RiskPage
    page_06_decision_that_mattered: DecisionThatMatteredPage
    page_07_missed_opportunities: MissedOpportunitiesPage
    page_08_adaptability: AdaptabilityPage
    page_09_decision_signature: DecisionSignaturePage
    page_10_score_explained: ScoreExplanationPage
    page_11_company_outcome: CompanyOutcomePage
    page_12_next_move: NextMovePage
