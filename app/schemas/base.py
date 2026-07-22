import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class QuarterScopedBase(ORMBase):
    quarter_id: uuid.UUID
