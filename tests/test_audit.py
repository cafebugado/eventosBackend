import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.rbac.roles import Role
from tests.conftest import make_token, set_user_role

pytestmark = pytest.mark.asyncio


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def admin_token(db_session: AsyncSession) -> str:
    token, user_id = make_token()
    await set_user_role(db_session, user_id, Role.ADMIN)
    return token


async def create_audit_log(
    db_session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    action: str = "INSERT",
    entity: str = "eventos",
    entity_id: str = "123",
    created_at: datetime | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        changes={"nome": "Evento de teste"},
        created_at=created_at or datetime.now(UTC),
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


async def test_list_audit_logs_requires_admin(client: AsyncClient):
    token, _ = make_token()

    response = await client.get(
        "/audit-logs", headers=auth_headers(token)
    )

    assert response.status_code == 403


async def test_list_audit_logs_as_admin(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(db_session)

    response = await client.get(
        "/audit-logs", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["action"] == "INSERT"
    assert body["items"][0]["entity"] == "eventos"
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_list_audit_logs_filters_by_action(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(db_session, action="INSERT")
    await create_audit_log(db_session, action="DELETE", entity_id="456")

    response = await client.get(
        "/audit-logs",
        params={"action": "DELETE"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "DELETE"


async def test_list_audit_logs_filters_by_entity(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(db_session, entity="eventos")
    await create_audit_log(
        db_session, entity="usuarios", entity_id="456"
    )

    response = await client.get(
        "/audit-logs",
        params={"entity": "usuarios"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["entity"] == "usuarios"


async def test_list_audit_logs_filters_by_user(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    target_user_id = uuid.uuid4()
    await create_audit_log(db_session, user_id=target_user_id)
    await create_audit_log(db_session, user_id=uuid.uuid4(), entity_id="456")

    response = await client.get(
        "/audit-logs",
        params={"user_id": str(target_user_id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == str(target_user_id)


async def test_list_audit_logs_filters_by_date(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(
        db_session,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    await create_audit_log(
        db_session,
        entity_id="456",
        created_at=datetime(2025, 2, 1, tzinfo=UTC),
    )

    response = await client.get(
        "/audit-logs",
        params={"date_from": "2025-01-15T00:00:00Z"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_id"] == "456"


async def test_list_audit_logs_pagination(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(db_session, entity_id="1")
    await create_audit_log(db_session, entity_id="2")
    await create_audit_log(db_session, entity_id="3")

    response = await client.get(
        "/audit-logs",
        params={"page": 2, "page_size": 2},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert len(body["items"]) == 1


async def test_list_audit_users_requires_admin(client: AsyncClient):
    token, _ = make_token()

    response = await client.get(
        "/audit-logs/users", headers=auth_headers(token)
    )

    assert response.status_code == 403


async def test_list_audit_users_as_admin(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(db_session, user_id=uuid.uuid4())

    response = await client.get(
        "/audit-logs/users", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert "user_id" in response.json()[0]


async def test_list_audit_logs_filters_by_date_to(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)
    await create_audit_log(
        db_session,
        entity_id="1",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    await create_audit_log(
        db_session,
        entity_id="2",
        created_at=datetime(2025, 2, 1, tzinfo=UTC),
    )

    response = await client.get(
        "/audit-logs",
        params={"date_to": "2025-01-15T00:00:00Z"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_id"] == "1"


async def test_list_audit_logs_orders_by_created_at_desc(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    await create_audit_log(
        db_session,
        entity_id="1",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    await create_audit_log(
        db_session,
        entity_id="2",
        created_at=datetime(2025, 3, 1, tzinfo=UTC),
    )
    await create_audit_log(
        db_session,
        entity_id="3",
        created_at=datetime(2025, 2, 1, tzinfo=UTC),
    )

    response = await client.get(
        "/audit-logs",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["entity_id"] for item in items] == ["2", "3", "1"]


async def test_list_audit_logs_returns_empty_page(
    client: AsyncClient, db_session: AsyncSession
):
    token = await admin_token(db_session)

    response = await client.get(
        "/audit-logs",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1
    assert body["page_size"] == 20
