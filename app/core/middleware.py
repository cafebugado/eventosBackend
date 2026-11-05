import re
import time
import uuid
from typing import Any

import sentry_sdk
import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_HEADER_RAW = REQUEST_ID_HEADER.lower().encode("latin-1")

# ID vindo do cliente: só caracteres seguros e tamanho limitado (evita log injection e ruído).
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


def _resolve_request_id(scope: Scope) -> str:
    # Reaproveita o ID do cliente se for válido; se ausente ou inválido, gera um uuid4.
    # O ID nasce AQUI, uma vez por request. Nunca no logger, nunca em um handler.
    for name, value in scope.get("headers", []):
        if name.lower() == _REQUEST_ID_HEADER_RAW:
            candidate = value.decode("latin-1")
            if _VALID_REQUEST_ID.fullmatch(candidate):
                return candidate
            break
    return str(uuid.uuid4())
    


class RequestIdMiddleware:
    # Middleware ASGI puro: request id, contexto de log e o log `http.request.completed`.
    # Limitação conhecida (provada em spike):
    # um erro NÃO tratado vira resposta 500 no `ServerErrorMiddleware`,
    # Essa resposta não passa pelo nosso `send`,
    # então sai sem `X-Request-ID` (e sem headers de CORS).
    # O `request_id` continua no log e na tag do Sentry.
    # O header desse caso é tratado no handler de `Exception` (app/core/exceptions.py),
    # lendo `request.state.request_id`.

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # lifespan e websocket passam direto.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)
        
        # clear no INÍCIO (e não no fim): o log de erro do servidor, emitido depois que a
        # exceção atravessa este middleware, ainda herda o request_id.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope["method"],
            path=scope["path"], # sem query string, para não poluir o log com dados sensíveis
        )
        sentry_sdk.set_tag("request_id", request_id)
        # Muta o MESMO dict de scope (não copia): é o que `request.state` enxerga, inclusive
        # no handler de 500 e em dependencies síncronas (threadpool).
        scope.setdefault("state", {})[request_id] = request_id

        started = time.perf_counter()
        status_code = 500 # assumido até alguém enviar http.response.start
        logged = False

        def log_completed() -> None:
            nonlocal logged
            if logged:
                return
            logged = True
            fields: dict[str, Any] = {
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }
            # user_id é opcional: endpoints públicos não têm usuário, então o campo some.
            user_id = scope["state"].get("user_id")
            if user_id is not None:
                fields["user_id"] = user_id
            structlog.get_logger(__name__).info("http.request.completed", **fields)

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            is_last_body = message["type"] == "http.response.body" and not message.get("more_body", False)
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # 'headers' pode estar ausente na mensagem (ASGI permite). Remove um
                # X-Request-ID que o endpoint tenha posto, para nunca duplicar.
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != _REQUEST_ID_HEADER_RAW
                ]
                headers.append((_REQUEST_ID_HEADER_RAW, request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)
            if is_last_body:
                log_completed()
            
        try:
            await self.app(scope, receive, send_with_request_id)
            
        finally:
            # Cobre o 500 não tratado, em que a resposta sai por fora do nosso send,
            # e o cliente que desconecta.
            # Nesse caminho o status 500 é ASSUMIDO
            # (o handler do projeto devolve 500), não observado.
            log_completed()
                