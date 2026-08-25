"""The Nadi Wear four-quarter scenario.

A parallel surface to the 22-line flow, not a replacement: same company, same ownership gates,
different engine. Nothing here touches the routes in `allocations.py`/`quarter.py`, and a
company can be driven by either without the other noticing.

The shape of a quarter here is deliberately two calls rather than eight:

    POST .../simulation/preview   -- run the plan, see the pressure, persist nothing
    POST .../simulation/lock      -- commit it, score it, carry the state forward

`preview` is what lets the client show a live dashboard without ever leaking the revenue
before the CEO commits: it runs the same engine that will grade them and returns the whole
chain, but the run is untouched until `lock`.
"""

import uuid

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.company import Company
from app.routes.deps import get_current_user
from app.schemas.errors import READ_RESPONSES_WITH_PLAIN_CONFLICT, WRITE_RESPONSES
from app.schemas.quarter import SimulationReportPdfResponse
from app.services.auth_service import CurrentUser
from app.services.authorization_service import require_owner, require_read_access
from app.services.simulation_service import (
    SimulationError,
    endgame_preview,
    lock,
    preview,
    run_state,
    submit_endgame,
)
from app.services.storage_service import (
    REPORT_BUCKET,
    SupabaseStorageClient,
    SupabaseStorageError,
    get_supabase_storage_client,
)

router = APIRouter(prefix="/companies/{company_id}/simulation", tags=["simulation"])

SIMULATION_REPORT_BUCKET = "simulation-reports"
_SIMULATION_PDF_SIGNED_URL_TTL = 3600


async def _readable(company_id: uuid.UUID, session: AsyncSession, user: CurrentUser) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")
    require_read_access(company, user)
    return company


async def _writable(company_id: uuid.UUID, session: AsyncSession, user: CurrentUser) -> Company:
    """Identity first, then ownership -- never the reverse, matching `deps.get_quarter_for_write`."""
    company = await _readable(company_id, session, user)
    require_owner(company, user)
    return company


def _illegal(exc: SimulationError) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        {"error": "illegal_move", "reason": exc.reason, "allowed_moves": list(exc.allowed)},
    )


@router.get(
    "/run",
    responses=READ_RESPONSES_WITH_PLAIN_CONFLICT,
    summary="Read the whole Nadi Wear run",
    description="Opening state for the quarter in progress, every locked quarter's result and "
    "score, the legal moves right now, and the crisis briefing once the crisis quarter is "
    "open. This is the payload the entire UI renders from, at every lifecycle point.",
)
async def get_run(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await run_state(session, await _readable(company_id, session, user))


@router.post(
    "/preview",
    responses=WRITE_RESPONSES,
    summary="Run a draft plan without committing it",
    description="Runs the quarter through the real engine and returns the whole chain -- "
    "readiness, the binding gate, the directors' evidence, the budget -- while persisting "
    "nothing. Deliberately the same engine that grades the quarter, so what the CEO is shown "
    "before committing and what happens after cannot disagree.",
)
async def post_preview(
    company_id: uuid.UUID,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    company = await _writable(company_id, session, user)
    try:
        return await preview(session, company, payload)
    except SimulationError as exc:
        raise _illegal(exc) from exc


@router.post(
    "/lock",
    responses=WRITE_RESPONSES,
    summary="Commit and score the quarter",
    description="Runs the quarter, scores it against the seven-trait rubric, persists the "
    "decisions and the result, and carries the state forward. In Q4 the signed term sheet is "
    "settled against the quarter that actually happened.",
)
async def post_lock(
    company_id: uuid.UUID,
    payload: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    company = await _writable(company_id, session, user)
    try:
        result = await lock(session, company, payload)
    except SimulationError as exc:
        raise _illegal(exc) from exc
    await session.commit()
    return result


@router.get(
    "/endgame",
    responses=READ_RESPONSES_WITH_PLAIN_CONFLICT,
    summary="Read the Q4 term sheet",
    description="The tier the first three quarters earned, the three-path menu it unlocks, and "
    "the continuation value the acquisition offer should be measured against. 409s until three "
    "quarters have locked.",
)
async def get_endgame(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    company = await _readable(company_id, session, user)
    try:
        return await endgame_preview(session, company)
    except SimulationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.reason) from exc


@router.post(
    "/endgame",
    responses=WRITE_RESPONSES,
    summary="Sign one of the three term sheets",
    description="Legal only between Q3 closing and Q4 locking, and upserted -- calling it again "
    "changes your mind. The outcome is scored at Q4's lock, not here.",
)
async def post_endgame(
    company_id: uuid.UUID,
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    company = await _writable(company_id, session, user)
    try:
        result = await submit_endgame(
            session, company,
            path=str(payload.get("path", "")),
            term_sheet_name=str(payload.get("term_sheet_name", "")),
            reasoning=payload.get("reasoning"),
        )
    except SimulationError as exc:
        raise _illegal(exc) from exc
    await session.commit()
    return result


def _simulation_report_path(user_id: uuid.UUID, company_id: uuid.UUID) -> str:
    return f"{user_id}/{company_id}/final.pdf"


@router.post(
    "/report/pdf",
    response_model=SimulationReportPdfResponse,
    summary="Store the simulation final report PDF",
    description="The frontend renders the PDF client-side from the scoring and history data, "
    "then hands the finished bytes here. Stored in Supabase Storage's private "
    "`simulation-reports` bucket under a user-scoped path.",
)
async def store_simulation_report_pdf(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    storage: SupabaseStorageClient = Depends(get_supabase_storage_client),
) -> SimulationReportPdfResponse:
    data = await file.read()
    path = _simulation_report_path(user.id, company_id)
    try:
        await storage.upload(
            SIMULATION_REPORT_BUCKET, path, data, content_type="application/pdf"
        )
        signed_url = await storage.create_signed_url(
            SIMULATION_REPORT_BUCKET, path, expires_in=_SIMULATION_PDF_SIGNED_URL_TTL
        )
    except SupabaseStorageError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Supabase Storage rejected the upload: {exc.message}",
        ) from exc

    return SimulationReportPdfResponse(
        bucket=SIMULATION_REPORT_BUCKET,
        path=path,
        signed_url=signed_url,
        expires_in=_SIMULATION_PDF_SIGNED_URL_TTL,
    )


@router.get(
    "/report/pdf",
    response_model=SimulationReportPdfResponse,
    summary="Re-sign a previously stored simulation report PDF",
    description="404s if the simulation PDF has never been generated. Signed URLs expire, "
    "so this always mints a fresh one.",
)
async def get_simulation_report_pdf(
    company_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    storage: SupabaseStorageClient = Depends(get_supabase_storage_client),
) -> SimulationReportPdfResponse:
    path = _simulation_report_path(user.id, company_id)
    try:
        signed_url = await storage.create_signed_url(
            SIMULATION_REPORT_BUCKET, path, expires_in=_SIMULATION_PDF_SIGNED_URL_TTL
        )
    except SupabaseStorageError as exc:
        if exc.status_code == 404:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "No simulation report PDF has been generated yet",
            ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Supabase Storage rejected the request: {exc.message}",
        ) from exc

    return SimulationReportPdfResponse(
        bucket=SIMULATION_REPORT_BUCKET,
        path=path,
        signed_url=signed_url,
        expires_in=_SIMULATION_PDF_SIGNED_URL_TTL,
    )
