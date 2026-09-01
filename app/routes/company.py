"""Company and quarter creation, plus read-through of current state.

The creation routes are the only place a Company, Quarter or Modifier row comes into existence
through the API -- before these, every test had to seed through the ORM and nothing on a
deployed instance could be exercised end to end.
"""

import uuid

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import cast, func, select
from sqlalchemy.types import Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_scenario
from app.core.db import get_db
from app.engines.run_state import Move
from app.models.company import Company
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_allocation import QuarterAllocation
from app.models.quarter_performance import QuarterPerformance
from app.models.app_user import AppUser
from app.models.simulation_quarter import SimulationQuarter
from app.routes.deps import get_current_user, get_quarter, get_quarter_modifiers
from app.schemas.company import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyListItem,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
    LeaderboardEntrySchema,
    LeaderboardResponse,
    QuarterDetailResponse,
    QuarterSummary,
    ScenarioResponse,
)
from app.schemas.errors import CREATE_ONLY_RESPONSES, READ_RESPONSES, WRITE_RESPONSES
from app.services.auth_service import CurrentUser
from app.services.authorization_service import require_owner, require_read_access
from app.services.company_service import ScenarioAssignmentError, create_company, create_quarter
from app.services.run_service import require_move

router = APIRouter(tags=["company"])

# Columns on QuarterAllocation that are not Rs-lakh spend lines: bookkeeping, the warranty
# choice (surfaced as its own integer field, not a 23rd "spend line"), and the Phase 10 crisis
# response columns (surfaced as their own `crisis` field -- a different category, only meaningful
# in the quarter a crisis actually fires, same reasoning as warranty).
_CRISIS_COLUMNS = {
    "crisis_choice", "price_match_fund", "comparison_ads", "retention_offers",
    "emergency_supply_fund", "crisis_choice_d_spend",
}
_NON_ALLOCATION_COLUMNS = {"id", "company_id", "quarter_id", "created_at", "warranty_years", *_CRISIS_COLUMNS}


async def _load_company(company_id: uuid.UUID, session: AsyncSession, user: CurrentUser) -> Company:
    """404 if the company doesn't exist, then the read-access gate (owner-or-instructor) --
    identity always checked before anything else a route does with the row."""
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")
    require_read_access(company, user)
    return company


def _company_detail(company: Company, quarters: list[Quarter]) -> CompanyDetailResponse:
    scenario = load_scenario(company.scenario_id)
    return CompanyDetailResponse(
        **CompanyResponse.model_validate(company, from_attributes=True).model_dump(),
        scenario=ScenarioResponse(
            scenario_id=scenario.scenario_id,
            display_name=scenario.display_name,
            total_quarters=scenario.total_quarters,
            crisis_quarter=scenario.crisis_quarter,
        ),
        quarters=[QuarterSummary.model_validate(q, from_attributes=True) for q in quarters],
    )


