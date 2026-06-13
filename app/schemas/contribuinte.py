import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
_LINKEDIN_URL_RE = re.compile(r"^https://(www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?$")
_PORTFOLIO_URL_RE = re.compile(r"^https?://.+")


def is_valid_github_username(username: str) -> bool:
    return bool(_GITHUB_USERNAME_RE.match(username))


def is_valid_linkedin_url(url: str) -> bool:
    return bool(_LINKEDIN_URL_RE.match(url))


def is_valid_portfolio_url(url: str) -> bool:
    return bool(_PORTFOLIO_URL_RE.match(url))


class ContribuinteBase(BaseModel):
    github_username: str
    nome: str
    avatar_url: str
    github_url: str
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("github_username")
    @classmethod
    def validate_github_username(cls, value: str) -> str:
        if not is_valid_github_username(value):
            raise ValueError("github_username invalido")
        return value

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_linkedin_url(value):
            raise ValueError("linkedin_url invalido")
        return value

    @field_validator("portfolio_url")
    @classmethod
    def validate_portfolio_url(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_portfolio_url(value):
            raise ValueError("portfolio_url invalido")
        return value


class ContribuinteCreate(ContribuinteBase):
    pass


class ContribuinteUpdate(BaseModel):
    github_username: str | None = None
    nome: str | None = None
    avatar_url: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("github_username")
    @classmethod
    def validate_github_username(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_github_username(value):
            raise ValueError("github_username invalido")
        return value

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_linkedin_url(value):
            raise ValueError("linkedin_url invalido")
        return value

    @field_validator("portfolio_url")
    @classmethod
    def validate_portfolio_url(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_portfolio_url(value):
            raise ValueError("portfolio_url invalido")
        return value


class ContribuinteRead(ContribuinteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GitHubUserInfo(BaseModel):
    github_username: str
    nome: str
    avatar_url: str
    github_url: str
