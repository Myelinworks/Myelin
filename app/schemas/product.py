from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class ProductDecisionSubmit(DecisionSubmitBase):
    """Legacy per-decision submission for the Product workspace -- see `DecisionSubmitBase`."""

    workspace = Workspace.PRODUCT


class ProductStateResponse(QuarterScopedBase):
    """`GET .../product/state` -- this workspace's own denormalised snapshot."""

    features_shipped: int
    nps_score: float
    tech_debt_index: float
