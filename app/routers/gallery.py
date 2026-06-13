import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db.session import get_db
from app.rbac.permissions import require_permission
from app.schemas.galeria import (
    GaleriaAlbumCreate,
    GaleriaAlbumRead,
    GaleriaAlbumUpdate,
    GaleriaFotoRead,
    GaleriaFotoUpdate,
    GaleriaFotoUrlCreate,
)
from app.services.galeria_service import GaleriaService

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.get("/albums", response_model=list[GaleriaAlbumRead])
async def list_albums(db: AsyncSession = Depends(get_db)) -> list[GaleriaAlbumRead]:
    service = GaleriaService(db)
    albums = await service.get_albums()
    return [GaleriaAlbumRead.model_validate(a) for a in albums]


@router.post("/albums", response_model=GaleriaAlbumRead, status_code=201)
async def create_album(
    data: GaleriaAlbumCreate,
    current_user: CurrentUser = Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> GaleriaAlbumRead:
    service = GaleriaService(db)
    album = await service.create_album(data, created_by=uuid.UUID(current_user.id))
    return GaleriaAlbumRead.model_validate(album)


@router.put("/albums/{album_id}", response_model=GaleriaAlbumRead)
async def update_album(
    album_id: uuid.UUID,
    data: GaleriaAlbumUpdate,
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> GaleriaAlbumRead:
    service = GaleriaService(db)
    album = await service.update_album(album_id, data)
    return GaleriaAlbumRead.model_validate(album)


@router.delete("/albums/{album_id}", status_code=204)
async def delete_album(
    album_id: uuid.UUID,
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = GaleriaService(db)
    await service.delete_album(album_id)


@router.post("/albums/{album_id}/photos", response_model=GaleriaFotoRead, status_code=201)
async def upload_photo(
    album_id: uuid.UUID,
    file: UploadFile = File(...),
    legenda: str | None = None,
    ordem: int = 0,
    current_user: CurrentUser = Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> GaleriaFotoRead:
    service = GaleriaService(db)
    content = await file.read()
    foto = await service.upload_foto(
        album_id,
        file.filename or "foto",
        content,
        file.content_type,
        legenda,
        ordem,
        uploaded_by=uuid.UUID(current_user.id),
    )
    return GaleriaFotoRead.model_validate(foto)


@router.post("/albums/{album_id}/photos/url", response_model=GaleriaFotoRead, status_code=201)
async def add_photo_by_url(
    album_id: uuid.UUID,
    data: GaleriaFotoUrlCreate,
    current_user: CurrentUser = Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> GaleriaFotoRead:
    service = GaleriaService(db)
    foto = await service.add_foto_by_url(album_id, data, uploaded_by=uuid.UUID(current_user.id))
    return GaleriaFotoRead.model_validate(foto)


@router.put("/photos/{photo_id}", response_model=GaleriaFotoRead)
async def update_photo_legenda(
    photo_id: uuid.UUID,
    data: GaleriaFotoUpdate,
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> GaleriaFotoRead:
    service = GaleriaService(db)
    foto = await service.update_foto_legenda(photo_id, data)
    return GaleriaFotoRead.model_validate(foto)


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: uuid.UUID,
    _user=Depends(require_permission("canUploadImages")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = GaleriaService(db)
    await service.delete_foto(photo_id)
