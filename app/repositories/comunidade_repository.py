import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunidade import Comunidade


class ComunidadeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Comunidade]:
        result = await self.db.execute(select(Comunidade).order_by(Comunidade.nome))
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Comunidade))
        return result.scalar_one()

    async def get_by_id(self, comunidade_id: uuid.UUID) -> Comunidade | None:
        result = await self.db.execute(select(Comunidade).where(Comunidade.id == comunidade_id))
        return result.scalar_one_or_none()

    async def create(self, comunidade: Comunidade) -> Comunidade:
        self.db.add(comunidade)
        await self.db.commit()
        await self.db.refresh(comunidade)
        return comunidade

    async def update(self, comunidade: Comunidade) -> Comunidade:
        await self.db.commit()
        await self.db.refresh(comunidade)
        return comunidade

    async def delete(self, comunidade: Comunidade) -> None:
        await self.db.delete(comunidade)
        await self.db.commit()
