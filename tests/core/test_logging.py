import json
import logging

import structlog

from app.core.logging import HANDLER_NAME, setup_logging


def _lines(capsys) -> list[dict]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_stdlib_e_structlog_saem_em_json(json_logging, capsys):
    structlog.contextvars.bind_contextvars(request_id="abc-123")

    logging.getLogger("x.stdlib").info("via stdlib", extra={"foo": "bar"})
    structlog.get_logger("x.structlog").info("via structlog", foo="bar")

    stdlib_log, structlog_log = _lines(capsys)
    for entry in (stdlib_log, structlog_log):
        assert entry["request_id"] == "abc-123"
        assert entry["foo"] == "bar"
        assert entry["level"] == "INFO"
        assert entry["service"] == "svc-teste"
        assert entry["environment"] == "preview"
        assert "timestamp" in entry
    assert stdlib_log["logger"] == "x.stdlib"
    assert structlog_log["logger"] == "x.structlog"


def test_excecao_sai_com_traceback(json_logging, capsys):
    try:
        raise ValueError("algo deu errado")
    except ValueError:
        logging.getLogger("x").exception("falhou")
        structlog.get_logger("y").exception("falhou")

    entries = _lines(capsys)

    assert len(entries) == 2

    for entry in entries:
        assert entry["level"] == "ERROR"
        assert "ValueError: algo deu errado" in entry["exception"]


def test_setup_logging_idempotente(json_logging):
    setup_logging("INFO")
    ours = [h for h in logging.getLogger().handlers if h.get_name() == HANDLER_NAME]
    assert len(ours) == 1
