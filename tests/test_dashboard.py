import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento
from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _br_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


async def test_dashboard_summary_requires_auth(client: AsyncClient):
    response = await client.get("/dashboard/summary")
    assert response.status_code == 401


async def test_dashboard_summary_counts_and_rbac(client: AsyncClient, db_session: AsyncSession):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.PARTICIPANTE)

    today = date.today()

    eventos = [
        Evento(
            nome="Evento de hoje",
            slug="evento-de-hoje",
            data_evento=_br_date(today),
            horario="19:00",
            dia_semana="Sexta",
            periodo="Noturno",
            modalidade="Presencial",
            link="https://example.com",
            status="publicado",
            created_by=uuid.UUID(user_id),
        ),
        Evento(
            nome="Evento futuro",
            slug="evento-futuro",
            data_evento=_br_date(today + timedelta(days=3)),
            horario="09:00",
            dia_semana="Segunda",
            periodo="Matinal",
            modalidade="Online",
            link="https://example.com",
            status="publicado",
        ),
        Evento(
            nome="Evento em analise",
            slug="evento-em-analise",
            data_evento=_br_date(today + timedelta(days=5)),
            horario="14:00",
            dia_semana="Quarta",
            periodo="Vespertino",
            modalidade="Online",
            link="https://example.com",
            status="em_analise",
        ),
    ]
    db_session.add_all(eventos)
    await db_session.commit()

    response = await client.get("/dashboard/summary", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()

    assert data["eventos"]["total"] == 3
    assert data["eventos"]["hoje"] == 1
    assert data["eventos"]["meus_eventos"] == 1
    assert data["eventos"]["noturno"] == 1

    assert len(data["proximos_eventos"]) == 2

    # participante nao tem permissao para revisar eventos nem gerenciar comunidades/usuarios
    assert data["pendentes_revisao"] == []
    assert data["comunidades"] is None
    assert data["contribuintes"] is None
    assert data["fotos"] is None
    assert data["usuarios"] is None
    assert data["atividade_recente"] == []


async def test_dashboard_summary_admin_sees_management_blocks(
    client: AsyncClient, db_session: AsyncSession
):
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)

    evento_em_analise = Evento(
        nome="Pendente de revisao",
        slug="pendente-de-revisao",
        data_evento=_br_date(date.today() + timedelta(days=1)),
        horario="10:00",
        dia_semana="Terça",
        periodo="Matinal",
        modalidade="Online",
        link="https://example.com",
        status="em_analise",
    )
    db_session.add(evento_em_analise)
    await db_session.commit()

    response = await client.get("/dashboard/summary", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()

    assert len(data["pendentes_revisao"]) == 1
    assert data["pendentes_revisao"][0]["nome"] == "Pendente de revisao"
    assert data["comunidades"] == 0
    assert data["contribuintes"] == 0
    assert data["usuarios"] == 1
