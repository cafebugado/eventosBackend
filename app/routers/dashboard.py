import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.rbac.permissions import get_current_user_role
from app.rbac.roles import Role
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: CurrentUser = Depends(get_current_user),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    service = DashboardService(db)
    return await service.get_summary(user_id=uuid.UUID(current_user.id), role=current_role)
