import xml.etree.ElementTree as ET
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import NotFoundError
from app.models.evento import Evento

pytestmark = pytest.mark.asyncio


async def test_health_returns_ok_when_database_is_available(
    client: AsyncClient,
):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_returns_503_when_database_fails(
        client: AsyncClient,
        db_session,
):
    with patch.object(
        db_session,
        "execute",
        new_callable=AsyncMock,
        side_effect=Exception("Database unavailable"),
    ):

        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}


async def test_og_returns_default_metadata_for_non_event_path(
    client: AsyncClient,
):
    response = await client.get("/og", params={"path": "/comunidades"})

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Agenda de Eventos"
    assert data["description"] == "Confira os proximos eventos de tecnologia."
    assert data["image"].endswith("/og-default.png")
    assert data["url"].endswith("/comunidades")


async def test_og_returns_default_metadata_when_event_is_not_found(
    client: AsyncClient,
):
    with patch("app.routers.meta.EventoService") as service_mock:
        service_mock.return_value.get_event_by_slug_or_id = AsyncMock(
            side_effect=NotFoundError("Evento nao encontrado")
        )

        response = await client.get(
            "/og",
            params={"path": "/eventos/evento-inexistente"},
        )

    assert response.status_code == 200
    assert response.json()["title"] == "Agenda de Eventos"


async def test_og_returns_event_metadata(client: AsyncClient):
    evento = SimpleNamespace(
        nome="Meetup Python",
        descricao="Encontro para pessoas desenvolvedoras.",
        imagem="https://example.com/evento.png",
    )

    with patch("app.routers.meta.EventoService") as service_mock:
        service_mock.return_value.get_event_by_slug_or_id = AsyncMock(
            return_value=evento
        )

        response = await client.get(
            "/og",
            params={"path": "/eventos/meetup-python"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Meetup Python"
    assert data["description"] == "Encontro para pessoas desenvolvedoras."
    assert data["image"] == "https://example.com/evento.png"
    assert data["url"].endswith("/eventos/meetup-python")


async def test_sitemap_returns_valid_xml_with_only_published_events(
    client: AsyncClient,
    db_session,
):
    published_event = Evento(
        nome="Meetup Python",
        slug="meetup-python",
        data_evento="15/12/2026",
        horario="19:00",
        dia_semana="Terça",
        link="https://example.com",
        status="publicado",
        updated_at=datetime(2026, 10, 15),
    )
    draft_event = Evento(
        nome="Evento Rascunho",
        slug="evento-rascunho",
        data_evento="20/12/2026",
        horario="19:00",
        dia_semana="Domingo",
        link="https://example.com",
        status="rascunho",
        updated_at=datetime(2026, 10, 15),
    )

    db_session.add_all([published_event, draft_event])
    await db_session.commit()

    response = await client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]

    root = ET.fromstring(response.text)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [
        element.text
        for element in root.findall("sm:url/sm:loc", namespace)
    ]

    assert "https://agendas-eventos.vercel.app/" in urls
    assert "https://agendas-eventos.vercel.app/eventos/meetup-python" in urls
    assert "https://agendas-eventos.vercel.app/eventos/evento-rascunho" not in urls
