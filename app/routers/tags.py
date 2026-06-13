import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rbac.permissions import require_permission
from app.schemas.tag import SetEventTagsRequest, TagCreate, TagRead, TagUpdate
from app.services.tag_service import TagService

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagRead])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[TagRead]:
    service = TagService(db)
    tags = await service.get_tags()
    return [TagRead.model_validate(t) for t in tags]


@router.post("/tags", response_model=TagRead, status_code=201)
async def create_tag(
    data: TagCreate,
    _user=Depends(require_permission("canManageTags")),
    db: AsyncSession = Depends(get_db),
) -> TagRead:
    service = TagService(db)
    tag = await service.create_tag(data)
    return TagRead.model_validate(tag)


@router.put("/tags/{tag_id}", response_model=TagRead)
async def update_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    _user=Depends(require_permission("canManageTags")),
    db: AsyncSession = Depends(get_db),
) -> TagRead:
    service = TagService(db)
    tag = await service.update_tag(tag_id, data)
    return TagRead.model_validate(tag)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: uuid.UUID,
    _user=Depends(require_permission("canDeleteTags")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = TagService(db)
    await service.delete_tag(tag_id)


@router.get("/events/tags-map")
async def get_all_event_tags(db: AsyncSession = Depends(get_db)) -> dict[str, list[TagRead]]:
    service = TagService(db)
    mapping = await service.get_all_event_tags()
    return {str(evento_id): [TagRead.model_validate(t) for t in tags] for evento_id, tags in mapping.items()}


@router.get("/events/{event_id}/tags", response_model=list[TagRead])
async def get_event_tags(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[TagRead]:
    service = TagService(db)
    tags = await service.get_event_tags(event_id)
    return [TagRead.model_validate(t) for t in tags]


@router.put("/events/{event_id}/tags", response_model=list[TagRead])
async def set_event_tags(
    event_id: uuid.UUID,
    data: SetEventTagsRequest,
    _user=Depends(require_permission("canManageTags")),
    db: AsyncSession = Depends(get_db),
) -> list[TagRead]:
    service = TagService(db)
    tags = await service.set_event_tags(event_id, data.tag_ids)
    return [TagRead.model_validate(t) for t in tags]
