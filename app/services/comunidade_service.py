import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.comunidade import Comunidade
from app.repositories.comunidade_repository import ComunidadeRepository
from app.schemas.comunidade import ComunidadeCreate, ComunidadeUpdate


class ComunidadeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ComunidadeRepository(db)

    async def get_comunidades(self) -> list[Comunidade]:
        return await self.repo.list_all()

    async def get_comunidade_by_id(self, comunidade_id: uuid.UUID) -> Comunidade:
        comunidade = await self.repo.get_by_id(comunidade_id)
        if comunidade is None:
            raise NotFoundError("Comunidade nao encontrada")
        return comunidade

    async def create_comunidade(self, data: ComunidadeCreate, created_by: uuid.UUID) -> Comunidade:
        comunidade = Comunidade(**data.model_dump(), created_by=created_by)
        try:
            return await self.repo.create(comunidade)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("Ja existe uma comunidade com este nome") from exc

    async def update_comunidade(self, comunidade_id: uuid.UUID, data: ComunidadeUpdate) -> Comunidade:
        comunidade = await self.get_comunidade_by_id(comunidade_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(comunidade, key, value)
        return await self.repo.update(comunidade)

    async def delete_comunidade(self, comunidade_id: uuid.UUID) -> None:
        comunidade = await self.get_comunidade_by_id(comunidade_id)
        await self.repo.delete(comunidade)
