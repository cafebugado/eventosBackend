import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento


class EventoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, limit: int | None = None, offset: int = 0) -> list[Evento]:
        stmt = select(Evento).order_by(Evento.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str, limit: int | None = None, offset: int = 0) -> list[Evento]:
        stmt = select(Evento).where(Evento.status == status).order_by(Evento.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, evento_id: uuid.UUID) -> Evento | None:
        result = await self.db.execute(select(Evento).where(Evento.id == evento_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Evento | None:
        result = await self.db.execute(select(Evento).where(Evento.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_nome(self, nome: str, exclude_id: uuid.UUID | None = None) -> Evento | None:
        normalized_name = nome.strip().lower()
        stmt = select(Evento).where(func.lower(func.trim(Evento.nome)) == normalized_name).limit(1)
        if exclude_id is not None:
            stmt = stmt.where(Evento.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_slugs_starting_with(self, prefix: str, exclude_id: uuid.UUID | None = None) -> set[str]:
        stmt = select(Evento.slug).where(Evento.slug.like(f"{prefix}%"))
        if exclude_id is not None:
            stmt = stmt.where(Evento.id != exclude_id)
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def create(self, evento: Evento) -> Evento:
        self.db.add(evento)
        await self.db.commit()
        await self.db.refresh(evento)
        return evento

    async def update(self, evento: Evento) -> Evento:
        await self.db.commit()
        await self.db.refresh(evento)
        return evento

    async def delete(self, evento: Evento) -> None:
        await self.db.delete(evento)
        await self.db.commit()
