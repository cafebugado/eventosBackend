import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rbac.permissions import require_permission
from app.schemas.evento import (
    EventoCreate,
    EventoRead,
    EventoStats,
    EventoUpdate,
    EventoWithTags,
)
from app.services.evento_service import EventoService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventoRead])
async def list_events(
    _user=Depends(require_permission("canCreateEvents")),
    db: AsyncSession = Depends(get_db),
) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_events()
    return [EventoRead.model_validate(e) for e in eventos]


@router.get("/published", response_model=list[EventoRead])
async def list_published_events(db: AsyncSession = Depends(get_db)) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_published_events()
    return [EventoRead.model_validate(e) for e in eventos]


@router.get("/upcoming", response_model=list[EventoRead])
async def list_upcoming_events(limit: int = 3, db: AsyncSession = Depends(get_db)) -> list[EventoRead]:
    service = EventoService(db)
    eventos = await service.get_upcoming_events(limit)
    return [EventoRead.model_validate(e) for e in eventos]


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
    return [EventoRead.model_validate(e) for e in eventos]


@router.get("/slug/{slug_or_id}", response_model=EventoRead)
async def get_event_by_slug_or_id(slug_or_id: str, db: AsyncSession = Depends(get_db)) -> EventoRead:
    service = EventoService(db)
    evento = await service.get_event_by_slug_or_id(slug_or_id)
    return EventoRead.model_validate(evento)


@router.get("/{event_id}", response_model=EventoRead)
async def get_event(
    event_id: uuid.UUID,
    _user=Depends(require_permission("canCreateEvents")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.get_event_by_id(event_id)
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
    _user=Depends(require_permission("canCreateEvents")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.create_event(data)
    return EventoRead.model_validate(evento)


@router.put("/{event_id}", response_model=EventoRead)
async def update_event(
    event_id: uuid.UUID,
    data: EventoUpdate,
    _user=Depends(require_permission("canEditEvents")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.update_event(event_id, data)
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


@router.post("/{event_id}/image", response_model=EventoRead)
async def upload_event_image(
    event_id: uuid.UUID,
    file: UploadFile = File(...),
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    content = await file.read()
    evento = await service.upload_event_image(event_id, file.filename or "imagem", content, file.content_type)
    return EventoRead.model_validate(evento)


@router.delete("/{event_id}/image", response_model=EventoRead)
async def delete_event_image(
    event_id: uuid.UUID,
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> EventoRead:
    service = EventoService(db)
    evento = await service.delete_event_image(event_id)
    return EventoRead.model_validate(evento)
