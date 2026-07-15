from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento
from app.models.evento_tag import EventoTag
from app.models.tag import Tag
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
    assert data["created_by"] == user_id


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


async def test_list_events_filters_by_current_user(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token(email="owner@example.com")
    other_token, other_user_id = make_token(email="other@example.com")
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)
    await set_user_role(db_session, other_user_id, Role.PARTICIPANTE)

    base_payload = {
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    await client.post(
        "/events",
        json={**base_payload, "nome": "Evento do Usuario"},
        headers=auth_headers(token),
    )
    await client.post(
        "/events",
        json={**base_payload, "nome": "Evento de Outra Pessoa"},
        headers=auth_headers(other_token),
    )

    response = await client.get(
        "/events",
        params={"page": 1, "page_size": 20, "mine": "true"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["nome"] == "Evento do Usuario"
    assert data["items"][0]["created_by"] == user_id


async def test_list_events_participant_is_always_scoped_to_current_user(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token(email="owner@example.com")
    other_token, other_user_id = make_token(email="other@example.com")
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)
    await set_user_role(db_session, other_user_id, Role.PARTICIPANTE)

    base_payload = {
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    await client.post(
        "/events",
        json={**base_payload, "nome": "Evento do Participante"},
        headers=auth_headers(token),
    )
    await client.post(
        "/events",
        json={**base_payload, "nome": "Evento de Outra Conta"},
        headers=auth_headers(other_token),
    )

    list_response = await client.get("/events", headers=auth_headers(token))
    response = await client.get(
        "/events",
        params={"page": 1, "page_size": 20},
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data) == 1
    assert list_data[0]["nome"] == "Evento do Participante"
    assert list_data[0]["created_by"] == user_id

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["nome"] == "Evento do Participante"
    assert data["items"][0]["created_by"] == user_id


async def test_participant_event_goes_to_review_and_can_be_approved(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento para Revisao",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "em_analise"
    assert created["created_by"] == participant_id

    public_response = await client.get("/events/slug/evento-para-revisao")
    assert public_response.status_code == 404

    owner_response = await client.get(
        "/events/slug/evento-para-revisao", headers=auth_headers(participant_token)
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["status"] == "em_analise"

    approve_response = await client.post(
        f"/events/{created['id']}/approve", headers=auth_headers(admin_token)
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "publicado"

    published_response = await client.get("/events/published")
    assert published_response.status_code == 200
    assert published_response.json()[0]["nome"] == "Evento para Revisao"


async def test_admin_can_reject_event_and_participant_still_sees_it(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento Recusavel",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    reject_response = await client.post(
        f"/events/{event_id}/reject",
        json={"motivo": "Faltou informar o endereco completo do evento"},
        headers=auth_headers(admin_token),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "recusado"
    assert reject_response.json()["motivo_recusa"] == "Faltou informar o endereco completo do evento"

    list_response = await client.get(
        "/events", params={"page": 1, "page_size": 20}, headers=auth_headers(participant_token)
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["total"] == 1
    assert data["items"][0]["nome"] == "Evento Recusavel"
    assert data["items"][0]["status"] == "recusado"


async def test_reject_event_requires_motivo(client: AsyncClient, db_session: AsyncSession):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento Sem Motivo",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    missing_response = await client.post(
        f"/events/{event_id}/reject", json={}, headers=auth_headers(admin_token)
    )
    assert missing_response.status_code == 422

    too_short_response = await client.post(
        f"/events/{event_id}/reject", json={"motivo": "curto"}, headers=auth_headers(admin_token)
    )
    assert too_short_response.status_code == 422


async def test_approve_event_clears_motivo_recusa(client: AsyncClient, db_session: AsyncSession):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento Recusado Depois Aprovado",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    reject_response = await client.post(
        f"/events/{event_id}/reject",
        json={"motivo": "Faltou o link de inscricao do evento"},
        headers=auth_headers(admin_token),
    )
    assert reject_response.json()["motivo_recusa"] == "Faltou o link de inscricao do evento"

    approve_response = await client.post(
        f"/events/{event_id}/approve", headers=auth_headers(admin_token)
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "publicado"
    assert approve_response.json()["motivo_recusa"] is None


async def test_participant_can_edit_own_published_event_and_it_returns_to_review(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento do Participante",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    approve_response = await client.post(
        f"/events/{event_id}/approve", headers=auth_headers(admin_token)
    )
    assert approve_response.json()["status"] == "publicado"

    update_response = await client.put(
        f"/events/{event_id}",
        json={"nome": "Evento do Participante Editado"},
        headers=auth_headers(participant_token),
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["nome"] == "Evento do Participante Editado"
    assert updated["status"] == "em_analise"


async def test_participant_can_edit_own_rejected_event_and_it_returns_to_review(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    admin_token, admin_id = make_token(email="admin@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, admin_id, Role.ADMIN)

    payload = {
        "nome": "Evento Recusado",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    reject_response = await client.post(
        f"/events/{event_id}/reject",
        json={"motivo": "Falta descricao detalhada do evento"},
        headers=auth_headers(admin_token),
    )
    assert reject_response.json()["status"] == "recusado"

    update_response = await client.put(
        f"/events/{event_id}",
        json={"nome": "Evento Recusado Corrigido"},
        headers=auth_headers(participant_token),
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["nome"] == "Evento Recusado Corrigido"
    assert updated["status"] == "em_analise"
    assert updated["motivo_recusa"] is None


async def test_participant_cannot_edit_event_created_by_another_participant(
    client: AsyncClient, db_session: AsyncSession
):
    owner_token, owner_id = make_token(email="owner@example.com")
    other_token, other_id = make_token(email="other@example.com")
    await set_user_role(db_session, owner_id, Role.PARTICIPANTE)
    await set_user_role(db_session, other_id, Role.PARTICIPANTE)

    payload = {
        "nome": "Evento de Outra Conta",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(owner_token))
    event_id = create_response.json()["id"]

    update_response = await client.put(
        f"/events/{event_id}",
        json={"nome": "Tentativa de Edicao Alheia"},
        headers=auth_headers(other_token),
    )

    assert update_response.status_code == 403


async def test_participant_cannot_edit_event_waiting_for_review(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)

    payload = {
        "nome": "Evento Em Analise",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]
    assert create_response.json()["status"] == "em_analise"

    update_response = await client.put(
        f"/events/{event_id}",
        json={"nome": "Evento Em Analise Editado"},
        headers=auth_headers(participant_token),
    )

    assert update_response.status_code == 403


async def test_moderator_cannot_publish_event_waiting_for_review(
    client: AsyncClient, db_session: AsyncSession
):
    participant_token, participant_id = make_token(email="participante@example.com")
    moderator_token, moderator_id = make_token(email="moderador@example.com")
    await set_user_role(db_session, participant_id, Role.PARTICIPANTE)
    await set_user_role(db_session, moderator_id, Role.MODERADOR)

    payload = {
        "nome": "Evento Pendente",
        "data_evento": "25/12/2026",
        "horario": "19:00",
        "dia_semana": "Sexta",
        "link": "https://example.com",
        "status": "publicado",
    }
    create_response = await client.post("/events", json=payload, headers=auth_headers(participant_token))
    event_id = create_response.json()["id"]

    response = await client.post(f"/events/{event_id}/publish", headers=auth_headers(moderator_token))
    assert response.status_code == 403

    update_response = await client.put(
        f"/events/{event_id}",
        json={"status": "publicado"},
        headers=auth_headers(moderator_token),
    )
    assert update_response.status_code == 403


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


async def test_list_events_filters_by_date_filter(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    for nome, data_evento in (
        ("Evento Antigo", yesterday),
        ("Evento Hoje", today),
        ("Evento Futuro", tomorrow),
    ):
        db_session.add(
            Evento(
                nome=nome,
                slug=nome.lower().replace(" ", "-"),
                data_evento=data_evento.strftime("%d/%m/%Y"),
                horario="19:00",
                dia_semana="Sexta",
                link="https://example.com",
                status="publicado",
            )
        )
    await db_session.commit()

    active_response = await client.get(
        "/events",
        params={"page": 1, "page_size": 20, "date_filter": "upcoming"},
        headers=auth_headers(token),
    )
    inactive_response = await client.get(
        "/events",
        params={"page": 1, "page_size": 20, "date_filter": "past"},
        headers=auth_headers(token),
    )

    assert active_response.status_code == 200
    active_data = active_response.json()
    assert active_data["total"] == 2
    assert {item["nome"] for item in active_data["items"]} == {"Evento Hoje", "Evento Futuro"}

    assert inactive_response.status_code == 200
    inactive_data = inactive_response.json()
    assert inactive_data["total"] == 1
    assert inactive_data["items"][0]["nome"] == "Evento Antigo"


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


async def test_get_event_metrics_requires_auth(client: AsyncClient):
    response = await client.get("/events/metrics")
    assert response.status_code == 401


async def test_get_event_metrics_returns_aggregations(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    tag_python = Tag(nome="Python", cor="#2563eb")
    tag_ia = Tag(nome="IA", cor="#16a34a")
    db_session.add_all([tag_python, tag_ia])
    await db_session.flush()

    eventos = [
        Evento(
            nome="Meetup Python SP",
            slug="meetup-python-sp",
            data_evento="10/01/2026",
            horario="19:00",
            dia_semana="Sexta",
            periodo="Noturno",
            modalidade="Presencial",
            cidade="São Paulo",
            estado="SP",
            link="https://example.com",
            status="publicado",
        ),
        Evento(
            nome="Meetup Python RJ",
            slug="meetup-python-rj",
            data_evento="17/01/2026",
            horario="09:00",
            dia_semana="Sexta",
            periodo="Matinal",
            modalidade="Online",
            cidade="Rio de Janeiro",
            estado="RJ",
            link="https://example.com",
            status="publicado",
        ),
        Evento(
            nome="Workshop IA",
            slug="workshop-ia",
            data_evento="24/01/2026",
            horario="14:00",
            dia_semana="Sábado",
            periodo="Vespertino",
            modalidade="Online",
            cidade="São Paulo",
            estado="SP",
            link="https://example.com",
            status="rascunho",
        ),
    ]
    db_session.add_all(eventos)
    await db_session.flush()

    db_session.add_all(
        [
            EventoTag(evento_id=eventos[0].id, tag_id=tag_python.id),
            EventoTag(evento_id=eventos[1].id, tag_id=tag_python.id),
            EventoTag(evento_id=eventos[2].id, tag_id=tag_ia.id),
        ]
    )
    await db_session.commit()

    response = await client.get("/events/metrics", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()

    assert data["total_eventos"] == 3
    assert data["media_eventos_por_semana"] > 0

    dia_semana_totais = {item["dia_semana"]: item["total"] for item in data["por_dia_semana"]}
    assert dia_semana_totais == {"Sexta": 2, "Sábado": 1}

    status_totais = {item["status"]: item["total"] for item in data["por_status"]}
    assert status_totais == {"publicado": 2, "rascunho": 1}

    top_tags = {item["nome"]: item["total"] for item in data["top_tags"]}
    assert top_tags == {"Python": 2, "IA": 1}

    assert data["evolucao_mensal"] == [{"ano_mes": "2026-01", "total": 3}]

    cidades = {item["cidade"] for item in data["por_cidade"]}
    assert cidades == {"São Paulo", "Rio de Janeiro"}


async def test_get_event_metrics_filters_by_date_range(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.MODERADOR)

    db_session.add_all(
        [
            Evento(
                nome="Evento Fora do Range",
                slug="evento-fora-do-range",
                data_evento="01/01/2025",
                horario="19:00",
                dia_semana="Quarta",
                link="https://example.com",
                status="publicado",
            ),
            Evento(
                nome="Evento Dentro do Range",
                slug="evento-dentro-do-range",
                data_evento="15/06/2026",
                horario="19:00",
                dia_semana="Segunda",
                link="https://example.com",
                status="publicado",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/events/metrics",
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_eventos"] == 1
    assert data["por_dia_semana"] == [{"dia_semana": "Segunda", "total": 1}]
