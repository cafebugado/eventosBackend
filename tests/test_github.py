
import httpx
import pytest

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.integrations.github import _get


@pytest.mark.asyncio
async def test_github_user_not_found():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404)
    )

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(NotFoundError) as exc:
            await _get(
                client,
                "https://api.github.com/users/usuario-inexistente",
                not_found_message="Usuario do GitHub nao encontrado",
            )

    assert exc.value.message == "Usuario do GitHub nao encontrado"
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_github_server_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500)
    )

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ExternalServiceError) as exc:
            await _get(client, "https://api.github.com/users/test")

    assert exc.value.status_code == 502
    assert exc.value.message == "Falha ao consultar a API do GitHub: 500"


@pytest.mark.asyncio
async def test_github_connection_error():
    def raise_connection_error(request):
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(raise_connection_error)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ExternalServiceError) as exc:
            await _get(client, "https://api.github.com/users/test")

    assert exc.value.status_code == 502
    assert exc.value.message == "Falha ao consultar a API do GitHub"
