import logging

import pytest
import structlog

from app.core.config import settings
from app.core.logging import HANDLER_NAME, setup_logging


@pytest.fixture
def json_logging(capsys, monkeypatch):
    # capsys vem ANTES: o handler captura sys.stdout na criação
    monkeypatch.setattr(settings, "SERVICE_NAME", "svc-teste")
    monkeypatch.setattr(settings, "ENVIRONMENT", "preview")
    setup_logging("INFO")
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        if h.get_name() == HANDLER_NAME:
            root.removeHandler(h)
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()
