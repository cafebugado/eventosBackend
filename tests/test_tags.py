import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_list_tags(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    response = await client.post(
        "/tags", json={"nome": "Python", "cor": "#306998"}, headers=auth_headers(token)
    )
    assert response.status_code == 201

    response = await client.get("/tags")
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 1
    assert tags[0]["nome"] == "Python"


async def test_create_duplicate_tag_conflict(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    await client.post("/tags", json={"nome": "Python"}, headers=auth_headers(token))
    response = await client.post("/tags", json={"nome": "Python"}, headers=auth_headers(token))
    assert response.status_code == 409


async def test_set_and_get_event_tags(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    tag_resp = await client.post("/tags", json={"nome": "Python"}, headers=auth_headers(token))
    tag_id = tag_resp.json()["id"]

    event_payload = {
        "nome": "Evento Tags",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    event_resp = await client.post("/events", json=event_payload, headers=auth_headers(token))
    event_id = event_resp.json()["id"]

    response = await client.put(
        f"/events/{event_id}/tags", json={"tag_ids": [tag_id]}, headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()[0]["nome"] == "Python"

    response = await client.get(f"/events/{event_id}/tags")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_participant_can_set_tags_only_on_own_event(client: AsyncClient, db_session: AsyncSession):
    moderator_token, moderator_id = make_token(email="moderador@example.com")
    participant_token, participant_id = make_token(email="participante@example.com")
    other_token, other_id = make_token(email="outro@example.com")
    await set_user_role(db_session, moderator_id, Role.MODERADOR)
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, other_id, Role.PARTICIPANTE)

    tag_resp = await client.post("/tags", json={"nome": "Comunidade"}, headers=auth_headers(moderator_token))
    tag_id = tag_resp.json()["id"]

    event_payload = {
        "nome": "Evento com Tags do Participante",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    event_resp = await client.post("/events", json=event_payload, headers=auth_headers(participant_token))
    event_id = event_resp.json()["id"]

    own_response = await client.put(
        f"/events/{event_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=auth_headers(participant_token),
    )
    assert own_response.status_code == 200
    assert own_response.json()[0]["nome"] == "Comunidade"

    other_response = await client.put(
        f"/events/{event_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=auth_headers(other_token),
    )
    assert other_response.status_code == 403
