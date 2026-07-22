from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class ProductDecisionSubmit(DecisionSubmitBase):
    workspace = Workspace.PRODUCT


class ProductStateResponse(QuarterScopedBase):
    features_shipped: int
    nps_score: float
    tech_debt_index: float
