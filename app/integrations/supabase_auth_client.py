import httpx

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

_TOKEN_URL = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"


async def sign_in_with_password(email: str, password: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _TOKEN_URL,
            headers={"apikey": settings.SUPABASE_SERVICE_ROLE_KEY},
            json={"email": email, "password": password},
        )
    if response.status_code != 200:
        raise UnauthorizedError("Credenciais invalidas")
    return response.json()
