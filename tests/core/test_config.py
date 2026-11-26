import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("info", "INFO"),
        ("Info", "INFO"),
        (" info ", "INFO"),
        ("debug", "DEBUG"),
    ],
)
def test_log_level_normalization(value: str, expected: str) -> None:
    settings = Settings(
        LOG_LEVEL=value,
        ENVIRONMENT="development",
    )

    assert settings.LOG_LEVEL == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Production", "production"),
        ("PREVIEW", "preview"),
        (" DEVELOPMENT ", "development"),
    ],
)
def test_environment_normalization(value: str, expected: str) -> None:
    settings = Settings(
        LOG_LEVEL="INFO",
        ENVIRONMENT=value,
    )

    assert settings.ENVIRONMENT == expected


def test_invalid_environment_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Settings(
            LOG_LEVEL="INFO",
            ENVIRONMENT="staging",
        )


def test_invalid_log_level_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Settings(
            LOG_LEVEL="TRACE",
            ENVIRONMENT="development",
        )
