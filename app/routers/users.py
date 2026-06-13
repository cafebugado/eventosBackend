import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.rbac.permissions import get_current_user_role, require_role
from app.rbac.roles import Role
from app.schemas.user import (
    AssignRoleRequest,
    CurrentUserRole,
    UserProfileRead,
    UserProfileUpsert,
    UserRoleRead,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/role", response_model=CurrentUserRole)
async def get_my_role(role: Role = Depends(get_current_user_role)) -> CurrentUserRole:
    return CurrentUserRole(role=role)


@router.get("", response_model=list[UserRoleRead])
async def list_users_with_roles(
    _user=Depends(require_role(Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[UserRoleRead]:
    service = RoleService(db)
    roles = await service.get_users_with_roles()
    return [UserRoleRead.model_validate(r) for r in roles]


@router.get("/moderators", response_model=list[UserRoleRead])
async def list_moderators(
    _user=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[UserRoleRead]:
    service = RoleService(db)
    roles = await service.get_users_with_roles_for_admin()
    return [UserRoleRead.model_validate(r) for r in roles]


@router.put("/{user_id}/role", response_model=UserRoleRead)
async def assign_user_role(
    user_id: uuid.UUID,
    data: AssignRoleRequest,
    current_user: CurrentUser = Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserRoleRead:
    service = RoleService(db)
    actor_role = await service.get_user_role(uuid.UUID(current_user.id))
    role = await service.assign_user_role(actor_role, user_id, data.role)
    return UserRoleRead.model_validate(role)


@router.delete("/{user_id}/role", status_code=204)
async def remove_user_role(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = RoleService(db)
    actor_role = await service.get_user_role(uuid.UUID(current_user.id))
    await service.remove_user_role(actor_role, user_id)


@router.get("/me/profile", response_model=UserProfileRead | None)
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileRead | None:
    service = RoleService(db)
    profile = await service.get_my_profile(uuid.UUID(current_user.id))
    return UserProfileRead.model_validate(profile) if profile else None


@router.put("/me/profile", response_model=UserProfileRead)
async def upsert_my_profile(
    data: UserProfileUpsert,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileRead:
    service = RoleService(db)
    profile = await service.upsert_my_profile(uuid.UUID(current_user.id), data)
    return UserProfileRead.model_validate(profile)
