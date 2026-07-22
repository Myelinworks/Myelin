from app.models.decision import Workspace
from app.models.product import ProductState
from app.routes._factory import build_workspace_router
from app.schemas.product import ProductDecisionSubmit, ProductStateResponse

router = build_workspace_router(
    workspace=Workspace.PRODUCT,
    state_model=ProductState,
    state_response_schema=ProductStateResponse,
    decision_submit_schema=ProductDecisionSubmit,
)
