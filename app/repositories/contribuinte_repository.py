import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contribuinte import Contribuinte


class ContribuinteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Contribuinte]:
        result = await self.db.execute(select(Contribuinte).order_by(Contribuinte.nome))
        return list(result.scalars().all())

    async def get_by_id(self, contribuinte_id: uuid.UUID) -> Contribuinte | None:
        result = await self.db.execute(select(Contribuinte).where(Contribuinte.id == contribuinte_id))
        return result.scalar_one_or_none()

    async def get_by_github_username(self, username: str) -> Contribuinte | None:
        result = await self.db.execute(
            select(Contribuinte).where(Contribuinte.github_username == username)
        )
        return result.scalar_one_or_none()

    async def create(self, contribuinte: Contribuinte) -> Contribuinte:
        self.db.add(contribuinte)
        await self.db.commit()
        await self.db.refresh(contribuinte)
        return contribuinte

    async def update(self, contribuinte: Contribuinte) -> Contribuinte:
        await self.db.commit()
        await self.db.refresh(contribuinte)
        return contribuinte

    async def delete(self, contribuinte: Contribuinte) -> None:
        await self.db.delete(contribuinte)
        await self.db.commit()
