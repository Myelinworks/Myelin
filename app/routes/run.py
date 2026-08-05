"""Phase 12: `GET /companies/{company_id}/run` -- the single rich state read.

Read-only, pure reads of already-persisted data plus already-pure engine functions
(`legal_moves`, `binding_constraints`, `build_endgame_preview`) -- computes no engine number of
its own. Exists so a frontend never has to combine `GET /companies/{id}`, `GET /quarters/{id}`,
`GET /quarters/{id}/report`, and `GET /quarters/{id}/endgame` itself just to answer "where am I,
and what can I legally do next" -- one call answers all of that.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.company import Company
from app.schemas.run import RunStateResponse
from app.services.run_service import get_run_state

router = APIRouter(prefix="/companies/{company_id}", tags=["run"])


@router.get("/run", response_model=RunStateResponse)
async def get_run(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> RunStateResponse:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")

    state = await get_run_state(session, company)
    return RunStateResponse.model_validate(state)
