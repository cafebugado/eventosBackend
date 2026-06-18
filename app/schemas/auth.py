import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from app.rbac.roles import Role
from app.utils.validators import validar_idade_minima


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    nome: str
    sobrenome: str
    email: str
    senha: str
    confirma_senha: str
    data_nascimento: date
    github: str
    linkedin: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()

    @model_validator(mode="after")
    def senhas_coincidem(self) -> "RegisterRequest":
        if self.senha != self.confirma_senha:
            raise ValueError("As senhas nao coincidem")
        return self

    @field_validator("senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres")
        return v

    @field_validator("data_nascimento")
    @classmethod
    def idade_minima(cls, v: date) -> date:
        validar_idade_minima(v)
        return v


class AuthUser(BaseModel):
    id: uuid.UUID
    email: str | None = None
    role: Role
    provider: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: AuthUser


class RegisterResponse(BaseModel):
    confirmacao_pendente: bool = False
    mensagem: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: AuthUser | None = None


class OAuthStartResponse(BaseModel):
    url: str


class OAuthCallbackRequest(BaseModel):
    code: str
    provider: Literal["github", "google"]
    state: str | None = None


class UpdatePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres")
        return v


class ResetPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()
