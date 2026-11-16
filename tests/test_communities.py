import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_list_communities(client: AsyncClient):
    response = await client.get("/communities")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_create_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    response = await client.post(
        "/communities",
        json={"nome": "Comunidade Nova"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["nome"] == "Comunidade Nova"
    assert response.json()["created_by"] == user_id


async def test_update_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade Original"},
        headers=auth_headers(token),
    )
    assert created.status_code == 201

    community_id = created.json()["id"]

    response = await client.put(
        f"/communities/{community_id}",
        json={"nome": "Comunidade Atualizada"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Comunidade Atualizada"


async def test_update_nonexistent_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    response = await client.put(
        f"/communities/{uuid.uuid4()}",
        json={"nome": "Comunidade Atualizada"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


async def test_delete_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade para excluir"},
        headers=auth_headers(token),
    )
    assert created.status_code == 201

    community_id = created.json()["id"]

    response = await client.delete(
        f"/communities/{community_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204

    listing = await client.get("/communities")
    assert all(item["id"] != community_id for item in listing.json())


async def test_delete_nonexistent_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    response = await client.delete(
        f"/communities/{uuid.uuid4()}",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


async def test_create_community_without_name(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    response = await client.post(
        "/communities",
        json={},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


async def test_moderador_can_create_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.post(
        "/communities",
        json={"nome": "Comunidade do Moderador"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201


async def test_participante_cannot_create_community(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.post(
        "/communities",
        json={"nome": "Comunidade não autorizada"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


async def test_moderador_can_update_community(
    client: AsyncClient, db_session: AsyncSession
):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade Original"},
        headers=auth_headers(admin_token),
    )
    assert created.status_code == 201

    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.put(
        f"/communities/{created.json()['id']}",
        json={"nome": "Comunidade Editada pelo Moderador"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Comunidade Editada pelo Moderador"


async def test_participante_cannot_update_community(
    client: AsyncClient, db_session: AsyncSession
):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade Original"},
        headers=auth_headers(admin_token),
    )
    assert created.status_code == 201

    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.put(
        f"/communities/{created.json()['id']}",
        json={"nome": "Tentativa de edição"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


async def test_moderador_can_delete_community(
    client: AsyncClient, db_session: AsyncSession
):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade para excluir"},
        headers=auth_headers(admin_token),
    )
    assert created.status_code == 201

    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.delete(
        f"/communities/{created.json()['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204


async def test_participante_cannot_delete_community(
    client: AsyncClient, db_session: AsyncSession
):
    admin_token, admin_id = make_token()
    await set_user_role(db_session, admin_id, Role.ADMIN)

    created = await client.post(
        "/communities",
        json={"nome": "Comunidade protegida"},
        headers=auth_headers(admin_token),
    )
    assert created.status_code == 201

    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    response = await client.delete(
        f"/communities/{created.json()['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 403
