import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db.session import get_db
from app.rbac.permissions import require_permission
from app.schemas.contribuinte import (
    ContribuinteCreate,
    ContribuinteRead,
    ContribuinteUpdate,
    GitHubUserInfo,
)
from app.services.contribuinte_service import ContribuinteService

router = APIRouter(prefix="/contributors", tags=["contributors"])


@router.get("", response_model=list[ContribuinteRead])
async def list_contributors(db: AsyncSession = Depends(get_db)) -> list[ContribuinteRead]:
    service = ContribuinteService(db)
    contribuintes = await service.get_contributors()
    return [ContribuinteRead.model_validate(c) for c in contribuintes]


@router.get("/github/{username}", response_model=GitHubUserInfo)
@limiter.limit("30/minute")
async def get_github_user(
    request: Request, username: str, db: AsyncSession = Depends(get_db)
) -> GitHubUserInfo:
    service = ContribuinteService(db)
    return await service.fetch_github_user(username)


@router.get("/{contributor_id}", response_model=ContribuinteRead)
async def get_contributor(contributor_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ContribuinteRead:
    service = ContribuinteService(db)
    contribuinte = await service.get_contributor_by_id(contributor_id)
    return ContribuinteRead.model_validate(contribuinte)


@router.post("", response_model=ContribuinteRead, status_code=201)
async def create_contributor(
    data: ContribuinteCreate,
    _user=Depends(require_permission("canManageContributors")),
    db: AsyncSession = Depends(get_db),
) -> ContribuinteRead:
    service = ContribuinteService(db)
    contribuinte = await service.create_contributor(data)
    return ContribuinteRead.model_validate(contribuinte)


@router.put("/{contributor_id}", response_model=ContribuinteRead)
async def update_contributor(
    contributor_id: uuid.UUID,
    data: ContribuinteUpdate,
    _user=Depends(require_permission("canManageContributors")),
    db: AsyncSession = Depends(get_db),
) -> ContribuinteRead:
    service = ContribuinteService(db)
    contribuinte = await service.update_contributor(contributor_id, data)
    return ContribuinteRead.model_validate(contribuinte)


@router.delete("/{contributor_id}", status_code=204)
async def delete_contributor(
    contributor_id: uuid.UUID,
    _user=Depends(require_permission("canManageContributors")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ContribuinteService(db)
    await service.delete_contributor(contributor_id)
