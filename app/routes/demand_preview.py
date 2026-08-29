"""
API endpoints for demand preview and buyer interest estimation.

Allows frontend to show dynamic buyer interest numbers before allocation is finalized.
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.engines.demand_dynamics import (
    MarketState,
    MarketingInvestment,
    estimate_addressable_demand,
    calculate_full_demand,
)
from app.models.company import Company
from app.models.quarter import Quarter

router = APIRouter(prefix="/api/demand", tags=["demand-preview"])


class DemandPreviewRequest(BaseModel):
    """Request to preview demand based on current state and planned investments"""
    company_id: str
    quarter: int
    
    # Marketing spend (lakhs)
    google_ads: Decimal = Field(default=Decimal("0"), ge=0)
    meta_ads: Decimal = Field(default=Decimal("0"), ge=0)
    social_influencer: Decimal = Field(default=Decimal("0"), ge=0)
    content_seo: Decimal = Field(default=Decimal("0"), ge=0)
    events_pr: Decimal = Field(default=Decimal("0"), ge=0)
    email: Decimal = Field(default=Decimal("0"), ge=0)
    direct_marketing: Decimal = Field(default=Decimal("0"), ge=0)
    referral: Decimal = Field(default=Decimal("0"), ge=0)
    
    # Optional: if user wants to see impact of product improvements
    brand_boost: Decimal = Field(default=Decimal("0"))
    innovation_boost: Decimal = Field(default=Decimal("0"))
    quality_boost: Decimal = Field(default=Decimal("0"))


class DemandPreviewResponse(BaseModel):
    """Addressable demand estimate"""
    addressable_demand_units: int
    total_market_demand: int
    our_market_share_potential: str  # percentage
    competitive_position_score: str
    
    # Breakdown for transparency
    product_pull_score: str
    rival_total_strength: str
    marketing_voice_index: str
    
    # Guidance
    guidance_message: str


class DetailedDemandResponse(BaseModel):
    """Full demand calculation breakdown for dashboard"""
    addressable_demand_units: int
    total_market_demand: int
    attractive_share_pct: str
    
    # Lead generation by channel
    google_leads: int
    meta_leads: int
    social_leads: int
    content_leads: int
    events_leads: int
    email_leads: int
    direct_leads: int
    total_raw_leads: int
    effective_leads: int  # After brand multiplier
    
    # Product metrics
    product_pull_score: str
    conversion_ceiling_pct: str
    expected_conversion_pct: str
    
    # Competitive position
    our_strength: str
    rival_strength: str


@router.post("/preview", response_model=DemandPreviewResponse)
async def preview_addressable_demand(
    request: DemandPreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Preview how many buyers would be interested based on current state + planned spend.
    
    This endpoint is called as the user adjusts allocation sliders on the frontend,
    showing real-time impact of their investment decisions.
    """
    # Fetch company current state
    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get prior quarter for current metrics
    prior_quarter = (
        db.query(Quarter)
        .filter(Quarter.company_id == request.company_id)
        .filter(Quarter.quarter_num == request.quarter - 1)
        .first()
    )
    
    # Build market state from current company position
    if prior_quarter:
        brand_score = Decimal(str(prior_quarter.brand_score or 0))
        innovation_score = Decimal(str(prior_quarter.innovation_score or 0))
        quality_score = Decimal(str(prior_quarter.quality_score or 0))
        satisfaction = Decimal(str(prior_quarter.satisfaction_score or 50))
        fill_rate = Decimal(str(prior_quarter.fill_rate or 1.0))
        market_share_prior = Decimal(str(prior_quarter.market_share or 0))
    else:
        # Opening quarter defaults
        brand_score = Decimal("0")
        innovation_score = Decimal("0")
        quality_score = Decimal("0")
        satisfaction = Decimal("50")
        fill_rate = Decimal("1.0")
        market_share_prior = Decimal("0")
    
    # Apply any boosts from request (for "what if" scenarios)
    brand_score += request.brand_boost
    innovation_score += request.innovation_boost
    quality_score += request.quality_boost
    
    market_state = MarketState(
        quarter=request.quarter,
        brand_score=brand_score,
        innovation_score=innovation_score,
        quality_score=quality_score,
        satisfaction_score=satisfaction,
        fill_rate=fill_rate,
        market_share_prior=market_share_prior
    )
    
    # Calculate total marketing spend
    total_marketing = (
        request.google_ads + request.meta_ads + request.social_influencer +
        request.content_seo + request.events_pr + request.email +
        request.direct_marketing + request.referral
    )
    
    # Estimate addressable demand
    addressable = estimate_addressable_demand(market_state, total_marketing)
    
    # Calculate market size and competitive position for context
    from app.engines.demand_dynamics import calculate_market_demand, calculate_rival_strength, calculate_product_pull
    
    market_demand = calculate_market_demand(request.quarter)
    rival_strength = calculate_rival_strength(request.quarter)
    product_pull = calculate_product_pull(
        brand_score, innovation_score, quality_score, satisfaction
    )
    
    # Voice index
    voice_idx = Decimal("0.55") + Decimal("0.45") * min(
        Decimal("1.0"),
        total_marketing / Decimal("18")
    )
    
    # Calculate potential share
    share_potential = (addressable / market_demand * Decimal("100")) if market_demand > 0 else Decimal("0")
    
    # Generate guidance message
    if total_marketing < Decimal("5"):
        guidance = "Marketing spend is low - consider funding demand generation to reach more buyers."
    elif product_pull < Decimal("25"):
        guidance = "Product attributes are limiting demand. Invest in R&D to improve quality and innovation."
    elif addressable < market_demand * Decimal("0.15"):
        guidance = "You're reaching less than 15% of the market. Competitors are capturing most buyers."
    else:
        guidance = f"Solid position - you could reach ~{int(addressable):,} of {int(market_demand):,} category buyers this quarter."
    
    return DemandPreviewResponse(
        addressable_demand_units=int(addressable),
        total_market_demand=int(market_demand),
        our_market_share_potential=f"{float(share_potential):.1f}%",
        competitive_position_score=f"{float(product_pull):.1f}",
        product_pull_score=f"{float(product_pull):.1f}",
        rival_total_strength=f"{float(rival_strength):.1f}",
        marketing_voice_index=f"{float(voice_idx * 100):.0f}%",
        guidance_message=guidance
    )