@router.post(
    "/companies",
    response_model=CompanyDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_ONLY_RESPONSES,
    summary="Start a new run",
    description="Step 1 of the lifecycle. Creates a company, assigning a scenario "
    "deterministically from the company id if none is given. The authenticated caller becomes "
    "this run's owner. No quarter exists yet -- `POST .../quarters` next.",
)
async def create_company_route(
    payload: CompanyCreate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CompanyDetailResponse:
    """Create a company on a scenario, assigning one deterministically if none is given.

    No ownership check needed -- there's nothing to own yet. The authenticated caller becomes
    the owner, which is what every later read/write on this company checks against.
    """
    try:
        company = await create_company(
            session,
            name=payload.name,
            scenario_id=payload.scenario_id,
            company_id=payload.company_id,
            owner_id=user.id,
        )
    except (ScenarioAssignmentError, FileNotFoundError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    await session.commit()
    return _company_detail(company, quarters=[])


@router.get(
    "/companies",
    response_model=CompanyListResponse,
    responses=CREATE_ONLY_RESPONSES,
    summary="List the runs this caller owns",
    description="Every run owned by the authenticated caller, newest first. Exists so a client "
    "can offer 'resume a run' without having to remember company ids itself -- ownership is "
    "already enforced server-side, but before this there was no way to *discover* which ids you "
    "owned. Strictly owner-scoped; never returns another user's runs.",
)
async def list_companies(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CompanyListResponse:
    """Owner-scoped read-through. Two queries total regardless of how many runs the caller owns
    (companies, then every quarter belonging to them joined to its performance row) -- the
    per-company rollups are folded in Python rather than issued as a query per company.
    """
    # First, get the total count of the user's runs for pagination
    total = await session.scalar(
        select(func.count()).where(Company.owner_id == user.id)
    )

    companies = (
        (
            await session.execute(
                select(Company)
                .where(Company.owner_id == user.id)
                .order_by(Company.created_at.desc(), Company.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    if not companies:
        return CompanyListResponse(total=total or 0, entries=[])

    rows = (
        await session.execute(
            select(Quarter, QuarterPerformance)
            .outerjoin(QuarterPerformance, QuarterPerformance.quarter_id == Quarter.id)
            .where(Quarter.company_id.in_([c.id for c in companies]))
            .order_by(Quarter.company_id, Quarter.number)
        )
    ).all()

    # The Nadi Wear simulation writes its own SimulationQuarter rows instead of the 22-line
    # Quarter/QuarterPerformance pair. Read those too so its rollup is populated the same way.
    sim_rows = (
        (
            await session.execute(
                select(SimulationQuarter)
                .where(SimulationQuarter.company_id.in_([c.id for c in companies]))
                .order_by(SimulationQuarter.company_id, SimulationQuarter.number)
            )
        )
        .scalars()
        .all()
    )

    by_company: dict[uuid.UUID, list[tuple[Quarter, QuarterPerformance | None]]] = {}
    for quarter, performance in rows:
        by_company.setdefault(quarter.company_id, []).append((quarter, performance))

    sim_by_company: dict[uuid.UUID, list[SimulationQuarter]] = {}
    for sq in sim_rows:
        sim_by_company.setdefault(sq.company_id, []).append(sq)

    entries = []
    for company in companies:
        quarters = by_company.get(company.id, [])
        sim_quarters = sim_by_company.get(company.id, [])
        scenario = load_scenario(company.scenario_id)
        if sim_quarters:
            latest_sim = sim_quarters[-1]
            sim_closed = [sq for sq in sim_quarters if sq.ceo_score is not None]
            latest_scored_sim = sim_closed[-1] if sim_closed else None
            entries.append(
                CompanyListItem(
                    id=company.id,
                    seq=company.seq,
                    name=company.name,
                    created_at=company.created_at,
                    run_status=company.run_status,
                    scenario_id=company.scenario_id,
                    total_quarters=scenario.total_quarters,
                    crisis_quarter=scenario.crisis_quarter,
                    current_quarter_number=latest_sim.number,
                    current_quarter_status="closed",
                    quarters_locked=len(sim_quarters),
                    latest_ceo_score=Decimal(latest_scored_sim.ceo_score) if latest_scored_sim else None,
                    latest_band=latest_scored_sim.band if latest_scored_sim else None,
                )
            )
            continue
        closed = [(q, p) for q, p in quarters if q.status == QuarterStatus.CLOSED]
        latest_scored = next(
            (p for _, p in reversed(closed) if p is not None and p.ceo_score is not None), None
        )
        current = quarters[-1][0] if quarters else None
        entries.append(
            CompanyListItem(
                id=company.id,
                seq=company.seq,
                name=company.name,
                created_at=company.created_at,
                run_status=company.run_status,
                scenario_id=company.scenario_id,
                total_quarters=scenario.total_quarters,
                crisis_quarter=scenario.crisis_quarter,
                current_quarter_number=current.number if current else None,
                current_quarter_status=current.status if current else None,
                quarters_locked=len(closed),
                latest_ceo_score=latest_scored.ceo_score if latest_scored else None,
                latest_band=latest_scored.score_band if latest_scored else None,
            )
        )
    return CompanyListResponse(total=total, entries=entries)


@router.get(
    "/companies/{company_id}",
    response_model=CompanyDetailResponse,
    responses=READ_RESPONSES,
    summary="Read a company's current state",
    description="Read-through of current state, including every quarter opened so far. Legal to "
    "call at any point in the lifecycle, including after the run has ended.",
)
async def get_company(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CompanyDetailResponse:
    """Read-through of current state. Computes nothing."""
    company = await _load_company(company_id, session, user)
    quarters = (
        (await session.execute(select(Quarter).where(Quarter.company_id == company_id).order_by(Quarter.number)))
        .scalars()
        .all()
    )

    return _company_detail(company, list(quarters))


@router.patch(
    "/companies/{company_id}",
    response_model=CompanyDetailResponse,
    responses=WRITE_RESPONSES,
    summary="Rename a company",
    description="Updates the display name of an existing run. Only the owner may rename.",
)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CompanyDetailResponse:
    """Rename the company. Owner-only."""
    company = await _load_company(company_id, session, user)
    require_owner(company, user)
    company.name = payload.name.strip()[:255] or company.name
    await session.commit()
    await session.refresh(company)
    quarters = (
        (await session.execute(select(Quarter).where(Quarter.company_id == company_id).order_by(Quarter.number)))
        .scalars()
        .all()
    )
    return _company_detail(company, list(quarters))


@router.post(
    "/companies/{company_id}/quarters",
    response_model=QuarterDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses=WRITE_RESPONSES,
    summary="Open the next quarter",
    description="Opens quarter N+1, carrying forward quarter N's closing state (cash, customers, "
    "Brand/Quality/Innovation Scores, etc.). Legal only when no quarter is currently open and the "
    "prior quarter (if any) is locked -- check `GET .../run`'s `legal_moves` first; an "
    "out-of-order call returns `illegal_move` (409).",
)
async def create_quarter_route(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> QuarterDetailResponse:
    """Open the company's next quarter, carrying forward the prior quarter's closing state.

    Phase 12: consults `require_move(OPEN_NEXT_QUARTER)` first, so "past the scenario's last
    quarter", "the run is terminal", and "the prior quarter isn't locked yet" all raise the same
    `IllegalMoveError` (409, one consistent JSON body) every other write route now raises for its
    own ordering violations -- this route no longer holds its own, differently-shaped 422 copy of
    the same three rules. `create_quarter` keeps its own equivalent checks as a safety net for
    non-HTTP callers (e.g. tests that call it directly); the `except ValueError` below stays for
    the same reason.

    Phase 13: this is a write, so it needs the owner-only gate on top of `_load_company`'s
    read-access check -- 404 (exists) -> 403 (yours) -> 409 (legal right now).
    """
    company = await _load_company(company_id, session, user)
    require_owner(company, user)
    await require_move(session, company, Move.OPEN_NEXT_QUARTER)
    try:
        quarter = await create_quarter(session, company)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    await session.commit()
    return await _quarter_detail(quarter, session)


@router.get(
    "/companies/{company_id}/quarters/{quarter_id}",
    response_model=QuarterDetailResponse,
    responses=READ_RESPONSES,
    summary="Read a quarter's current submitted state",
    description="The 22 spend lines submitted so far (and crisis fields, if this is the crisis "
    "quarter) -- not a report; there is no scored outcome until the quarter locks.",
)
async def get_quarter_detail(
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterDetailResponse:
    """Read-through of current state. Computes nothing."""
    return await _quarter_detail(quarter, session)


async def _quarter_detail(quarter: Quarter, session: AsyncSession) -> QuarterDetailResponse:
    allocation = (
        await session.execute(select(QuarterAllocation).where(QuarterAllocation.quarter_id == quarter.id))
    ).scalar_one_or_none()

    return QuarterDetailResponse(
        id=quarter.id,
        company_id=quarter.company_id,
        number=quarter.number,
        status=quarter.status,
        cash_balance=quarter.cash_balance,
        revenue=quarter.revenue,
        created_at=quarter.created_at,
        closed_at=quarter.closed_at,
        modifiers=await get_quarter_modifiers(quarter.id, session),
        allocations=None
        if allocation is None
        else {
            column.key: getattr(allocation, column.key)
            for column in allocation.__table__.columns
            if column.key not in _NON_ALLOCATION_COLUMNS
        },
        warranty_years=None if allocation is None else allocation.warranty_years,
        crisis=None
        if allocation is None
        else {column: getattr(allocation, column) for column in _CRISIS_COLUMNS},
    )



@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    responses=READ_RESPONSES,
    summary="Cross-user simulation leaderboard",
    description=(
        "Returns the top-3 users ranked by their best CEO score across all their runs in the "
        "given scenario, plus the requesting user's own entry.  All figures (composite score, "
        "valuation, net profit) come from the single best-scoring quarter of each user's best "
        "run.  Only SimulationQuarter rows are considered (Nadi Wear / startup-survival flow)."
    ),
)
async def get_leaderboard(
    scenario_id: str = Query(default="nadi_wear_standard", description="Scenario to rank users within"),
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> LeaderboardResponse:
    from sqlalchemy import and_

    # ── Step 1: for every (user, company) pair find the highest ceo_score quarter ──
    # We use a correlated subquery approach that works on SQLAlchemy 2.x async:
    #
    #   best_sq  – per-user MAX(cast(ceo_score, numeric)) across all companies+quarters
    #              in this scenario.
    #   detail_sq – join back to pick one representative quarter row per user (the one
    #              whose cast score equals the user's max).  DISTINCT ON user_id keeps
    #              one row when two quarters are tied.
    #
    # result['valuation'] and result['net_profit'] are JSONB path reads; cast to Numeric
    # so they arrive as Decimal rather than a JSON string.

    best_sq = (
        select(
            Company.owner_id.label("user_id"),
            func.max(cast(SimulationQuarter.ceo_score, Numeric)).label("best_score"),
        )
        .join(SimulationQuarter, SimulationQuarter.company_id == Company.id)
        .where(
            and_(
                Company.scenario_id == scenario_id,
                Company.owner_id.isnot(None),
                SimulationQuarter.ceo_score.isnot(None),
            )
        )
        .group_by(Company.owner_id)
        .subquery("best_sq")
    )

    # Pick the earliest (by SimulationQuarter.id) quarter that matches the user's best
    # score, joining through the company that owns it.  DISTINCT ON is PostgreSQL-specific
    # but this project already requires PostgreSQL.
    detail_q = (
        select(
            best_sq.c.user_id,
            best_sq.c.best_score,
            AppUser.first_name,
            AppUser.email,
            Company.name.label("company_name"),
            SimulationQuarter.band,
            SimulationQuarter.score["final"].astext.cast(Numeric).label("composite_score"),
            SimulationQuarter.result["valuation"].astext.cast(Numeric).label("valuation_inr"),
            SimulationQuarter.result["net_profit"].astext.cast(Numeric).label("net_profit_inr"),
        )
        .select_from(best_sq)
        .join(AppUser, AppUser.id == best_sq.c.user_id)
        .join(
            Company,
            and_(
                Company.owner_id == best_sq.c.user_id,
                Company.scenario_id == scenario_id,
            ),
        )
        .join(
            SimulationQuarter,
            and_(
                SimulationQuarter.company_id == Company.id,
                cast(SimulationQuarter.ceo_score, Numeric) == best_sq.c.best_score,
            ),
        )
        .distinct(best_sq.c.user_id)           # one row per user
        .order_by(best_sq.c.user_id, best_sq.c.best_score.desc())
    )

    rows = (await session.execute(detail_q)).all()

    if not rows:
        return LeaderboardResponse(
            scenario_id=scenario_id,
            total_entries=0,
            top_entries=[],
            current_user_entry=None,
        )

    # Sort all rows by best_score desc, valuation_inr desc (tiebreaker) in Python so we
    # can assign contiguous ranks and handle ties identically to what the client sees.
    def _sort_key(r):
        score = float(r.best_score) if r.best_score is not None else 0.0
        val   = float(r.valuation_inr) if r.valuation_inr is not None else 0.0
        return (-score, -val)

    sorted_rows = sorted(rows, key=_sort_key)

    entries: list[LeaderboardEntrySchema] = []
    current_user_entry: LeaderboardEntrySchema | None = None

    for rank, row in enumerate(sorted_rows, start=1):
        display_name = (row.first_name or "").strip() or row.email.split("@")[0]
        is_me = row.user_id == user.id

        # composite_score may be None when the JSONB key is absent (very old rows written
        # before the score column existed); fall back to the typed ceo_score column.
        composite = row.composite_score if row.composite_score is not None else row.best_score

        entry = LeaderboardEntrySchema(
            rank=rank,
            user_id=row.user_id,
            user_name=display_name,
            company_name=row.company_name,
            ceo_score=row.best_score,
            composite_score=composite,
            band=row.band,
            valuation_inr=row.valuation_inr,
            net_profit_inr=row.net_profit_inr,
            is_current_user=is_me,
        )
        entries.append(entry)
        if is_me:
            current_user_entry = entry

    return LeaderboardResponse(
        scenario_id=scenario_id,
        total_entries=len(entries),
        top_entries=entries[:3],
        current_user_entry=current_user_entry,
    )
