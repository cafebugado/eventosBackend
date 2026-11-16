from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from supabase_auth.errors import AuthApiError

from app.core.exceptions import UnauthorizedError
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.rbac.roles import Role

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient):
    user_id = str(uuid4())

    supabase_response = {
        "access_token": "fake_access_token",
        "refresh_token": "fake-refresh-token",
        "expires_in": 3600,
        "user": {
            "id": user_id,
            "email": "usuario@example.com",
        },
    }

    with (
        patch(
            "app.services.auth_service.sign_in_with_password",
            new_callable=AsyncMock,
            return_value=supabase_response,
        ),
        patch(
            "app.repositories.user_repository.UserRepository.get_role_and_profile",
            new_callable=AsyncMock,
            return_value=(None, None),    
        ),
    ):
        response = await client.post(
            "/auth/login",
            json={
                "email": "usuario@example.com",
                "password": "senha123",
            },
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "fake_access_token"
    assert response.json()["user"]["id"] == user_id
    assert response.json()["user"]["email"] == "usuario@example.com"


async def test_login_invalid_credentials(client: AsyncClient):
    with patch(
        "app.services.auth_service.sign_in_with_password",
        new_callable=AsyncMock,
        side_effect=UnauthorizedError("Credenciais invalidas"),
    ):
        response = await client.post(
            "/auth/login",
            json={
                "email": "usuario@example.com",
                "password": "senha-errada",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais invalidas"


async def test_register_email_confirmation_pending(
    client: AsyncClient,
    db_session,
):
    user_id = str(uuid4())

    fake_user = type("FakeUser", (), {"id": user_id})()
    fake_sign_up_result = type("FakeSignUpResult", (), {"user": fake_user})()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, data: fake_sign_up_result,
            "sign_in_with_password": lambda self, data: type(
                "FakeLoginResult",
                (),
                {"session": None},
            )(),
        },
    )()

    fake_supabase = type("FakeSupabase", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_supabase,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_profile",
            new_callable=AsyncMock,
        ) as mock_profile,
        patch(
            "app.services.auth_service.UserRepository.upsert_role",
            new_callable=AsyncMock,
        ) as mock_role,
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 201
    assert response.json()["confirmacao_pendente"] is True
    assert response.json()["access_token"] is None
    mock_profile.assert_awaited_once()
    mock_role.assert_awaited_once()


async def test_register_success_with_session(client: AsyncClient):
    user_id = str(uuid4())

    fake_user = type("FakeUser", (), {"id": user_id})()
    fake_sign_up_result = type("FakeSignUpResult", (), {"user": fake_user})()

    fake_session = type(
        "FakeSession",
        (),
        {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
        },
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, data: fake_sign_up_result,
            "sign_in_with_password": lambda self, data: type(
                "FakeLoginResult",
                (),
                {"session": fake_session},
            )(),
        },
    )()

    fake_supabase = type("FakeSupabase", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_supabase,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_profile",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_role",
            new_callable=AsyncMock,
        ),
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 201
    assert response.json()["confirmacao_pendente"] is False
    assert response.json()["access_token"] == "fake-access-token"
    assert response.json()["refresh_token"] == "fake-refresh-token"
    assert response.json()["user"]["id"] == user_id
    assert response.json()["user"]["role"] == "participante"


async def test_register_email_already_exists(client):
    from supabase_auth.errors import AuthApiError

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, payload: (_ for _ in ()).throw(
                AuthApiError("User already registered", 422, None)
            )
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Este email ja esta cadastrado"


