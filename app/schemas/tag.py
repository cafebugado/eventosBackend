import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    nome: str
    cor: str = "#2563eb"


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    nome: str | None = None
    cor: str | None = None


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SetEventTagsRequest(BaseModel):
    tag_ids: list[uuid.UUID]
