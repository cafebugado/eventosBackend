import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunidade import Comunidade
from app.models.evento import Evento
from app.models.galeria import GaleriaAlbum, GaleriaFoto
from app.models.user_profile import UserProfile

pytestmark = pytest.mark.asyncio


async def test_list_albums_public_is_public_and_returns_empty_list(client: AsyncClient):
    response = await client.get("/gallery/albums/public")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_albums_public_resolves_denormalized_names(
    client: AsyncClient, db_session: AsyncSession
):
    creator_id = uuid.uuid4()
    uploader_id = uuid.uuid4()

    evento = Evento(
        nome="Meetup Python SP",
        slug="meetup-python-sp",
        data_evento="25/12/2026",
        horario="19:00",
        dia_semana="Sexta",
        link="https://example.com",
        status="publicado",
    )
    comunidade = Comunidade(nome="Café Bugado")
    db_session.add_all([evento, comunidade])
    await db_session.flush()

    db_session.add_all(
        [
            UserProfile(user_id=creator_id, nome="Maria", sobrenome="Silva"),
            UserProfile(user_id=uploader_id, nome="Joao", sobrenome=None),
        ]
    )

    album = GaleriaAlbum(evento_id=evento.id, comunidade_id=comunidade.id, created_by=creator_id)
    db_session.add(album)
    await db_session.flush()

    db_session.add_all(
        [
            GaleriaFoto(
                album_id=album.id,
                url="https://example.com/foto2.jpg",
                legenda="Segunda foto",
                ordem=1,
                uploaded_by=uploader_id,
            ),
            GaleriaFoto(
                album_id=album.id,
                url="https://example.com/foto1.jpg",
                legenda="Primeira foto",
                ordem=0,
                uploaded_by=None,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/gallery/albums/public")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    album_data = data[0]
    assert album_data["evento_nome"] == "Meetup Python SP"
    assert album_data["evento_data"] == "25/12/2026"
    assert album_data["comunidade_nome"] == "Café Bugado"
    assert album_data["created_by_nome"] == "Maria Silva"

    fotos = album_data["fotos"]
    assert [f["legenda"] for f in fotos] == ["Primeira foto", "Segunda foto"]
    assert fotos[0]["uploaded_by_nome"] is None
    assert fotos[1]["uploaded_by_nome"] == "Joao"


async def test_list_albums_public_handles_album_without_evento_or_comunidade(
    client: AsyncClient, db_session: AsyncSession
):
    album = GaleriaAlbum(evento_id=None, comunidade_id=None, created_by=None)
    db_session.add(album)
    await db_session.commit()

    response = await client.get("/gallery/albums/public")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["evento_nome"] is None
    assert data[0]["comunidade_nome"] is None
    assert data[0]["created_by_nome"] is None
    assert data[0]["fotos"] == []
