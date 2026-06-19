import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user_profile import UserProfile


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_logs(
        self,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)

        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        if entity is not None:
            stmt = stmt.where(AuditLog.entity == entity)
            count_stmt = count_stmt.where(AuditLog.entity == entity)
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
            count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= date_to)
            count_stmt = count_stmt.where(AuditLog.created_at <= date_to)

        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_distinct_users(self) -> list[tuple[uuid.UUID, UserProfile | None]]:
        result = await self.db.execute(
            select(AuditLog.user_id, UserProfile)
            .distinct(AuditLog.user_id)
            .outerjoin(UserProfile, AuditLog.user_id == UserProfile.user_id)
            .where(AuditLog.user_id.is_not(None))
            .order_by(AuditLog.user_id)
        )
        return [(row[0], row[1]) for row in result.all()]
