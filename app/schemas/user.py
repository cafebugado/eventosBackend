import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.rbac.roles import Role
from app.utils.validators import validar_idade_minima

GeneroOpcao = Literal["Masculino", "Feminino", "Outro", "Prefiro não informar"]
NivelExperienciaOpcao = Literal["Estagiário", "Júnior", "Pleno", "Sênior", "Especialista/Staff"]


class UserRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: Role
    created_at: datetime
    updated_at: datetime
    nome: str | None = None
    sobrenome: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class CurrentUserRole(BaseModel):
    role: Role


class UserWithRole(BaseModel):
    user_id: uuid.UUID
    email: str | None = None
    role: Role | None = None


class AssignRoleRequest(BaseModel):
    role: Role


class UserProfileBase(BaseModel):
    nome: str | None = None
    sobrenome: str | None = None
    github_username: str | None = None
    linkedin_url: str | None = None
    avatar_url: str | None = None
    data_nascimento: date | None = None
    genero: GeneroOpcao | None = None
    whatsapp: str | None = None
    cargo_atual: str | None = None
    empresa: str | None = None
    area_atuacao: str | None = None
    nivel_experiencia: NivelExperienciaOpcao | None = None
    portfolio_url: str | None = None
    bio: str | None = None

    @field_validator("data_nascimento")
    @classmethod
    def idade_minima(cls, v: date | None) -> date | None:
        return validar_idade_minima(v)


class UserProfileUpsert(UserProfileBase):
    pass


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    provider: str | None = None
    updated_at: datetime
