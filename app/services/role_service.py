import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.models.user_profile import UserProfile
from app.models.user_role import UserRole
from app.rbac.roles import DEFAULT_ROLE, Role
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileUpsert


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def get_user_role(self, user_id: uuid.UUID) -> Role:
        role = await self.repo.get_role(user_id)
        return role.role if role else DEFAULT_ROLE

    async def get_users_with_roles(self) -> list[dict]:
        rows = await self.repo.list_roles()
        return await self._merge_with_email(rows)

    async def get_users_with_roles_for_admin(self) -> list[dict]:
        """Lista usuarios com papel 'moderador' (admins gerenciam apenas moderadores)."""
        rows = await self.repo.list_roles_by([Role.MODERADOR])
        return await self._merge_with_email(rows)

    async def _merge_with_email(
        self, rows: list[tuple[UserRole, UserProfile | None]]
    ) -> list[dict]:
        emails = await self.repo.get_emails([role.user_id for role, _ in rows])
        return [
            {
                "user_id": role.user_id,
                "role": role.role,
                "created_at": role.created_at,
                "updated_at": role.updated_at,
                "nome": profile.nome if profile else None,
                "sobrenome": profile.sobrenome if profile else None,
                "avatar_url": profile.avatar_url if profile else None,
                "email": emails.get(role.user_id),
            }
            for role, profile in rows
        ]

    async def assign_user_role(
        self, actor_role: Role, target_user_id: uuid.UUID, new_role: Role
    ) -> UserRole:
        if actor_role == Role.SUPER_ADMIN:
            return await self.repo.upsert_role(target_user_id, new_role)

        if actor_role == Role.ADMIN:
            if new_role != Role.MODERADOR:
                raise ForbiddenError("Admins so podem atribuir o papel 'moderador'")

            target = await self.repo.get_role(target_user_id)
            if target is not None and target.role in (Role.SUPER_ADMIN, Role.ADMIN):
                raise ForbiddenError("Admins nao podem alterar papeis de admin/super_admin")

            return await self.repo.upsert_role(target_user_id, new_role)

        raise ForbiddenError("Permissao insuficiente para gerenciar papeis")

    async def remove_user_role(self, actor_role: Role, target_user_id: uuid.UUID) -> None:
        if actor_role == Role.SUPER_ADMIN:
            await self.repo.remove_role(target_user_id)
            return

        if actor_role == Role.ADMIN:
            target = await self.repo.get_role(target_user_id)
            if target is None:
                return
            if target.role in (Role.SUPER_ADMIN, Role.ADMIN):
                raise ForbiddenError("Admins nao podem remover papeis de admin/super_admin")
            await self.repo.remove_role(target_user_id)
            return

        raise ForbiddenError("Permissao insuficiente para gerenciar papeis")

    async def get_my_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        return await self.repo.get_profile(user_id)

    async def upsert_my_profile(self, user_id: uuid.UUID, data: UserProfileUpsert) -> UserProfile:
        return await self.repo.upsert_profile(user_id, data.model_dump(exclude_unset=True))
