import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento
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


async def test_create_event_duplicate_name_returns_conflict(client: AsyncClient, db_session: AsyncSession):
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
    r2 = await client.post(
        "/events",
        json={**payload, "nome": " meetup python "},
        headers=auth_headers(token),
    )
    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["detail"] == "Ja existe um evento cadastrado com este nome"


async def test_update_event_duplicate_name_returns_conflict(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    base_payload = {
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    await client.post(
        "/events",
        json={"nome": "Meetup Python", **base_payload},
        headers=auth_headers(token),
    )
    other = await client.post(
        "/events",
        json={"nome": "Evento Frontend", **base_payload},
        headers=auth_headers(token),
    )

    response = await client.put(
        f"/events/{other.json()['id']}",
        json={"nome": "Meetup Python"},
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Ja existe um evento cadastrado com este nome"


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


async def test_list_events_supports_pagination_and_filters(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    base_payload = {
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
    }
    for index in range(3):
        await client.post(
            "/events",
            json={
                **base_payload,
                "nome": f"Evento Publico {index}",
                "descricao": "Evento para listagem",
                "status": "publicado",
            },
            headers=auth_headers(token),
        )
    await client.post(
        "/events",
        json={**base_payload, "nome": "Evento Rascunho", "status": "rascunho"},
        headers=auth_headers(token),
    )

    response = await client.get(
        "/events",
        params={"page": 1, "page_size": 2, "status": "publicado", "search": "Evento"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert all(item["status"] == "publicado" for item in data["items"])


async def test_list_events_pagination_includes_past_events(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    for index in range(25):
        db_session.add(
            Evento(
                nome=f"Evento Antigo {index}",
                slug=f"evento-antigo-{index}",
                data_evento="01/01/2025",
                horario="19:00",
                dia_semana="Quarta",
                link="https://example.com",
                status="publicado",
            )
        )
    await db_session.commit()

    response = await client.get(
        "/events",
        params={"page": 1, "page_size": 20},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 20
    assert all(item["data_evento"] == "01/01/2025" for item in data["items"])


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
