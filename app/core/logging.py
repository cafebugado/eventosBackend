import logging
import sys

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from app.core.config import settings

HANDLER_NAME = "app-json-stdout"


class _DynamicStdout:
    # Resolve sys.stdout a cada escrita, e não na criação do handler.
    # Garante que o log siga o stdout atual mesmo se ele for trocado depois do
    # setup (captura do pytest, redirecionamentos do runtime).

    def write(self, message: str) -> int:
        return sys.stdout.write(message)

    def flush(self) -> None:
        sys.stdout.flush()


def _uppercase_level(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    level = event_dict.get("level")
    if isinstance(level, str):
        event_dict["level"] = level.upper()
    return event_dict


def _add_static_fields(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("service", settings.SERVICE_NAME)
    event_dict.setdefault("environment", settings.ENVIRONMENT)
    return event_dict


def setup_logging(level: int | str | None = None) -> None:
    log_level = level if level is not None else settings.LOG_LEVEL

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _uppercase_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_static_fields,
    ]

    # Caminho 1: logs nativos do structlog mas NÃO renderiza.
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Ponto ÚNICO de renderização (caminho 2 entra pela foreign_pre_chain).
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[*shared_processors, structlog.stdlib.ExtraAdder()],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,  # -> "exception"
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(_DynamicStdout())
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Idempotência: remove só o NOSSO handler de chamadas anteriores
    for h in list(root.handlers):
        if h.get_name() == HANDLER_NAME:
            root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(log_level)

    # uvicorn.access fica silenciado: o http.request.completed (middleware)
    # é a única linha de acesso, com request_id, status_code e duration_ms.
    for name in ("uvicorn", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True

    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.addHandler(logging.NullHandler())
    access.propagate = False
