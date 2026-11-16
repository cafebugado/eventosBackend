import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from app.schemas.contribuinte import GitHubUserInfo
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def contributor_payload(username: str = "octocat") -> dict[str, str]:
    return {
        "github_username": username,
        "nome": "Octocat",
        "avatar_url": "https://example.com/avatar.png",
        "github_url": f"https://github.com/{username}",
    }


async def admin_token(db_session: AsyncSession) -> str:
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)
    return token


async def test_list_contributors(client: AsyncClient):
    response = await client.get("/contributors")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_create_and_get_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    created = await client.post(
        "/contributors",
        json=contributor_payload("octocat"),
        headers=auth_headers(token),
    )

    assert created.status_code == 201
    assert created.json()["github_username"] == "octocat"

    contributor_id = created.json()["id"]
    response = await client.get(f"/contributors/{contributor_id}")

    assert response.status_code == 200
    assert response.json()["id"] == contributor_id


async def test_create_duplicate_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    payload = contributor_payload("octocat")

    first = await client.post(
        "/contributors", json=payload, headers=auth_headers(token)
    )
    second = await client.post(
        "/contributors", json=payload, headers=auth_headers(token)
    )

    assert first.status_code == 201
    assert second.status_code == 409


async def test_update_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    created = await client.post(
        "/contributors",
        json=contributor_payload("octocat"),
        headers=auth_headers(token),
    )
    assert created.status_code == 201

    contributor_id = created.json()["id"]
    response = await client.put(
        f"/contributors/{contributor_id}",
        json={"nome": "Octocat Atualizado"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Octocat Atualizado"


async def test_update_nonexistent_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    response = await client.put(
        "/contributors/00000000-0000-0000-0000-000000000001",
        json={"nome": "Nome Atualizado"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


async def test_delete_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    created = await client.post(
        "/contributors",
        json=contributor_payload("octocat"),
        headers=auth_headers(token),
    )
    assert created.status_code == 201

    contributor_id = created.json()["id"]
    response = await client.delete(
        f"/contributors/{contributor_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 204

    lookup = await client.get(f"/contributors/{contributor_id}")
    assert lookup.status_code == 404


async def test_delete_nonexistent_contributor(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    response = await client.delete(
        "/contributors/00000000-0000-0000-0000-000000000001",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

async def test_create_contributor_with_invalid_username(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    response = await client.post(
        "/contributors",
        json=contributor_payload("-nome-invalido"),
        headers=auth_headers(token),
    )

    assert response.status_code == 422


async def test_get_github_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def fake_get_user_info(username: str) -> GitHubUserInfo:
        return GitHubUserInfo(
            github_username=username,
            nome="Octocat",
            avatar_url="https://example.com/avatar.png",
            github_url=f"https://github.com/{username}",
        )

    monkeypatch.setattr(
        "app.services.contribuinte_service.get_user_info",
        fake_get_user_info,
    )

    response = await client.get("/contributors/github/octocat")

    assert response.status_code == 200
    assert response.json()["github_username"] == "octocat"
    assert response.json()["nome"] == "Octocat"


@pytest.mark.parametrize(
    ("actor_role", "operation"),
    [
        (Role.MODERADOR, "create"),
        (Role.MODERADOR, "update"),
        (Role.MODERADOR, "delete"),
        (Role.PARTICIPANTE, "create"),
        (Role.PARTICIPANTE, "update"),
        (Role.PARTICIPANTE, "delete"),
    ],
)
async def test_roles_without_permission_cannot_manage_contributors(
    client: AsyncClient,
    db_session: AsyncSession,
    actor_role: Role,
    operation: str,
):
    admin = await admin_token(db_session)

    contributor_id = None
    if operation != "create":
        created = await client.post(
            "/contributors",
            json=contributor_payload("octocat"),
            headers=auth_headers(admin),
        )
        assert created.status_code == 201
        contributor_id = created.json()["id"]

    token, user_id = make_token()
    await set_user_role(db_session, user_id, actor_role)

    if operation == "create":
        response = await client.post(
            "/contributors",
            json=contributor_payload("new-contributor"),
            headers=auth_headers(token),
        )
    elif operation == "update":
        response = await client.put(
            f"/contributors/{contributor_id}",
            json={"nome": "Nome alterado"},
            headers=auth_headers(token),
        )
    else:
        response = await client.delete(
            f"/contributors/{contributor_id}",
            headers=auth_headers(token),
        )

    assert response.status_code == 403


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_super_admin_can_manage_contributors(
    client: AsyncClient,
    db_session: AsyncSession,
    operation: str,
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.SUPER_ADMIN)

    contributor_id = None
    if operation != "create":
        created = await client.post(
            "/contributors",
            json=contributor_payload("octocat"),
            headers=auth_headers(token),
        )
        assert created.status_code == 201
        contributor_id = created.json()["id"]

    if operation == "create":
        response = await client.post(
            "/contributors",
            json=contributor_payload("new-contributor"),
            headers=auth_headers(token),
        )
        assert response.status_code == 201
    elif operation == "update":
        response = await client.put(
            f"/contributors/{contributor_id}",
            json={"nome": "Nome atualizado"},
            headers=auth_headers(token),
        )
        assert response.status_code == 200
    else:
        response = await client.delete(
            f"/contributors/{contributor_id}",
            headers=auth_headers(token),
        )
        assert response.status_code == 204
