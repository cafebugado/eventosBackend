import uuid

from pydantic import BaseModel

from app.rbac.roles import Role


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: uuid.UUID
    email: str | None = None
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    user: AuthUser
