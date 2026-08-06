import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Constructed via `Model.model_validate(orm_row, from_attributes=True)` -- never hand-mapped
    field by field."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class QuarterScopedBase(ORMBase):
    quarter_id: uuid.UUID
