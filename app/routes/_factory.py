"""Builds the identical 3-endpoint router shape (submit decision, get state, list decisions)
for each workspace. The 6 workspaces' routers are byte-for-byte identical in logic --
differing only in the workspace enum value, the *State model, and the two schema types --
so this factors that once instead of hand-rolling 6 near-duplicate route files that would
each need the same guard-rail and audit-logging fix applied separately.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base, get_db
from app.models.decision import Decision, DecisionLog, DecisionStatus, Workspace
from app.models.quarter import Quarter
from app.routes.deps import get_open_quarter, get_quarter, get_quarter_modifiers
from app.schemas.decision import DecisionLogEntry, DecisionSubmissionResponse, DecisionSubmitBase, FieldImpactResponse
from app.services.decision_engine import compute_decision_impact
from app.services.evidence_engine import generate_evidence


def _state_to_dict(state: Base | None) -> dict[str, Any] | None:
    """Flattens a *State ORM row into a plain dict so decision_engine can read prerequisite
    values (e.g. FIN-002 needs cash_balance) without decision_engine touching the DB itself.

    Read-only, deliberately: submitting a decision must never write to a *State row. All
    allocations and decisions evaluate against the opening snapshot for the quarter; only
    `run_quarter()` (`services/quarter_run_service.py`) writes closing state, once, when the
    quarter is locked. Do not add a `session.add(state_model(...))`/write-back here -- see
    CLAUDE.md's "No within-quarter compounding" rule.
    """
    if state is None:
        return None
    return {column.key: getattr(state, column.key) for column in sa_inspect(state).mapper.columns}


def build_workspace_router(
    *,
    workspace: Workspace,
    state_model: type[Base],
    state_response_schema: type,
    decision_submit_schema: type[DecisionSubmitBase],
) -> APIRouter:
    router = APIRouter(
        prefix=f"/companies/{{company_id}}/quarters/{{quarter_id}}/{workspace.value}",
        tags=[workspace.value],
    )

    @router.post("/decisions", response_model=DecisionSubmissionResponse, status_code=status.HTTP_201_CREATED)
    async def submit_decision(
        company_id: uuid.UUID,
        submission: decision_submit_schema,
        quarter: Quarter = Depends(get_open_quarter),
        session: AsyncSession = Depends(get_db),
    ) -> DecisionSubmissionResponse:
        decision = Decision(
            quarter_id=quarter.id,
            workspace=workspace,
            title=submission.decision_key,
            decision_key=submission.decision_key,
            payload=submission.payload,
            status=DecisionStatus.SUBMITTED,
        )
        session.add(decision)
        await session.flush()

        modifiers = await get_quarter_modifiers(quarter.id, session)
        current_state = (
            await session.execute(select(state_model).where(state_model.quarter_id == quarter.id))
        ).scalar_one_or_none()

        # Gaps in decision_engine (TODO(source-doc-gap) items, unimplemented decision_keys,
        # missing prerequisite payload/state fields) surface as 422s here rather than
        # silently persisting a decision with no computed business impact.
        try:
            impacts = compute_decision_impact(
                workspace.value,
                submission.decision_key,
                modifiers,
                payload=submission.payload,
                state=_state_to_dict(current_state),
            )
        except (NotImplementedError, KeyError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

        session.add(
            DecisionLog(
                decision_id=decision.id,
                stage="business_impact",
                input_snapshot={
                    "decision_key": submission.decision_key,
                    "payload": submission.payload,
                    "modifiers": modifiers,
                },
                output_snapshot={"impacts": [i.__dict__ for i in impacts]},
            )
        )

        # Unlike business impact (the response contract promises a business_impact list),
        # a missing evidence-extraction rule is non-fatal here -- the Business Impact and
        # Evidence pipelines are independent (see architecture docs), and quarter_engine
        # already treats this as a recoverable "skipped", not a hard failure. Blocking an
        # otherwise-successful submission because evidence isn't wired up yet for this
        # decision_key would be wrong for the same reason quarter_engine doesn't do it.
        try:
            evidence_records = generate_evidence(decision, company_id=company_id)
            evidence_output: dict = {
                "evidence": [
                    {"key": e.evidence_key, "value": e.evidence_value, "categories": e.categories}
                    for e in evidence_records
                ]
            }
        except NotImplementedError as exc:
            evidence_records = []
            evidence_output = {"skipped": str(exc)}

        session.add_all(evidence_records)
        session.add(
            DecisionLog(
                decision_id=decision.id,
                stage="evidence",
                input_snapshot={"decision_key": submission.decision_key, "payload": submission.payload},
                output_snapshot=evidence_output,
            )
        )

        await session.commit()

        return DecisionSubmissionResponse(
            decision_id=decision.id,
            workspace=workspace,
            decision_key=submission.decision_key,
            business_impact=[
                FieldImpactResponse(field=i.field, base_value=i.base_value, actual_value=i.actual_value)
                for i in impacts
            ],
            evidence_generated=len(evidence_records),
        )

    @router.get("/state", response_model=state_response_schema)
    async def get_state(
        quarter: Quarter = Depends(get_quarter),
        session: AsyncSession = Depends(get_db),
    ):
        result = await session.execute(select(state_model).where(state_model.quarter_id == quarter.id))
        state = result.scalar_one_or_none()
        if state is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"No {workspace.value} state snapshot yet for this quarter"
            )
        return state

    @router.get("/decisions", response_model=list[DecisionLogEntry])
    async def list_decisions(
        quarter: Quarter = Depends(get_quarter),
        session: AsyncSession = Depends(get_db),
    ):
        result = await session.execute(
            select(Decision).where(Decision.quarter_id == quarter.id, Decision.workspace == workspace)
        )
        return result.scalars().all()

    return router
