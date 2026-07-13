import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db.session import get_db
from app.rbac.permissions import require_permission
from app.schemas.comunidade import ComunidadeCreate, ComunidadeRead, ComunidadeUpdate
from app.services.comunidade_service import ComunidadeService

router = APIRouter(prefix="/communities", tags=["communities"])


@router.get("", response_model=list[ComunidadeRead])
async def list_communities(db: AsyncSession = Depends(get_db)) -> list[ComunidadeRead]:
    service = ComunidadeService(db)
    comunidades = await service.get_comunidades()
    return [ComunidadeRead.model_validate(c) for c in comunidades]


@router.post("", response_model=ComunidadeRead, status_code=201)
async def create_community(
    data: ComunidadeCreate,
    current_user: CurrentUser = Depends(require_permission("canManageComunidades")),
    db: AsyncSession = Depends(get_db),
) -> ComunidadeRead:
    service = ComunidadeService(db)
    comunidade = await service.create_comunidade(data, created_by=uuid.UUID(current_user.id))
    return ComunidadeRead.model_validate(comunidade)


@router.put("/{community_id}", response_model=ComunidadeRead)
async def update_community(
    community_id: uuid.UUID,
    data: ComunidadeUpdate,
    _user: CurrentUser = Depends(require_permission("canManageComunidades")),
    db: AsyncSession = Depends(get_db),
) -> ComunidadeRead:
    service = ComunidadeService(db)
    comunidade = await service.update_comunidade(community_id, data)
    return ComunidadeRead.model_validate(comunidade)


@router.delete("/{community_id}", status_code=204)
async def delete_community(
    community_id: uuid.UUID,
    _user: CurrentUser = Depends(require_permission("canManageComunidades")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ComunidadeService(db)
    await service.delete_comunidade(community_id)
