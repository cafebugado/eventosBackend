import uuid

from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile
from app.models.user_role import UserRole
from app.rbac.roles import Role


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role(self, user_id: uuid.UUID) -> UserRole | None:
        result = await self.db.execute(select(UserRole).where(UserRole.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_roles(self) -> list[tuple[UserRole, UserProfile | None]]:
        result = await self.db.execute(
            select(UserRole, UserProfile).outerjoin(
                UserProfile, UserRole.user_id == UserProfile.user_id
            )
        )
        return list(result.all())

    async def list_roles_by(self, roles: list[Role]) -> list[tuple[UserRole, UserProfile | None]]:
        result = await self.db.execute(
            select(UserRole, UserProfile)
            .outerjoin(UserProfile, UserRole.user_id == UserProfile.user_id)
            .where(UserRole.role.in_(roles))
        )
        return list(result.all())

    async def get_emails(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
        if not user_ids:
            return {}
        query = text("SELECT id, email FROM auth.users WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        result = await self.db.execute(query, {"ids": user_ids})
        return {row.id: row.email for row in result.all()}

    async def upsert_role(self, user_id: uuid.UUID, role: Role) -> UserRole:
        existing = await self.get_role(user_id)
        if existing:
            existing.role = role
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        new_role = UserRole(user_id=user_id, role=role)
        self.db.add(new_role)
        await self.db.commit()
        await self.db.refresh(new_role)
        return new_role

    async def remove_role(self, user_id: uuid.UUID) -> bool:
        existing = await self.get_role(user_id)
        if existing is None:
            return False
        await self.db.delete(existing)
        await self.db.commit()
        return True

    async def get_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: uuid.UUID, data: dict) -> UserProfile:
        existing = await self.get_profile(user_id)
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        profile = UserProfile(user_id=user_id, **data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
