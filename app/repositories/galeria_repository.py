import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.galeria import GaleriaAlbum, GaleriaFoto


class GaleriaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_albums(self) -> list[GaleriaAlbum]:
        result = await self.db.execute(
            select(GaleriaAlbum)
            .options(selectinload(GaleriaAlbum.fotos))
            .order_by(GaleriaAlbum.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_fotos(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(GaleriaFoto))
        return result.scalar_one()

    async def get_album(self, album_id: uuid.UUID) -> GaleriaAlbum | None:
        result = await self.db.execute(
            select(GaleriaAlbum)
            .options(selectinload(GaleriaAlbum.fotos))
            .where(GaleriaAlbum.id == album_id)
        )
        return result.scalar_one_or_none()

    async def create_album(self, album: GaleriaAlbum) -> GaleriaAlbum:
        self.db.add(album)
        await self.db.commit()
        await self.db.refresh(album)
        return await self.get_album(album.id)  # type: ignore[return-value]

    async def update_album(self, album: GaleriaAlbum) -> GaleriaAlbum:
        await self.db.commit()
        await self.db.refresh(album)
        return album

    async def delete_album(self, album: GaleriaAlbum) -> None:
        await self.db.delete(album)
        await self.db.commit()

    async def get_foto(self, foto_id: uuid.UUID) -> GaleriaFoto | None:
        result = await self.db.execute(select(GaleriaFoto).where(GaleriaFoto.id == foto_id))
        return result.scalar_one_or_none()

    async def add_foto(self, foto: GaleriaFoto) -> GaleriaFoto:
        self.db.add(foto)
        await self.db.commit()
        await self.db.refresh(foto)
        return foto

    async def update_foto(self, foto: GaleriaFoto) -> GaleriaFoto:
        await self.db.commit()
        await self.db.refresh(foto)
        return foto

    async def delete_foto(self, foto: GaleriaFoto) -> None:
        await self.db.delete(foto)
        await self.db.commit()
