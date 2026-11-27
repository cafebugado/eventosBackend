import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_evento_service, get_tag_service
from app.core.security import CurrentUser
from app.rbac.permissions import get_current_user_role, require_permission
from app.rbac.roles import Role
from app.schemas.tag import SetEventTagsRequest, TagCreate, TagRead, TagUpdate
from app.services.evento_service import EventoService
from app.services.tag_service import TagService

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagRead])
async def list_tags(service: TagService = Depends(get_tag_service)) -> list[TagRead]:
    tags = await service.get_tags()
    return [TagRead.model_validate(t) for t in tags]


@router.post("/tags", response_model=TagRead, status_code=201)
async def create_tag(
    data: TagCreate,
    _user=Depends(require_permission("canManageTags")),
    service: TagService = Depends(get_tag_service),
) -> TagRead:
    tag = await service.create_tag(data)
    return TagRead.model_validate(tag)


@router.put("/tags/{tag_id}", response_model=TagRead)
async def update_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    _user=Depends(require_permission("canManageTags")),
    service: TagService = Depends(get_tag_service),
) -> TagRead:
    tag = await service.update_tag(tag_id, data)
    return TagRead.model_validate(tag)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: uuid.UUID,
    _user=Depends(require_permission("canDeleteTags")),
    service: TagService = Depends(get_tag_service),
) -> None:
    await service.delete_tag(tag_id)


@router.get("/events/tags-map")
async def get_all_event_tags(service: TagService = Depends(get_tag_service)) -> dict[str, list[TagRead]]:
    mapping = await service.get_all_event_tags()
    return {str(evento_id): [TagRead.model_validate(t) for t in tags] for evento_id, tags in mapping.items()}


@router.get("/events/{event_id}/tags", response_model=list[TagRead])
async def get_event_tags(
    event_id: uuid.UUID, service: TagService = Depends(get_tag_service)
) -> list[TagRead]:
    tags = await service.get_event_tags(event_id)
    return [TagRead.model_validate(t) for t in tags]


@router.put("/events/{event_id}/tags", response_model=list[TagRead])
async def set_event_tags(
    event_id: uuid.UUID,
    data: SetEventTagsRequest,
    current_user: CurrentUser = Depends(require_permission("canCreateEvents")),
    current_role: Role = Depends(get_current_user_role),
    service: TagService = Depends(get_tag_service),
    evento_service: EventoService = Depends(get_evento_service),
) -> list[TagRead]:
    if current_role == Role.PARTICIPANTE:
        evento = await evento_service.get_event_by_id(event_id)
        if evento.created_by != uuid.UUID(current_user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente para esta acao")

    tags = await service.set_event_tags(event_id, data.tag_ids)
    return [TagRead.model_validate(t) for t in tags]
