import asyncio
import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from supabase_auth.errors import AuthApiError
from supabase_auth.types import CodeExchangeParams, SignInWithOAuthCredentials

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import CurrentUser
from app.integrations.supabase_storage import get_storage_client
from app.rbac.roles import Role
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthUser,
    LoginResponse,
    OAuthCallbackRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.services.role_service import RoleService
from app.utils.social import normalize_github, normalize_linkedin

logger = logging.getLogger(__name__)

_OAUTH_PROVIDERS = {"github", "google"}


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

        user_id = uuid.UUID(result.user.id)
        role_service = RoleService(self.db)
        role = await role_service.get_user_role(user_id)
        profile = await UserRepository(self.db).get_profile(user_id)

        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=AuthUser(
                id=user_id,
                email=result.user.email,
                role=role,
                provider=profile.provider if profile else "email",
            ),
        )

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        client = get_storage_client()

        github_username = normalize_github(data.github)
        linkedin_username = normalize_linkedin(data.linkedin)

        try:
            sign_up_result = await asyncio.to_thread(
                client.auth.sign_up,
                {
                    "email": data.email,
                    "password": data.senha,
                    "options": {
                        "data": {
                            "nome": data.nome,
                            "sobrenome": data.sobrenome,
                        }
                    },
                },
            )
        except AuthApiError as exc:
            msg = str(exc).lower()
            if "already registered" in msg or "email already" in msg or "already exists" in msg:
                raise ConflictError("Este email ja esta cadastrado") from exc
            raise ValidationAppError(str(exc)) from exc

        if sign_up_result.user is None:
            raise ConflictError("Este email ja esta cadastrado")

        user_id = uuid.UUID(sign_up_result.user.id)

        repo = UserRepository(self.db)
        try:
            await repo.upsert_profile(
                user_id,
                {
                    "nome": data.nome,
                    "sobrenome": data.sobrenome,
                    "github_username": github_username,
                    "linkedin_url": linkedin_username,
                    "data_nascimento": data.data_nascimento,
                    "provider": "email",
                },
            )
            await repo.upsert_role(user_id, Role.PARTICIPANTE)
        except SQLAlchemyError as exc:
            logger.exception("Erro ao salvar perfil do usuario %s no banco", user_id)
            raise AppError("Erro ao salvar perfil. Tente novamente mais tarde.") from exc

        # Tenta login imediato — funciona quando confirmacao de email esta desabilitada
        try:
            login_result = await asyncio.to_thread(
                client.auth.sign_in_with_password,
                {"email": data.email, "password": data.senha},
            )
            session = login_result.session
        except AuthApiError:
            session = None

        if session is None:
            return RegisterResponse(
                confirmacao_pendente=True,
                mensagem=(
                    "Conta criada com sucesso. Verifique seu email para "
                    "confirmar o cadastro antes de fazer login."
                ),
            )

        return RegisterResponse(
            confirmacao_pendente=False,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=AuthUser(id=user_id, email=data.email, role=Role.PARTICIPANTE, provider="email"),
        )

    async def start_oauth(self, provider: str) -> str:
        if provider not in _OAUTH_PROVIDERS:
            raise ValidationAppError(f"Provider '{provider}' nao suportado. Use: github, google")

        client = get_storage_client()
        payload: SignInWithOAuthCredentials = {"provider": provider}  # type: ignore[typeddict-item]
        if settings.OAUTH_REDIRECT_URL:
            payload["options"] = {"redirect_to": settings.OAUTH_REDIRECT_URL}
        result = await asyncio.to_thread(client.auth.sign_in_with_oauth, payload)
        return result.url

    async def oauth_callback(self, data: OAuthCallbackRequest) -> LoginResponse:
        client = get_storage_client()
        params: CodeExchangeParams = {
            "auth_code": data.code,
            "code_verifier": "",
            "redirect_to": settings.OAUTH_REDIRECT_URL,
        }
        try:
            result = await asyncio.to_thread(client.auth.exchange_code_for_session, params)
        except AuthApiError as exc:
            raise UnauthorizedError("Codigo OAuth invalido ou expirado") from exc

        session = result.session
        if session is None or result.user is None:
            raise UnauthorizedError("Falha ao obter sessao OAuth")

        user_id = uuid.UUID(result.user.id)
        user_meta = result.user.user_metadata or {}
        app_meta = result.user.app_metadata or {}
        provider = app_meta.get("provider") or data.provider

        repo = UserRepository(self.db)
        existing_role = await repo.get_role(user_id)
        profile_updates: dict = {"provider": provider}

        if existing_role is None:
            await repo.upsert_role(user_id, Role.PARTICIPANTE)
            role = Role.PARTICIPANTE

            # Salva dados basicos do perfil vindos do provider social
            nome = user_meta.get("full_name", user_meta.get("name", ""))
            avatar_url = user_meta.get("avatar_url", user_meta.get("picture", ""))
            if nome:
                parts = nome.split(" ", 1)
                profile_updates["nome"] = parts[0]
                profile_updates["sobrenome"] = parts[1] if len(parts) > 1 else None
            if avatar_url:
                profile_updates["avatar_url"] = avatar_url
        else:
            role = existing_role.role

        await repo.upsert_profile(user_id, profile_updates)

        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user=AuthUser(
                id=user_id,
                email=result.user.email,
                role=role,
                provider=provider,
            ),
        )

    async def get_me(self, current_user: CurrentUser) -> AuthUser:
        user_id = uuid.UUID(current_user.id)
        role_service = RoleService(self.db)
        role = await role_service.get_user_role(user_id)
        profile = await role_service.get_my_profile(user_id)
        return AuthUser(
            id=user_id,
            email=current_user.email,
            role=role,
            provider=profile.provider if profile else None,
        )

    async def update_password(
        self, current_user: CurrentUser, senha_atual: str, nova_senha: str
    ) -> None:
        if not current_user.email:
            raise ValidationAppError("Usuario sem email cadastrado")

        client = get_storage_client()
        try:
            await asyncio.to_thread(
                client.auth.sign_in_with_password,
                {"email": current_user.email, "password": senha_atual},
            )
        except AuthApiError as exc:
            raise UnauthorizedError("Senha atual incorreta") from exc

        await asyncio.to_thread(
            client.auth.admin.update_user_by_id,
            current_user.id,
            {"password": nova_senha},
        )

    async def request_password_reset(self, email: str) -> None:
        client = get_storage_client()
        try:
            await asyncio.to_thread(client.auth.reset_password_for_email, email)
        except AuthApiError:
            # Nao revela se o email existe ou nao, para evitar enumeracao de contas
            logger.warning("Falha ao solicitar reset de senha para %s", email)
