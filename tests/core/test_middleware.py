import asyncio
import json
import logging
import uuid
from typing import Any

import pytest
import structlog
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.types import Receive, Scope, Send

from app.core import middleware as middleware_module
from app.core.config import settings
from app.core.logging import HANDLER_NAME, setup_logging
from app.core.middleware import RequestIdMiddleware

ORIGIN = "http://localhost:5173"


class SimulatedError(Exception):
    """Erro simulado: existe só nos testes. O código de produção não sabe que é teste."""


@pytest.fixture
def json_logging(capsys, monkeypatch):
    monkeypatch.setattr(settings, "SERVICE_NAME", "svc-teste")
    monkeypatch.setattr(settings, "ENVIRONMENT", "preview")
    monkeypatch.setattr(settings, "SENTRY_DSN", "")  # impede o init do Sentry no setup_logging
    setup_logging("INFO")
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        if h.get_name() == HANDLER_NAME:
            root.removeHandler(h)
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def _read_logs(capsys) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in capsys.readouterr().out.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("logger") == "httpx":  # ruído do TestClient
            continue
        records.append(record)
    return records


def _completed(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r["event"] == "http.request.completed"]


def _build_app() -> FastAPI:
    app = FastAPI()
    endpoint_logger = logging.getLogger("app.test.endpoint")

    # Espelha o handler genérico do projeto (chave Exception => ServerErrorMiddleware).
    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "erro interno"})

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        endpoint_logger.info("endpoint-async")
        return {"ok": True}

    @app.get("/ok-sync")
    def ok_sync() -> dict[str, bool]:  # roda em threadpool: o contexto precisa atravessar
        endpoint_logger.info("endpoint-sync")
        return {"ok": True}

    @app.get("/user-async")
    async def user_async(request: Request) -> dict[str, bool]:
        request.state.user_id = "u-123"
        return {"ok": True}

    @app.get("/user-sync")
    def user_sync(request: Request) -> dict[str, bool]:
        request.state.user_id = "u-123"
        return {"ok": True}

    @app.get("/own-header")
    async def own_header() -> Response:
        return Response(content="x", headers={"X-Request-ID": "from-endpoint"})

    @app.get("/bg")
    async def bg(tasks: BackgroundTasks) -> dict[str, bool]:
        async def slow() -> None:
            await asyncio.sleep(0.3)

        tasks.add_task(slow)
        return {"ok": True}

    @app.get("/boom")
    async def boom() -> None:
        raise SimulatedError("erro simulado (teste)")

    # O ÚLTIMO add_middleware é o mais externo: request id depois do CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGIN],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)
    return app


@pytest.mark.parametrize(
    ("path", "marker"), [("/ok", "endpoint-async"), ("/ok-sync", "endpoint-sync")]
)
def test_logs_carry_the_same_request_id_as_the_response_header(json_logging, capsys, path, marker):
    # Critério de aceite da task.
    with TestClient(_build_app()) as client:
        response = client.get(path)

    request_id = response.headers["x-request-id"]
    records = _read_logs(capsys)
    inside = [r for r in records if r["event"] == marker]
    completed = _completed(records)
    assert len(inside) == 1 and inside[0]["request_id"] == request_id
    assert len(completed) == 1 and completed[0]["request_id"] == request_id


def test_completed_log_follows_the_field_contract(json_logging, capsys):
    with TestClient(_build_app()) as client:
        client.get("/ok")

    (record,) = _completed(_read_logs(capsys))
    for key in ("timestamp", "level", "event", "logger", "service", "environment"):
        assert key in record
    assert record["level"] == "INFO"
    assert record["method"] == "GET"
    assert record["path"] == "/ok"
    assert record["status_code"] == 200
    assert isinstance(record["duration_ms"], int | float) and record["duration_ms"] >= 0


def test_valid_client_request_id_is_reused(json_logging, capsys):
    with TestClient(_build_app()) as client:
        response = client.get("/ok", headers={"X-Request-ID": "client-id_1.2"})

    assert response.headers["x-request-id"] == "client-id_1.2"
    (record,) = _completed(_read_logs(capsys))
    assert record["request_id"] == "client-id_1.2"


