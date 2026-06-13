import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tag import Tag
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagUpdate


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TagRepository(db)

    async def get_tags(self) -> list[Tag]:
        return await self.repo.list_all()

    async def get_tag_by_id(self, tag_id: uuid.UUID) -> Tag:
        tag = await self.repo.get_by_id(tag_id)
        if tag is None:
            raise NotFoundError("Tag nao encontrada")
        return tag

    async def create_tag(self, data: TagCreate) -> Tag:
        existing = await self.repo.get_by_nome(data.nome)
        if existing is not None:
            raise ConflictError("Ja existe uma tag com este nome")
        tag = Tag(**data.model_dump())
        return await self.repo.create(tag)

    async def update_tag(self, tag_id: uuid.UUID, data: TagUpdate) -> Tag:
        tag = await self.get_tag_by_id(tag_id)
        update_data = data.model_dump(exclude_unset=True)

        if "nome" in update_data and update_data["nome"] != tag.nome:
            existing = await self.repo.get_by_nome(update_data["nome"])
            if existing is not None:
                raise ConflictError("Ja existe uma tag com este nome")

        for key, value in update_data.items():
            setattr(tag, key, value)

        return await self.repo.update(tag)

    async def delete_tag(self, tag_id: uuid.UUID) -> None:
        tag = await self.get_tag_by_id(tag_id)
        await self.repo.delete(tag)

    async def get_event_tags(self, event_id: uuid.UUID) -> list[Tag]:
        return await self.repo.get_tags_for_evento(event_id)

    async def set_event_tags(self, event_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list[Tag]:
        await self.repo.set_event_tags(event_id, tag_ids)
        return await self.repo.get_tags_for_evento(event_id)

    async def get_all_event_tags(self) -> dict[uuid.UUID, list[Tag]]:
        return await self.repo.get_event_tags_map()
