import uuid
from collections.abc import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user_role import UserRole
from app.rbac.roles import Role

TEST_JWT_SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _set_jwt_secret():
    settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def make_token(user_id: str | None = None, email: str = "user@example.com") -> tuple[str, str]:
    user_id = user_id or str(uuid.uuid4())
    payload = {"sub": user_id, "email": email, "aud": "authenticated"}
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return token, user_id


async def set_user_role(db_session: AsyncSession, user_id: str, role: Role) -> None:
    db_session.add(UserRole(user_id=uuid.UUID(user_id), role=role))
    await db_session.commit()
