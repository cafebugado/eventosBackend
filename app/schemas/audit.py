import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

AuditAction = Literal["INSERT", "UPDATE", "DELETE"]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: AuditAction
    entity: str
    entity_id: str | None = None
    changes: dict[str, Any] | None = None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int


class AuditUser(BaseModel):
    user_id: uuid.UUID
    email: str | None = None
