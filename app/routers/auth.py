from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    OAuthCallbackRequest,
    OAuthStartResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    UpdatePasswordRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    service = AuthService(db)
    return await service.register(data)


@router.get("/oauth/{provider}", response_model=OAuthStartResponse)
async def oauth_start(provider: str, db: AsyncSession = Depends(get_db)) -> OAuthStartResponse:
    service = AuthService(db)
    url = await service.start_oauth(provider)
    return OAuthStartResponse(url=url)


@router.post("/oauth/callback", response_model=LoginResponse)
async def oauth_callback(
    data: OAuthCallbackRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    service = AuthService(db)
    return await service.oauth_callback(data)


@router.get("/me", response_model=AuthUser)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    service = AuthService(db)
    return await service.get_me(current_user)


@router.post("/update-password", status_code=204)
async def update_password(
    data: UpdatePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = AuthService(db)
    await service.update_password(current_user, data.password)


@router.post("/reset-password", status_code=204)
@limiter.limit("5/minute")
async def reset_password(
    request: Request, data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> None:
    service = AuthService(db)
    await service.request_password_reset(data.email)