async def test_oauth_callback_success_new_user(client):
    user_id = str(uuid4())

    fake_session = type(
        "FakeSession",
        (),
        {
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "expires_in": 3600,
        },
    )()

    fake_user = type(
        "FakeUser",
        (),
        {
            "id": user_id,
            "email": "ingrid@example.com",
            "user_metadata": {
                "full_name": "Ingrid Xisto",
                "avatar_url": "https://example.com/avatar.png",
            },
            "app_metadata": {"provider": "github"},
        },
    )()

    fake_result = type(
        "FakeOAuthResult",
        (),
        {
            "session": fake_session,
            "user": fake_user,
        },
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "exchange_code_for_session": lambda self, payload: fake_result,
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ),
        patch(
            "app.repositories.user_repository.UserRepository.get_role",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.repositories.user_repository.UserRepository.upsert_role",
            new_callable=AsyncMock,
        ) as mock_upsert_role,
        patch(
            "app.repositories.user_repository.UserRepository.upsert_profile",
            new_callable=AsyncMock,
        ) as mock_upsert_profile,
    ):
        response = await client.post(
            "/auth/oauth/callback",
            json={
                "code": "fake-oauth-code",
                "provider": "github",
            },
        )

    assert response.status_code == 200
    assert response.json()["access_token"] == "oauth-access-token"
    assert response.json()["refresh_token"] == "oauth-refresh-token"
    assert response.json()["user"]["id"] == user_id
    assert response.json()["user"]["provider"] == "github"
    assert response.json()["user"]["role"] == "participante"

    mock_upsert_role.assert_awaited_once()
    mock_upsert_profile.assert_awaited_once()


