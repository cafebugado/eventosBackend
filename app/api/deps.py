from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.evento_service import EventoService
from app.services.tag_service import TagService


async def get_evento_service(db: AsyncSession = Depends(get_db)) -> EventoService:
    return EventoService(db)


async def get_tag_service(db: AsyncSession = Depends(get_db)) -> TagService:
    return TagService(db)
