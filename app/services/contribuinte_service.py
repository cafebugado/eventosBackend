import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.integrations.github import get_user_info
from app.models.contribuinte import Contribuinte
from app.repositories.contribuinte_repository import ContribuinteRepository
from app.schemas.contribuinte import ContribuinteCreate, ContribuinteUpdate, GitHubUserInfo


class ContribuinteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ContribuinteRepository(db)

    async def get_contributors(self) -> list[Contribuinte]:
        return await self.repo.list_all()

    async def get_contributor_by_id(self, contributor_id: uuid.UUID) -> Contribuinte:
        contribuinte = await self.repo.get_by_id(contributor_id)
        if contribuinte is None:
            raise NotFoundError("Contribuidor nao encontrado")
        return contribuinte

    async def create_contributor(self, data: ContribuinteCreate) -> Contribuinte:
        existing = await self.repo.get_by_github_username(data.github_username)
        if existing is not None:
            raise ConflictError("Ja existe um contribuidor com este github_username")

        contribuinte = Contribuinte(**data.model_dump())
        try:
            return await self.repo.create(contribuinte)
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError("Ja existe um contribuidor com este github_username") from exc

    async def update_contributor(self, contributor_id: uuid.UUID, data: ContribuinteUpdate) -> Contribuinte:
        contribuinte = await self.get_contributor_by_id(contributor_id)
        update_data = data.model_dump(exclude_unset=True)

        new_username = update_data.get("github_username")
        if new_username is not None and new_username != contribuinte.github_username:
            existing = await self.repo.get_by_github_username(new_username)
            if existing is not None:
                raise ConflictError("Ja existe um contribuidor com este github_username")

        for key, value in update_data.items():
            setattr(contribuinte, key, value)

        return await self.repo.update(contribuinte)

    async def delete_contributor(self, contributor_id: uuid.UUID) -> None:
        contribuinte = await self.get_contributor_by_id(contributor_id)
        await self.repo.delete(contribuinte)

    async def fetch_github_user(self, username: str) -> GitHubUserInfo:
        return await get_user_info(username)
