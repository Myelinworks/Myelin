import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.quarter import Quarter
from app.routes.deps import get_open_quarter, get_quarter
from app.schemas.endgame import EndgameDecisionResponse, EndgameDecisionSubmit, EndgamePreviewResponse
from app.services.endgame_service import (
    EndgameNotReadyError,
    NotEndgameQuarterError,
    get_endgame_preview,
    submit_endgame_decision,
)

router = APIRouter(prefix="/companies/{company_id}/quarters/{quarter_id}/endgame", tags=["endgame"])


@router.get("", response_model=EndgamePreviewResponse)
async def get_endgame(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> EndgamePreviewResponse:
    """The Q4 endgame preview (`docs/16` sections 1-3): this company's Momentum tier, the term-sheet
    menu it unlocked, and Path A/B's figures -- all read-through, nothing computed beyond what
    `engines/endgame.py` derives from Q1-Q3's already-locked results. 409s if Q3 hasn't locked yet
    (matching `get_quarter_report`'s convention), 404s if this quarter isn't the scenario's last one.
    """
    try:
        preview = await get_endgame_preview(session, quarter.id)
    except EndgameNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except NotEndgameQuarterError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return EndgamePreviewResponse.model_validate(preview)


@router.post("", response_model=EndgameDecisionResponse)
async def post_endgame(
    company_id: uuid.UUID,
    submission: EndgameDecisionSubmit,
    quarter: Quarter = Depends(get_open_quarter),
    session: AsyncSession = Depends(get_db),
) -> EndgameDecisionResponse:
    """Records this company's Q4 strategic decision -- one row per company, upserted until Q4
    locks. The outcome (covenant hit/missed, correct/incorrect acceptance) is scored later, at Q4's
    own lock, not here; `get_open_quarter` 409s once that lock has happened.
    """
    decision = await submit_endgame_decision(
        session, quarter, submission.path, submission.term_sheet_name, submission.reasoning
    )
    return EndgameDecisionResponse.model_validate(decision)
