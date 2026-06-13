import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.integrations.supabase_storage import remove_file, upload_file
from app.models.galeria import GaleriaAlbum, GaleriaFoto
from app.repositories.galeria_repository import GaleriaRepository
from app.schemas.galeria import (
    GaleriaAlbumCreate,
    GaleriaAlbumUpdate,
    GaleriaFotoUpdate,
    GaleriaFotoUrlCreate,
)


class GaleriaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GaleriaRepository(db)

    async def get_albums(self) -> list[GaleriaAlbum]:
        return await self.repo.list_albums()

    async def get_album_by_id(self, album_id: uuid.UUID) -> GaleriaAlbum:
        album = await self.repo.get_album(album_id)
        if album is None:
            raise NotFoundError("Album nao encontrado")
        return album

    async def create_album(self, data: GaleriaAlbumCreate, created_by: uuid.UUID) -> GaleriaAlbum:
        album = GaleriaAlbum(**data.model_dump(), created_by=created_by)
        return await self.repo.create_album(album)

    async def update_album(self, album_id: uuid.UUID, data: GaleriaAlbumUpdate) -> GaleriaAlbum:
        album = await self.get_album_by_id(album_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(album, key, value)
        return await self.repo.update_album(album)

    async def delete_album(self, album_id: uuid.UUID) -> None:
        album = await self.get_album_by_id(album_id)
        for foto in album.fotos:
            if foto.storage_path:
                remove_file(foto.storage_path)
        await self.repo.delete_album(album)

    async def upload_foto(
        self,
        album_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
        legenda: str | None,
        ordem: int,
        uploaded_by: uuid.UUID,
    ) -> GaleriaFoto:
        await self.get_album_by_id(album_id)  # garante que o album existe

        prefix = f"galeria/{album_id}"
        url = upload_file(prefix, filename, content, content_type)
        storage_path = _extract_path_from_prefix(url, prefix)

        foto = GaleriaFoto(
            album_id=album_id,
            url=url,
            storage_path=storage_path,
            legenda=legenda,
            ordem=ordem,
            uploaded_by=uploaded_by,
        )
        return await self.repo.add_foto(foto)

    async def add_foto_by_url(
        self,
        album_id: uuid.UUID,
        data: GaleriaFotoUrlCreate,
        uploaded_by: uuid.UUID,
    ) -> GaleriaFoto:
        await self.get_album_by_id(album_id)

        foto = GaleriaFoto(
            album_id=album_id,
            url=data.url,
            storage_path=None,
            legenda=data.legenda,
            ordem=data.ordem,
            uploaded_by=uploaded_by,
        )
        return await self.repo.add_foto(foto)

    async def update_foto_legenda(self, foto_id: uuid.UUID, data: GaleriaFotoUpdate) -> GaleriaFoto:
        foto = await self.repo.get_foto(foto_id)
        if foto is None:
            raise NotFoundError("Foto nao encontrada")
        if data.legenda is not None:
            foto.legenda = data.legenda
        return await self.repo.update_foto(foto)

    async def delete_foto(self, foto_id: uuid.UUID) -> None:
        foto = await self.repo.get_foto(foto_id)
        if foto is None:
            raise NotFoundError("Foto nao encontrada")
        if foto.storage_path:
            remove_file(foto.storage_path)
        await self.repo.delete_foto(foto)


def _extract_path_from_prefix(public_url: str, prefix: str) -> str | None:
    marker = f"/{prefix}/"
    idx = public_url.find(marker)
    if idx == -1:
        return None
    return f"{prefix}/{public_url[idx + len(marker):]}"
