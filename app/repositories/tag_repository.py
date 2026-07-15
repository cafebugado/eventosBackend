import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento
from app.models.evento_tag import EventoTag
from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Tag]:
        result = await self.db.execute(select(Tag).order_by(Tag.nome))
        return list(result.scalars().all())

    async def get_by_id(self, tag_id: uuid.UUID) -> Tag | None:
        result = await self.db.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalar_one_or_none()

    async def get_by_nome(self, nome: str) -> Tag | None:
        result = await self.db.execute(select(Tag).where(Tag.nome == nome))
        return result.scalar_one_or_none()

    async def create(self, tag: Tag) -> Tag:
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def update(self, tag: Tag) -> Tag:
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete(self, tag: Tag) -> None:
        await self.db.delete(tag)
        await self.db.commit()

    async def get_tags_for_evento(self, evento_id: uuid.UUID) -> list[Tag]:
        result = await self.db.execute(
            select(Tag).join(EventoTag, EventoTag.tag_id == Tag.id).where(EventoTag.evento_id == evento_id)
        )
        return list(result.scalars().all())

    async def get_event_tags_map(self) -> dict[uuid.UUID, list[Tag]]:
        result = await self.db.execute(
            select(EventoTag.evento_id, Tag).join(Tag, EventoTag.tag_id == Tag.id)
        )
        mapping: dict[uuid.UUID, list[Tag]] = {}
        for evento_id, tag in result.all():
            mapping.setdefault(evento_id, []).append(tag)
        return mapping

    async def get_top_tags(
        self, *, limit: int = 10, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[uuid.UUID, str, str, int]]:
        total = func.count(EventoTag.evento_id)
        stmt = (
            select(Tag.id, Tag.nome, Tag.cor, total)
            .join(EventoTag, EventoTag.tag_id == Tag.id)
        )
        if date_from is not None or date_to is not None:
            date_key = (
                func.substr(Evento.data_evento, 7, 4)
                + "-"
                + func.substr(Evento.data_evento, 4, 2)
                + "-"
                + func.substr(Evento.data_evento, 1, 2)
            )
            stmt = stmt.join(Evento, Evento.id == EventoTag.evento_id)
            if date_from is not None:
                stmt = stmt.where(date_key >= date_from)
            if date_to is not None:
                stmt = stmt.where(date_key <= date_to)
        stmt = stmt.group_by(Tag.id, Tag.nome, Tag.cor).order_by(total.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.all())

    async def set_event_tags(self, evento_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        await self.db.execute(delete(EventoTag).where(EventoTag.evento_id == evento_id))
        for tag_id in tag_ids:
            self.db.add(EventoTag(evento_id=evento_id, tag_id=tag_id))
        await self.db.commit()