async def test_oauth_callback_invalid_code(client):
    fake_auth = type(
        "FakeAuth",
        (),
        {
            "exchange_code_for_session": lambda self, payload: (_ for _ in ()).throw(
                AuthApiError("Invalid OAuth code", 400, None)
            )
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/oauth/callback",
            json={
                "code": "invalid-code",
                "provider": "github",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Codigo OAuth invalido ou expirado"


async def test_oauth_callback_without_session(client):
    fake_result = type(
        "FakeOAuthResult",
        (),
        {
            "session": None,
            "user": None,
        },
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "exchange_code_for_session": lambda self, payload: fake_result,
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/oauth/callback",
            json={
                "code": "valid-code",
                "provider": "github",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Falha ao obter sessao OAuth"


async def test_oauth_callback_existing_user(client):
    user_id = str(uuid4())

    fake_session = type(
        "FakeSession",
        (),
        {
            "access_token": "existing-access-token",
            "refresh_token": "existing-refresh-token",
            "expires_in": 3600,
        },
    )()

    fake_user = type(
        "FakeUser",
        (),
        {
            "id": user_id,
            "email": "ingrid@example.com",
            "user_metadata": {},
            "app_metadata": {},
        },
    )()

    fake_result = type(
        "FakeOAuthResult",
        (),
        {
            "session": fake_session,
            "user": fake_user,
        },
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "exchange_code_for_session": lambda self, payload: fake_result,
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    existing_role = type(
        "FakeRole",
        (),
        {"role": Role.PARTICIPANTE},
    )()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ),
        patch(
            "app.repositories.user_repository.UserRepository.get_role",
            new_callable=AsyncMock,
            return_value=existing_role,
        ),
        patch(
            "app.repositories.user_repository.UserRepository.upsert_role",
            new_callable=AsyncMock,
        ) as mock_upsert_role,
        patch(
            "app.repositories.user_repository.UserRepository.upsert_profile",
            new_callable=AsyncMock,
        ) as mock_upsert_profile,
    ):
        response = await client.post(
            "/auth/oauth/callback",
            json={
                "code": "existing-user-code",
                "provider": "google",
            },
        )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == user_id
    assert response.json()["user"]["role"] == "participante"
    assert response.json()["user"]["provider"] == "google"

    mock_upsert_role.assert_not_awaited()
    mock_upsert_profile.assert_awaited_once_with(
        UUID(user_id),
        {"provider": "google"},
    )


async def test_oauth_start_invalid_provider(client):
    response = await client.get("/auth/oauth/facebook")

    assert response.status_code == 422
    assert "nao suportado" in response.json()["detail"]


async def test_oauth_start_success(client):
    fake_result = type(
        "FakeOAuthResult",
        (),
        {"url": "https://github.com/login/oauth/authorize?client_id=test"},
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_in_with_oauth": lambda self, payload: fake_result,
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ),
        patch(
            "app.services.auth_service.settings.OAUTH_REDIRECT_URL",
            "",
        ),
    ):
        response = await client.get("/auth/oauth/github")

    assert response.status_code == 200
    assert response.json()["url"] == (
        "https://github.com/login/oauth/authorize?client_id=test"
    )


async def test_oauth_start_with_redirect_url(client):
    fake_result = type(
        "FakeOAuthResult",
        (),
        {"url": "https://accounts.google.com/o/oauth2/auth?client_id=test"},
    )()

    def fake_sign_in_with_oauth(self, payload):
        assert payload["provider"] == "google"
        assert payload["options"]["redirect_to"] == "https://example.com/callback"
        return fake_result

    fake_auth = type(
        "FakeAuth",
        (),
        {"sign_in_with_oauth": fake_sign_in_with_oauth},
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ),
        patch(
            "app.services.auth_service.settings.OAUTH_REDIRECT_URL",
            "https://example.com/callback",
        ),
    ):
        response = await client.get("/auth/oauth/google")

    assert response.status_code == 200
    assert response.json()["url"] == (
        "https://accounts.google.com/o/oauth2/auth?client_id=test"
    )


async def test_get_me_success(client):
    user_id = str(uuid4())

    fake_profile = type("FakeProfile", (), {"provider": "github"},)()

    async def fake_get_current_user():
        return CurrentUser(
            id=user_id,
            email="ingrid@example.com",
        )

    app.dependency_overrides[get_current_user] = fake_get_current_user

    try:
        with (
            patch(
                "app.services.auth_service.RoleService.get_user_role",
                new_callable=AsyncMock,
                return_value=Role.PARTICIPANTE,
            ),
            patch(
                "app.services.auth_service.RoleService.get_my_profile",
                new_callable=AsyncMock,
                return_value=fake_profile,
            ),
        ):
            response = await client.get("/auth/me")

    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["email"] == "ingrid@example.com"
    assert response.json()["role"] == "participante"
    assert response.json()["provider"] == "github"


async def test_update_password_success(client):
    user_id = str(uuid4())

    fake_client = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=MagicMock(return_value={"user": {"id": user_id}}),
            admin=SimpleNamespace(
                update_user_by_id=MagicMock(return_value=None)
            ),
        )
    )

    async def fake_get_current_user():
        return CurrentUser(
            id=user_id,
            email="ingrid@example.com",
        )

    app.dependency_overrides[get_current_user] = fake_get_current_user

    try:
        with patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ):
            response = await client.post(
                "/auth/update-password",
                json={
                    "senha_atual": "senha-antiga",
                    "nova_senha": "senha-nova-segura",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 204

    fake_client.auth.sign_in_with_password.assert_called_once_with(
        {
            "email": "ingrid@example.com",
            "password": "senha-antiga",
        }
    )

    fake_client.auth.admin.update_user_by_id.assert_called_once_with(
        user_id,
        {"password": "senha-nova-segura"},
    )


async def test_update_password_without_email(client):
    user_id = str(uuid4())

    async def fake_get_current_user():
        return CurrentUser(
            id=user_id,
            email=None,
        )

    app.dependency_overrides[get_current_user] = fake_get_current_user

    try:
        response = await client.post(
            "/auth/update-password",
            json={
                "senha_atual": "senha-antiga",
                "nova_senha": "senha-nova-segura",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    assert response.json()["detail"] == "Usuario sem email cadastrado"


async def test_update_password_invalid_current_password(client):
    user_id = str(uuid4())

    fake_client = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=MagicMock(
                side_effect=AuthApiError("Invalid login credentials", 400, None)
            ),
            admin=SimpleNamespace(
                update_user_by_id=MagicMock(),
            ),
        )
    )

    async def fake_get_current_user():
        return CurrentUser(
            id=user_id,
            email="ingrid@example.com",
        )

    app.dependency_overrides[get_current_user] = fake_get_current_user

    try:
        with patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_client,
        ):
            response = await client.post(
                "/auth/update-password",
                json={
                    "senha_atual": "senha-incorreta",
                    "nova_senha": "senha-nova-segura",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 401
    assert response.json()["detail"] == "Senha atual incorreta"

    fake_client.auth.admin.update_user_by_id.assert_not_called()


async def test_reset_password_success(client):
    fake_client = SimpleNamespace(
        auth=SimpleNamespace(
            reset_password_for_email=MagicMock(return_value=None)
        )
    )

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/reset-password",
            json={"email": "ingrid@example.com"},
        )

    assert response.status_code == 204

    fake_client.auth.reset_password_for_email.assert_called_once_with(
        "ingrid@example.com"
    )


async def test_reset_password_supabase_error(client):
    fake_client = SimpleNamespace(
        auth=SimpleNamespace(
            reset_password_for_email=MagicMock(
                side_effect=AuthApiError("User not found", 404, None)
            )
        )
    )

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/reset-password",
            json={"email": "ingrid@example.com"},
        )

    assert response.status_code == 204

    fake_client.auth.reset_password_for_email.assert_called_once_with(
        "ingrid@example.com"
    )


async def test_login_without_access_token(client):
    with (
        patch(
            "app.services.auth_service.sign_in_with_password",
            new_callable=AsyncMock,
            return_value={
                "access_token": None,
                "user": {"id": str(uuid4())},
            },
        ),
    ):
        response = await client.post(
            "/auth/login",
            json={
                "email": "ingrid@example.com",
                "password": "senha-teste",
            },
        )

    assert response.status_code == 401


async def test_register_auth_error(client):
    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, payload: (
                (_ for _ in ()). throw(
                    AuthApiError("Invalid signup request", 400, None)
                )
            )
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid signup request"


async def test_register_without_user_returned(client):
    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, payload: SimpleNamespace(user=None)
        },
    )()

    fake_client = type("FakeClient", (), {"auth": fake_auth})()

    with patch(
        "app.services.auth_service.get_supabase_client",
        return_value=fake_client,
    ):
        response = await client.post(
            "auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 409


async def test_register_database_error(client):
    from sqlalchemy.exc import SQLAlchemyError

    user_id = str(uuid4())

    fake_user = type("FakeUser", (), {"id": user_id})()
    fake_sign_up_result = type(
        "FakeSignUpResult", (), {"user": fake_user}
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, payload: fake_sign_up_result,
        },
    )()

    fake_supabase = type("FakeSupabase", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_supabase,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_profile",
            new_callable=AsyncMock,
            side_effect=SQLAlchemyError("Erro simulado no banco"),
        ) as mock_upsert_profile,
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Erro ao salvar perfil. Tente novamente mais tarde."
    )
    mock_upsert_profile.assert_awaited_once()


