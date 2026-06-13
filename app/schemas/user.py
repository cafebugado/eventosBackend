import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.rbac.roles import Role


class UserRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: Role
    created_at: datetime
    updated_at: datetime


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
    avatar_url: str | None = None


class UserProfileUpsert(UserProfileBase):
    pass


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    updated_at: datetime
