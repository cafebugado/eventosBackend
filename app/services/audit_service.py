import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuditRepository(db)

    async def get_audit_logs(
        self,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        return await self.repo.list_logs(
            user_id=user_id,
            action=action,
            entity=entity,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    async def get_audit_users(self) -> list[dict]:
        rows = await self.repo.list_distinct_users()
        user_repo = UserRepository(self.db)
        emails = await user_repo.get_emails([uid for uid, _ in rows])
        return [
            {
                "user_id": uid,
                "nome": profile.nome if profile else None,
                "sobrenome": profile.sobrenome if profile else None,
                "email": emails.get(uid),
            }
            for uid, profile in rows
        ]