@pytest.mark.parametrize("incoming", ["a b", "a;b", "x" * 129])
def test_invalid_client_request_id_is_replaced_by_uuid4(json_logging, capsys, incoming):
    with TestClient(_build_app()) as client:
        response = client.get("/ok", headers={"X-Request-ID": incoming})

    returned = response.headers["x-request-id"]
    assert returned != incoming
    assert uuid.UUID(returned).version == 4
    (record,) = _completed(_read_logs(capsys))
    assert record["request_id"] == returned


def test_context_does_not_leak_between_requests(json_logging, capsys):
    # Prova fraca por natureza (TestClient não reproduz as tasks por request do uvicorn),
    # mas pega um clear/bind errado.
    with TestClient(_build_app()) as client:
        client.get("/ok", headers={"X-Request-ID": "first-req"})
        second = client.get("/ok-sync")

    second_id = second.headers["x-request-id"]
    ids = [r["request_id"] for r in _read_logs(capsys)]
    assert ids == ["first-req", "first-req", second_id, second_id]


def test_preflight_gets_request_id_header(json_logging, capsys):
    # Prova a ordem de registro: o request id é mais externo que o CORS.
    with TestClient(_build_app()) as client:
        response = client.options(
            "/ok", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"}
        )

    assert response.status_code == 200
    (record,) = _completed(_read_logs(capsys))
    assert record["method"] == "OPTIONS"
    assert record["request_id"] == response.headers["x-request-id"]


def test_cors_exposes_request_id_header(json_logging):
    with TestClient(_build_app()) as client:
        response = client.get("/ok", headers={"Origin": ORIGIN})

    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_path_excludes_query_string(json_logging, capsys):
    with TestClient(_build_app()) as client:
        client.get("/ok", params={"token": "segredo"})

    records = _read_logs(capsys)
    assert _completed(records)[0]["path"] == "/ok"
    assert "segredo" not in json.dumps(records)


@pytest.mark.parametrize("path", ["/user-async", "/user-sync"])
def test_user_id_is_logged_when_present(json_logging, capsys, path):
    with TestClient(_build_app()) as client:
        client.get(path)

    (record,) = _completed(_read_logs(capsys))
    assert record["user_id"] == "u-123"


def test_user_id_is_omitted_when_absent(json_logging, capsys):
    with TestClient(_build_app()) as client:
        client.get("/ok")

    (record,) = _completed(_read_logs(capsys))
    assert "user_id" not in record


def test_duration_is_measured_until_last_body_not_until_background_tasks(json_logging, capsys):
    with TestClient(_build_app()) as client:
        client.get("/bg")  # a BackgroundTask dorme 300 ms

    (record,) = _completed(_read_logs(capsys))
    assert 0 <= record["duration_ms"] < 200


def test_unhandled_error_logs_completed_once_with_status_500(json_logging, capsys):
    # raise_server_exceptions=False: o Starlette re-levanta a exceção depois do handler de 500.
    # O header X-Request-ID desse caso é tema do handler de Exception (commit seguinte).
    with TestClient(_build_app(), raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    completed = _completed(_read_logs(capsys))
    assert len(completed) == 1
    assert completed[0]["status_code"] == 500
    assert completed[0]["request_id"]


def test_endpoint_own_request_id_header_is_not_duplicated(json_logging, capsys):
    with TestClient(_build_app()) as client:
        response = client.get("/own-header")

    values = response.headers.get_list("x-request-id")
    (record,) = _completed(_read_logs(capsys))
    assert values == [record["request_id"]]
    assert values != ["from-endpoint"]


def test_sentry_tag_is_set_with_request_id(json_logging, monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        middleware_module.sentry_sdk, "set_tag", lambda key, value: calls.append((key, value))
    )
    with TestClient(_build_app()) as client:
        response = client.get("/ok")

    assert calls == [("request_id", response.headers["x-request-id"])]


def test_response_start_without_headers_is_tolerated(json_logging):
    async def headerless_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200})  # sem a chave "headers"
        await send({"type": "http.response.body", "body": b"x"})

    response = TestClient(RequestIdMiddleware(headerless_app)).get("/")

    assert response.status_code == 200
    assert "x-request-id" in response.headers


async def test_non_http_scope_passes_through_untouched():
    seen: list[dict[str, Any]] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(dict(scope))

    async def noop_receive() -> dict[str, Any]:
        return {}

    async def noop_send(message: dict[str, Any]) -> None:
        return None

    await RequestIdMiddleware(inner)({"type": "lifespan"}, noop_receive, noop_send)

    assert seen == [{"type": "lifespan"}]  # nada foi adicionado ao scope (sem "state")