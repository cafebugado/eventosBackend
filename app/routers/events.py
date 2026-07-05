import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_optional_user
from app.db.session import get_db
from app.models.evento import Evento
from app.rbac.permissions import get_current_user_role, get_user_role, require_permission, require_role
from app.rbac.roles import Role
from app.schemas.evento import (
    EventoCreate,
    EventoDateFilter,
    EventoPage,
    EventoRead,
    EventoRejectRequest,
    EventoStats,
    EventoStatus,
    EventoUpdate,
    EventoWithTags,
)
from app.services.evento_service import EventoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

REVIEW_ROLES = {Role.SUPER_ADMIN, Role.ADMIN}


def _serialize_events(eventos: list[Evento]) -> list[EventoRead]:
    result = []
    for evento in eventos:
        try:
            result.append(EventoRead.model_validate(evento))
        except ValidationError:
            logger.warning("Evento com dados invalidos ignorado na listagem: id=%s", evento.id)
    return result


def _is_event_owner(evento: Evento, current_user: CurrentUser | None) -> bool:
    return current_user is not None and evento.created_by == uuid.UUID(current_user.id)


def _can_view_event(
    evento: Evento,
    current_user: CurrentUser | None,
    current_role: Role | None,
) -> bool:
    if evento.status == "publicado":
        return True

    if current_role in REVIEW_ROLES:
        return True

    return _is_event_owner(evento, current_user)


async def _get_optional_role(
    current_user: CurrentUser | None,
    db: AsyncSession,
) -> Role | None:
    if current_user is None:
        return None
    return await get_user_role(current_user.id, db)


async def _ensure_participant_owns_event(
    event_id: uuid.UUID,
    current_user: CurrentUser,
    current_role: Role,
    db: AsyncSession,
) -> None:
    if current_role != Role.PARTICIPANTE:
        return

    service = EventoService(db)
    evento = await service.get_event_by_id(event_id)
    if not _is_event_owner(evento, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente para esta acao")


@router.get("", response_model=EventoPage | list[EventoRead])
async def list_events(
    limit: int | None = None,
    offset: int = 0,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    status: EventoStatus | None = Query(default=None),
    date_filter: EventoDateFilter | None = Query(default=None),
    search: str | None = Query(default=None),
    mine: bool = Query(default=False),
    current_user=Depends(require_permission("canCreateEvents")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoPage | list[EventoRead]:
    service = EventoService(db)
    created_by = uuid.UUID(current_user.id) if mine or current_role == Role.PARTICIPANTE else None
    pending_first = current_role in REVIEW_ROLES and status is None
    if (
        page is not None
        or page_size is not None
        or status is not None
        or date_filter is not None
        or search
        or mine
    ):
        resolved_page = page or 1
        resolved_page_size = page_size or limit or 20
        eventos, total = await service.get_events_page(
            page=resolved_page,
            page_size=resolved_page_size,
            status=status,
            date_filter=date_filter,
            search=search,
            created_by=created_by,
            pending_first=pending_first,
        )
        return EventoPage(
            items=_serialize_events(eventos),
            total=total,
            page=resolved_page,
            page_size=resolved_page_size,
        )

    eventos = await service.get_events(
        limit=limit,
        offset=offset,
        created_by=created_by,
        pending_first=pending_first,
    )
    return _serialize_events(eventos)


@router.get("/published", response_model=list[EventoRead])
async def list_published_events(
    limit: int | None = None, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_published_events(limit=limit, offset=offset)
    return _serialize_events(eventos)


@router.get("/upcoming", response_model=list[EventoRead])
async def list_upcoming_events(limit: int = 3, db: AsyncSession = Depends(get_db)) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_upcoming_events(limit)
    return _serialize_events(eventos)


@router.get("/stats", response_model=EventoStats)
async def get_event_stats(
    _user=Depends(require_permission("canCreateEvents")),
    db: AsyncSession = Depends(get_db),
) -> EventoStats:
    service = EventoService(db)
    return await service.get_event_stats()


@router.get("/by-period/{periodo}", response_model=list[EventoRead])
async def list_events_by_period(periodo: str, db: AsyncSession = Depends(get_db)) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_events_by_period(periodo)
    return _serialize_events(eventos)


@router.get("/slug/{slug_or_id}", response_model=EventoRead)
async def get_event_by_slug_or_id(
    slug_or_id: str,
    current_user: CurrentUser | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.get_event_by_slug_or_id(slug_or_id)
    current_role = await _get_optional_role(current_user, db)
    if not _can_view_event(evento, current_user, current_role):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento nao encontrado")
    return EventoRead.model_validate(evento)


@router.get("/{event_id}", response_model=EventoRead)
async def get_event(
    event_id: uuid.UUID,
    current_user=Depends(require_permission("canCreateEvents")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.get_event_by_id(event_id)
    if not _can_view_event(evento, current_user, current_role):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento nao encontrado")
    return EventoRead.model_validate(evento)


@router.get("/{event_id}/recommended", response_model=list[EventoWithTags])
async def get_recommended_events(
    event_id: uuid.UUID, limit: int = 3, db: AsyncSession = Depends(get_db)
) -> list[EventoWithTags]:
    service = EventoService(db)
    return await service.get_recommended_events(event_id, limit)


@router.post("", response_model=EventoRead, status_code=201)
async def create_event(
    data: EventoCreate,
    current_user=Depends(require_permission("canCreateEvents")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.create_event(
        data,
        created_by=uuid.UUID(current_user.id),
        actor_role=current_role,
    )
    return EventoRead.model_validate(evento)


@router.put("/{event_id}", response_model=EventoRead)
async def update_event(
    event_id: uuid.UUID,
    data: EventoUpdate,
    current_user=Depends(require_permission("canEditEvents")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.update_event(
        event_id,
        data,
        actor_id=uuid.UUID(current_user.id),
        actor_role=current_role,
    )
    return EventoRead.model_validate(evento)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    _user=Depends(require_permission("canDeleteEvents")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = EventoService(db)
    await service.delete_event(event_id)


@router.post("/{event_id}/publish", response_model=EventoRead)
async def publish_event(
    event_id: uuid.UUID,
    _user=Depends(require_permission("canPublishEvents")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.publish_event(event_id)
    return EventoRead.model_validate(evento)


@router.post("/{event_id}/approve", response_model=EventoRead)
async def approve_event(
    event_id: uuid.UUID,
    _user=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.approve_event(event_id)
    return EventoRead.model_validate(evento)


@router.post("/{event_id}/reject", response_model=EventoRead)
async def reject_event(
    event_id: uuid.UUID,
    payload: EventoRejectRequest,
    _user=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.reject_event(event_id, payload.motivo)
    return EventoRead.model_validate(evento)


@router.post("/{event_id}/image", response_model=EventoRead)
async def upload_event_image(
    event_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user=Depends(require_permission("canUploadImages")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    await _ensure_participant_owns_event(event_id, current_user, current_role, db)
    service = EventoService(db)
    content = await file.read()
    evento = await service.upload_event_image(event_id, file.filename or "imagem", content, file.content_type)
    return EventoRead.model_validate(evento)


@router.delete("/{event_id}/image", response_model=EventoRead)
async def delete_event_image(
    event_id: uuid.UUID,
    current_user=Depends(require_permission("canUploadImages")),
    current_role: Role = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    await _ensure_participant_owns_event(event_id, current_user, current_role, db)
    service = EventoService(db)
    evento = await service.delete_event_image(event_id)
    return EventoRead.model_validate(evento)
