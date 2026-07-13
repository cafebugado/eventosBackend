import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_default_role_is_participante(client: AsyncClient):
    token, _ = make_token()
    response = await client.get("/users/me/role", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["role"] == "participante"


async def test_moderador_cannot_manage_contributors(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    payload = {
        "github_username": "octocat",
        "nome": "Octocat",
        "avatar_url": "https://example.com/avatar.png",
        "github_url": "https://github.com/octocat",
    }
    response = await client.post("/contributors", json=payload, headers=auth_headers(token))
    assert response.status_code == 403


async def test_admin_can_manage_contributors(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    payload = {
        "github_username": "octocat",
        "nome": "Octocat",
        "avatar_url": "https://example.com/avatar.png",
        "github_url": "https://github.com/octocat",
    }
    response = await client.post("/contributors", json=payload, headers=auth_headers(token))
    assert response.status_code == 201


async def test_only_super_admin_lists_all_users(client: AsyncClient, db_session: AsyncSession):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    response = await client.get("/users", headers=auth_headers(admin_token))
    assert response.status_code == 403

    super_token, super_id = make_token()
    await set_user_role(db_session, super_id, Role.SUPER_ADMIN)

    response = await client.get("/users", headers=auth_headers(super_token))
    assert response.status_code == 200


async def test_admin_cannot_assign_admin_role(client: AsyncClient, db_session: AsyncSession):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    target_token, target_id = make_token()

    response = await client.put(
        f"/users/{target_id}/role",
        json={"role": "admin"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 403


async def test_admin_can_assign_moderador_role(client: AsyncClient, db_session: AsyncSession):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    target_token, target_id = make_token()

    response = await client.put(
        f"/users/{target_id}/role",
        json={"role": "moderador"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "moderador"


async def test_participante_cannot_create_community(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.post(
        "/communities", json={"nome": "Comunidade Teste"}, headers=auth_headers(token)
    )
    assert response.status_code == 403


async def test_participante_can_list_communities(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.get("/communities", headers=auth_headers(token))
    assert response.status_code == 200


async def test_moderador_can_create_community(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.post(
        "/communities", json={"nome": "Comunidade Teste"}, headers=auth_headers(token)
    )
    assert response.status_code == 201


async def test_participante_cannot_create_gallery_album(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.post("/gallery/albums", json={}, headers=auth_headers(token))
    assert response.status_code == 403


async def test_participante_can_list_gallery_albums(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.get("/gallery/albums", headers=auth_headers(token))
    assert response.status_code == 200


async def test_moderador_can_create_gallery_album(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.post("/gallery/albums", json={}, headers=auth_headers(token))
    assert response.status_code == 201