@router.post("/detailed", response_model=DetailedDemandResponse)
async def detailed_demand_breakdown(
    request: DemandPreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Full demand calculation with channel-by-channel lead breakdown.
    
    Use this for the main dashboard to show detailed impact of each investment.
    """
    # Fetch company state (same as preview endpoint)
    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    prior_quarter = (
        db.query(Quarter)
        .filter(Quarter.company_id == request.company_id)
        .filter(Quarter.quarter_num == request.quarter - 1)
        .first()
    )
    
    if prior_quarter:
        brand_score = Decimal(str(prior_quarter.brand_score or 0))
        innovation_score = Decimal(str(prior_quarter.innovation_score or 0))
        quality_score = Decimal(str(prior_quarter.quality_score or 0))
        satisfaction = Decimal(str(prior_quarter.satisfaction_score or 50))
        fill_rate = Decimal(str(prior_quarter.fill_rate or 1.0))
        market_share_prior = Decimal(str(prior_quarter.market_share or 0))
        customers = prior_quarter.customers_count or 4000
    else:
        brand_score = Decimal("0")
        innovation_score = Decimal("0")
        quality_score = Decimal("0")
        satisfaction = Decimal("50")
        fill_rate = Decimal("1.0")
        market_share_prior = Decimal("0")
        customers = 4000
    
    market_state = MarketState(
        quarter=request.quarter,
        brand_score=brand_score,
        innovation_score=innovation_score,
        quality_score=quality_score,
        satisfaction_score=satisfaction,
        fill_rate=fill_rate,
        market_share_prior=market_share_prior
    )
    
    investment = MarketingInvestment(
        google_ads=request.google_ads,
        meta_ads=request.meta_ads,
        social_influencer=request.social_influencer,
        content_seo=request.content_seo,
        events_pr=request.events_pr,
        email=request.email,
        direct_marketing=request.direct_marketing,
        referral=request.referral
    )
    
    # Calculate full demand
    result = calculate_full_demand(
        market_state=market_state,
        investment=investment,
        current_customers=customers,
        sales_capacity=Decimal("10000"),  # Placeholder - not used in estimate
        production_capacity=Decimal("10000")  # Placeholder
    )
    
    return DetailedDemandResponse(
        addressable_demand_units=int(result.addressable_demand_units),
        total_market_demand=int(result.total_market_demand),
        attractive_share_pct=f"{float(result.attractive_share * 100):.1f}%",
        google_leads=int(result.channel_leads.get("google", Decimal("0"))),
        meta_leads=int(result.channel_leads.get("meta", Decimal("0"))),
        social_leads=int(result.channel_leads.get("social", Decimal("0"))),
        content_leads=int(result.channel_leads.get("content", Decimal("0"))),
        events_leads=int(result.channel_leads.get("events", Decimal("0"))),
        email_leads=int(result.channel_leads.get("email", Decimal("0"))),
        direct_leads=int(result.channel_leads.get("direct", Decimal("0"))),
        total_raw_leads=int(result.total_raw_leads),
        effective_leads=int(result.effective_leads),
        product_pull_score=f"{float(result.product_pull_score):.1f}",
        conversion_ceiling_pct=f"{float(result.conversion_ceiling_pct):.1f}%",
        expected_conversion_pct=f"{float(result.expected_conversion_pct):.1f}%",
        our_strength=f"{float(result.our_strength):.1f}",
        rival_strength=f"{float(result.rival_total_strength):.1f}"
    )
