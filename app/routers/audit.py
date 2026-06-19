import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rbac.permissions import require_role
from app.rbac.roles import Role
from app.schemas.audit import AuditLogPage, AuditLogRead, AuditUser
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    entity: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _user=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AuditLogPage:
    service = AuditService(db)
    items, total = await service.get_audit_logs(
        user_id=user_id,
        action=action,
        entity=entity,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return AuditLogPage(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users", response_model=list[AuditUser])
async def list_audit_users(
    _user=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[AuditUser]:
    service = AuditService(db)
    users = await service.get_audit_users()
    return [AuditUser(**u) for u in users]
