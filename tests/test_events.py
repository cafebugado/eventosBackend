import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_event_requires_auth(client: AsyncClient):
    payload = {
        "nome": "Meetup Python",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 401


async def test_create_event_generates_slug(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    payload = {
        "nome": "Meetup Python",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    response = await client.post("/events", json=payload, headers=auth_headers(token))
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "meetup-python"


async def test_create_event_duplicate_name_gets_unique_slug(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    payload = {
        "nome": "Meetup Python",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    r1 = await client.post("/events", json=payload, headers=auth_headers(token))
    r2 = await client.post("/events", json=payload, headers=auth_headers(token))
    assert r1.json()["slug"] == "meetup-python"
    assert r2.json()["slug"] == "meetup-python-2"


async def test_get_published_events_is_public(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    payload = {
        "nome": "Evento Publico",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    await client.post("/events", json=payload, headers=auth_headers(token))

    response = await client.get("/events/published")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_event_by_slug(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    payload = {
        "nome": "Evento Slug",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    await client.post("/events", json=payload, headers=auth_headers(token))

    response = await client.get("/events/slug/evento-slug")
    assert response.status_code == 200
    assert response.json()["nome"] == "Evento Slug"


async def test_get_event_by_slug_not_found(client: AsyncClient):
    response = await client.get("/events/slug/does-not-exist")
    assert response.status_code == 404
