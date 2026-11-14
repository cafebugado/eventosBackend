from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from app.main import app

ORIGIN = settings.cors_origins_list[0]


def test_preflight_recebe_request_id() -> None:
    client = TestClient(app)
    response = client.options(
        "/qualquer-rota",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"},
    )
    assert REQUEST_ID_HEADER in response.headers


def test_429_do_slowapi_recebe_request_id() -> None:
    limiter = Limiter(key_func=get_remote_address)
    mini = FastAPI()
    mini.state.limiter = limiter
    mini.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    mini.add_middleware(RequestIdMiddleware)

    @mini.get("/limitada")
    @limiter.limit("1/minute")
    async def limitada(request: Request) -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(mini)
    assert client.get("/limitada").status_code == 200
    response = client.get("/limitada")
    assert response.status_code == 429
    assert REQUEST_ID_HEADER in response.headers


def test_404_recebe_request_id_e_expose_headers() -> None:
    client = TestClient(app)
    response = client.get("/rota-que-nao-existe", headers={"Origin": ORIGIN})
    assert response.status_code == 404
    assert REQUEST_ID_HEADER in response.headers
    expose = response.headers["access-control-expose-headers"].lower()
    assert REQUEST_ID_HEADER.lower() in expose
