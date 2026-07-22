from app.models.decision import Workspace
from app.models.marketing import MarketingState
from app.routes._factory import build_workspace_router
from app.schemas.marketing import MarketingDecisionSubmit, MarketingStateResponse

router = build_workspace_router(
    workspace=Workspace.MARKETING,
    state_model=MarketingState,
    state_response_schema=MarketingStateResponse,
    decision_submit_schema=MarketingDecisionSubmit,
)
