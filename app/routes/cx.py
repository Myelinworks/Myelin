from app.models.decision import Workspace
from app.models.cx import CXState
from app.routes._factory import build_workspace_router
from app.schemas.cx import CXDecisionSubmit, CXStateResponse

router = build_workspace_router(
    workspace=Workspace.CX,
    state_model=CXState,
    state_response_schema=CXStateResponse,
    decision_submit_schema=CXDecisionSubmit,
)