async def test_register_login_error_requires_email_confirmation(client):
    from supabase_auth.errors import AuthApiError

    user_id = str(uuid4())

    fake_user = type("FakeUser", (), {"id": user_id})()
    fake_sign_up_result = type(
        "FakeSignUpResult", (), {"user": fake_user}
    )()

    fake_auth = type(
        "FakeAuth",
        (),
        {
            "sign_up": lambda self, payload: fake_sign_up_result,
            "sign_in_with_password": lambda self, payload: (
                (_ for _ in ()).throw(
                    AuthApiError("Email not confirmed", 400, None)
                )
            ),
        },
    )()

    fake_supabase = type("FakeSupabase", (), {"auth": fake_auth})()

    with (
        patch(
            "app.services.auth_service.get_supabase_client",
            return_value=fake_supabase,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_profile",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.auth_service.UserRepository.upsert_role",
            new_callable=AsyncMock,
        ),
    ):
        response = await client.post(
            "/auth/register",
            json={
                "nome": "Ingrid",
                "sobrenome": "Xisto",
                "email": "ingrid@example.com",
                "senha": "senha123",
                "confirma_senha": "senha123",
                "data_nascimento": "1995-05-10",
                "github": "ingridxisto",
                "linkedin": "https://www.linkedin.com/in/ingrid-xisto",
            },
        )

    assert response.status_code == 201
    assert response.json()["confirmacao_pendente"] is True
    assert "Verifique seu email" in response.json()["mensagem"]
    assert response.json().get("access_token") is None
