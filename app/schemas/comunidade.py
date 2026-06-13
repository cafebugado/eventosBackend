import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ComunidadeBase(BaseModel):
    nome: str


class ComunidadeCreate(ComunidadeBase):
    pass


class ComunidadeUpdate(BaseModel):
    nome: str | None = None


class ComunidadeRead(ComunidadeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
