import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.rbac.roles import Role
from app.services.role_service import RoleService

pytestmark = pytest.mark.asyncio


async def test_super_admin_can_assign_any_role(db_session: AsyncSession):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    for role in Role:
        result = await service.assign_user_role(
            Role.SUPER_ADMIN, target_id, role
        )
        assert result.role == role


async def test_admin_can_assign_moderador(db_session: AsyncSession):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    result = await service.assign_user_role(
        Role.ADMIN, target_id, Role.MODERADOR
    )

    assert result.role == Role.MODERADOR


@pytest.mark.parametrize(
    "target_role",
    [Role.ADMIN, Role.SUPER_ADMIN],
)
async def test_admin_cannot_assign_restricted_role(
    db_session: AsyncSession, target_role: Role
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    with pytest.raises(ForbiddenError):
        await service.assign_user_role(
            Role.ADMIN, target_id, target_role
        )


@pytest.mark.parametrize(
    "actor_role",
    [Role.MODERADOR, Role.PARTICIPANTE],
)
async def test_non_admin_cannot_assign_role(
    db_session: AsyncSession, actor_role: Role
):
    service = RoleService(db_session)

    with pytest.raises(ForbiddenError):
        await service.assign_user_role(
            actor_role, uuid.uuid4(), Role.MODERADOR
        )


async def test_admin_cannot_change_existing_admin_role(
        db_session: AsyncSession,
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    await service.repo.upsert_role(target_id, Role.ADMIN)

    with pytest.raises(ForbiddenError):
        await service.assign_user_role(
            Role.ADMIN, target_id, Role.MODERADOR
        )


async def test_admin_cannot_change_existing_super_admin_role(
    db_session: AsyncSession,
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    await service.repo.upsert_role(target_id, Role.SUPER_ADMIN)

    with pytest.raises(ForbiddenError):
        await service.assign_user_role(
            Role.ADMIN, target_id, Role.MODERADOR
        )


@pytest.mark.parametrize("target_role", list(Role))
async def test_super_admin_can_remove_any_role(
    db_session: AsyncSession, target_role: Role
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    await service.repo.upsert_role(target_id, target_role)
    await service.remove_user_role(Role.SUPER_ADMIN, target_id)

    assert await service.get_user_role(target_id) == Role.PARTICIPANTE


@pytest.mark.parametrize(
    "target_role",
    [Role.MODERADOR, Role.PARTICIPANTE],
)
async def test_admin_can_remove_allowed_roles(
    db_session: AsyncSession, target_role: Role
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    await service.repo.upsert_role(target_id, target_role)
    await service.remove_user_role(Role.ADMIN, target_id)

    assert await service.get_user_role(target_id) == Role.PARTICIPANTE


@pytest.mark.parametrize(
    "target_role",
    [Role.ADMIN, Role.SUPER_ADMIN],
)
async def test_admin_cannot_remove_restricted_roles(
    db_session: AsyncSession, target_role: Role
):
    service = RoleService(db_session)
    target_id = uuid.uuid4()

    await service.repo.upsert_role(target_id, target_role)

    with pytest.raises(ForbiddenError):
        await service.remove_user_role(Role.ADMIN, target_id)


async def test_admin_can_remove_role_that_does_not_exist(
        db_session: AsyncSession,
):
    service = RoleService(db_session)

    await service.remove_user_role(Role.ADMIN, uuid.uuid4())


@pytest.mark.parametrize(
    "actor_role",
    [Role.MODERADOR, Role.PARTICIPANTE],
)
async def test_non_admin_cannot_remove_role(
    db_session: AsyncSession, actor_role: Role
):
    service = RoleService(db_session)

    with pytest.raises(ForbiddenError):
        await service.remove_user_role(actor_role, uuid.uuid4())
