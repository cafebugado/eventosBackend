import logging
import sys

import pytest
import sentry_sdk

from app.core import telemetry
from app.core.config import settings


@pytest.fixture
def init_calls(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    return calls


def test_setup_sentry_inits_with_environment_and_sample_rate(init_calls, monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@example.invalid/1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "preview")

    telemetry.setup_sentry()

    assert init_calls == [
        {
            "dsn": "https://key@example.invalid/1",
            "environment": "preview",
            "traces_sample_rate": 0.1,
        }
    ]


def test_setup_sentry_does_nothing_without_dsn(init_calls, monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", "")

    telemetry.setup_sentry()

    assert init_calls == []


def test_setup_sentry_warns_when_sdk_is_missing(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@example.invalid/1")
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)  # `import sentry_sdk` passa a levantar ImportError

    with caplog.at_level(logging.WARNING):
        telemetry.setup_sentry()

    assert "sentry_sdk nao instalado" in caplog.text