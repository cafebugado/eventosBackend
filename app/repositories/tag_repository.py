import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def set_event_tags(self, evento_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        await self.db.execute(delete(EventoTag).where(EventoTag.evento_id == evento_id))
        for tag_id in tag_ids:
            self.db.add(EventoTag(evento_id=evento_id, tag_id=tag_id))
        await self.db.commit()
