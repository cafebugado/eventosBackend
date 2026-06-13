import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from supabase_auth.errors import AuthApiError

from app.core.exceptions import UnauthorizedError
from app.core.security import CurrentUser
from app.integrations.supabase_storage import get_storage_client
from app.schemas.auth import AuthUser, LoginResponse
from app.services.role_service import RoleService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, email: str, password: str) -> LoginResponse:
        client = get_storage_client()
        try:
            result = await asyncio.to_thread(
                client.auth.sign_in_with_password,
                {"email": email, "password": password},
            )
        except AuthApiError as exc:
            raise UnauthorizedError("Credenciais invalidas") from exc

        session = result.session
        if session is None or result.user is None:
            raise UnauthorizedError("Credenciais invalidas")

        role_service = RoleService(self.db)
        role = await role_service.get_user_role(uuid.UUID(result.user.id))

        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=AuthUser(id=uuid.UUID(result.user.id), email=result.user.email, role=role),
        )

    async def get_me(self, current_user: CurrentUser) -> AuthUser:
        role_service = RoleService(self.db)
        role = await role_service.get_user_role(uuid.UUID(current_user.id))
        return AuthUser(id=uuid.UUID(current_user.id), email=current_user.email, role=role)
