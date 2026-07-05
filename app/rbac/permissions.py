import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.user_role import UserRole
from app.rbac.roles import DEFAULT_ROLE, Role

# Matriz de permissoes (espelha src/hooks/useUserRole.js)
PERMISSIONS: dict[str, set[Role]] = {
    "canCreateEvents": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR, Role.PARTICIPANTE},
    "canEditEvents": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR, Role.PARTICIPANTE},
    "canDeleteEvents": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR},
    "canPublishEvents": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR},
    "canManageTags": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR},
    "canDeleteTags": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR},
    "canManageContributors": {Role.SUPER_ADMIN, Role.ADMIN},
    "canManageUsers": {Role.SUPER_ADMIN, Role.ADMIN},
    "canUploadImages": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR, Role.PARTICIPANTE},
    "canSaveSettings": {Role.SUPER_ADMIN, Role.ADMIN, Role.MODERADOR},
}


async def get_user_role(user_id: str, db: AsyncSession) -> Role:
    result = await db.execute(
        select(UserRole.role).where(UserRole.user_id == uuid.UUID(user_id))
    )
    role = result.scalar_one_or_none()
    return role if role is not None else DEFAULT_ROLE


async def get_current_user_role(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Role:
    return await get_user_role(current_user.id, db)


def require_role(*allowed_roles: Role) -> Callable[..., Awaitable[CurrentUser]]:
    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        role = await get_user_role(current_user.id, db)
        if role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente para esta acao")
        return current_user

    return dependency


def require_permission(permission: str) -> Callable[..., Awaitable[CurrentUser]]:
    allowed_roles = PERMISSIONS.get(permission, set())

    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        role = await get_user_role(current_user.id, db)
        if role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente para esta acao")
        return current_user

    return dependency
