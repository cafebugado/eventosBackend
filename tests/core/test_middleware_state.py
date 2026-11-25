import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.middleware import REQUEST_ID_HEADER, RequestIdMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/async")
    async def read_async(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    @app.get("/sync")
    def read_sync(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    return app


@pytest.mark.parametrize("path", ["/async", "/sync"])
def test_request_state_expoe_o_mesmo_id_do_header(path: str) -> None:
    client = TestClient(_build_app())
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_request_state_usa_o_id_valido_enviado_pelo_client() -> None:
    client = TestClient(_build_app())
    response = client.get("/async", headers={REQUEST_ID_HEADER: "abc-123"})
    assert response.json()["request_id"] == "abc-123"
