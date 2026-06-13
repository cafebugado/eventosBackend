from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import AuthUser, LoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.get("/me", response_model=AuthUser)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    service = AuthService(db)
    return await service.get_me(current_user)
