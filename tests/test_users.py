from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_participante_cannot_list_moderators(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.get(
        "/users/moderators", headers=auth_headers(token)
    )

    assert response.status_code == 403


async def test_admin_can_list_moderators(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    response = await client.get(
        "/users/moderators", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_super_admin_can_list_moderators(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.SUPER_ADMIN)

    response = await client.get(
        "/users/moderators", headers=auth_headers(token)
    )

    assert response.status_code == 200


async def test_participant_cannot_remove_user_role(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    _, target_id = make_token()

    response = await client.delete(
        f"/users/{target_id}/role",
        headers=auth_headers(token),
    )

    assert response.status_code == 403


async def test_get_my_profile_without_profile_returns_none(
    client: AsyncClient,
):
    token, _ = make_token()

    response = await client.get(
        "/users/me/profile", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json() is None


async def test_create_my_profile(client: AsyncClient):
    token, _ = make_token()

    payload = {
        "nome": "Ingrid",
        "sobrenome": "Xisto",
        "github_username": "ingriddev",
        "bio": "Desenvolvedora Python",
    }

    response = await client.put(
        "/users/me/profile",
        json=payload,
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Ingrid"
    assert response.json()["sobrenome"] == "Xisto"
    assert response.json()["github_username"] == "ingriddev"
    assert response.json()["bio"] == "Desenvolvedora Python"


async def test_get_my_profile_after_creation(client: AsyncClient):
    token, _ = make_token()

    payload = {
        "nome": "Ingrid",
        "cargo_atual": "Desenvolvedora Júnior",
    }

    create_response = await client.put(
        "/users/me/profile",
        json=payload,
        headers=auth_headers(token),
    )
    assert create_response.status_code == 200

    response = await client.get(
        "/users/me/profile",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Ingrid"
    assert response.json()["cargo_atual"] == "Desenvolvedora Júnior"


async def test_update_my_profile(client: AsyncClient):
    token, _ = make_token()

    await client.put(
        "/users/me/profile",
        json={"nome": "Ingrid"},
        headers=auth_headers(token),
    )

    response = await client.put(
        "/users/me/profile",
        json={"nome": "Ingrid Santos", "bio": "Backend Python"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Ingrid Santos"
    assert response.json()["bio"] == "Backend Python"


async def test_get_my_profile_without_authentication(client: AsyncClient):
    response = await client.get("/users/me/profile")

    assert response.status_code in (401, 403)


async def test_update_my_profile_without_authentication(client: AsyncClient):
    response = await client.put(
        "/users/me/profile",
        json={"nome": "Ingrid"},
    )

    assert response.status_code in (401, 403)


async def test_create_profile_with_invalid_gender(client: AsyncClient):
    token, _ = make_token()

    response = await client.put(
        "/users/me/profile",
        json={"genero": "Opção inválida"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


async def test_create_profile_with_underage_birth_date(client: AsyncClient):
    token, _ = make_token()
    underage_date = (date.today() - timedelta(days=365 * 17)).isoformat()

    response = await client.put(
        "/users/me/profile",
        json={"data_nascimento": underage_date},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("actor_role", "expected_status"),
    [
        (Role.SUPER_ADMIN, 200),
        (Role.ADMIN, 403),
        (Role.MODERADOR, 403),
        (Role.PARTICIPANTE, 403),
    ],
)
async def test_list_users_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    actor_role: Role,
    expected_status: int,
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, actor_role)

    response = await client.get(
        "/users",
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert isinstance(response.json(), list)


@pytest.mark.parametrize(
    ("actor_role", "expected_status"),
    [
        (Role.SUPER_ADMIN, 200),
        (Role.ADMIN, 200),
        (Role.MODERADOR, 403),
        (Role.PARTICIPANTE, 403),
    ],
)
async def test_list_moderators_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    actor_role: Role,
    expected_status: int,
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, actor_role)

    response = await client.get(
        "/users/moderators",
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert isinstance(response.json(), list)


@pytest.mark.parametrize(
    ("actor_role", "new_role", "expected_status"),
    [
        (Role.SUPER_ADMIN, Role.SUPER_ADMIN, 200),
        (Role.SUPER_ADMIN, Role.ADMIN, 200),
        (Role.SUPER_ADMIN, Role.MODERADOR, 200),
        (Role.SUPER_ADMIN, Role.PARTICIPANTE, 200),
        (Role.ADMIN, Role.MODERADOR, 200),
        (Role.ADMIN, Role.SUPER_ADMIN, 403),
        (Role.ADMIN, Role.ADMIN, 403),
        (Role.ADMIN, Role.PARTICIPANTE, 403),
        (Role.MODERADOR, Role.SUPER_ADMIN, 403),
        (Role.MODERADOR, Role.ADMIN, 403),
        (Role.MODERADOR, Role.MODERADOR, 403),
        (Role.MODERADOR, Role.PARTICIPANTE, 403),
        (Role.PARTICIPANTE, Role.SUPER_ADMIN, 403),
        (Role.PARTICIPANTE, Role.ADMIN, 403),
        (Role.PARTICIPANTE, Role.MODERADOR, 403),
        (Role.PARTICIPANTE, Role.PARTICIPANTE, 403),
    ],
)
async def test_assign_user_role_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    actor_role: Role,
    new_role: Role,
    expected_status: int,
):
    token, actor_id = make_token()
    await set_user_role(db_session, actor_id, actor_role)

    _, target_id = make_token()

    response = await client.put(
        f"/users/{target_id}/role",
        json={"role": new_role.value},
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status

    if expected_status == 200:
        assert response.json()["role"] == new_role.value


@pytest.mark.parametrize(
    "target_role",
    [Role.ADMIN, Role.SUPER_ADMIN],
)
async def test_admin_cannot_change_admin_or_super_admin_role(
    client: AsyncClient,
    db_session: AsyncSession,
    target_role: Role,
):
    token, actor_id = make_token()
    await set_user_role(db_session, actor_id, Role.ADMIN)

    _, target_id = make_token()
    await set_user_role(db_session, target_id, target_role)

    response = await client.put(
        f"/users/{target_id}/role",
        json={"role": Role.MODERADOR.value},
        headers=auth_headers(token),
    )

    assert response.status_code == 403
