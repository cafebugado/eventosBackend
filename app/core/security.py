from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str | None = None


@lru_cache
def get_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(settings.supabase_jwks_url)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError("Token de autenticacao ausente")

    token = credentials.credentials
    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise UnauthorizedError("Token invalido ou expirado") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token sem identificador de usuario")

    return CurrentUser(id=user_id, email=payload.get("email"))


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except UnauthorizedError:
        return None
