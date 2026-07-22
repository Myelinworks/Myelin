from app.models.decision import Workspace
from app.models.finance import FinanceState
from app.routes._factory import build_workspace_router
from app.schemas.finance import FinanceDecisionSubmit, FinanceStateResponse

router = build_workspace_router(
    workspace=Workspace.FINANCE,
    state_model=FinanceState,
    state_response_schema=FinanceStateResponse,
    decision_submit_schema=FinanceDecisionSubmit,
)
