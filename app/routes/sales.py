from app.models.decision import Workspace
from app.models.sales import SalesState
from app.routes._factory import build_workspace_router
from app.schemas.sales import SalesDecisionSubmit, SalesStateResponse

router = build_workspace_router(
    workspace=Workspace.SALES,
    state_model=SalesState,
    state_response_schema=SalesStateResponse,
    decision_submit_schema=SalesDecisionSubmit,
)
