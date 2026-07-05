import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.integrations.supabase_storage import remove_by_public_url, upload_file
from app.models.evento import Evento
from app.rbac.roles import Role
from app.repositories.evento_repository import EventoRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.evento import (
    EventoCreate,
    EventoDateFilter,
    EventoStats,
    EventoStatus,
    EventoUpdate,
    EventoWithTags,
)
from app.utils.event_date import get_iso_week, get_iso_year, parse_event_date
from app.utils.slug import generate_slug, resolve_unique_slug

REVIEW_ROLES = {Role.SUPER_ADMIN, Role.ADMIN}
REVIEW_STATUSES = {"em_analise", "recusado"}


class EventoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventoRepository(db)
        self.tag_repo = TagRepository(db)

    async def get_events(
        self,
        limit: int | None = None,
        offset: int = 0,
        created_by: uuid.UUID | None = None,
        pending_first: bool = False,
    ) -> list[Evento]:
        return await self.repo.list_all(
            limit=limit,
            offset=offset,
            created_by=created_by,
            pending_first=pending_first,
        )

    async def get_events_page(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: EventoStatus | None = None,
        date_filter: EventoDateFilter | None = None,
        search: str | None = None,
        created_by: uuid.UUID | None = None,
        pending_first: bool = False,
    ) -> tuple[list[Evento], int]:
        return await self.repo.list_filtered(
            page=page,
            page_size=page_size,
            status=status,
            date_filter=date_filter,
            search=search,
            created_by=created_by,
            pending_first=pending_first,
        )

    async def get_published_events(self, limit: int | None = None, offset: int = 0) -> list[Evento]:
        return await self.repo.list_by_status("publicado", limit=limit, offset=offset)

    async def get_event_by_id(self, event_id: uuid.UUID) -> Evento:
        evento = await self.repo.get_by_id(event_id)
        if evento is None:
            raise NotFoundError("Evento nao encontrado")
        return evento

    async def get_event_by_slug_or_id(self, slug_or_id: str) -> Evento:
        evento = await self.repo.get_by_slug(slug_or_id)
        if evento is not None:
            return evento

        try:
            event_id = uuid.UUID(slug_or_id)
        except ValueError as exc:
            raise NotFoundError("Evento nao encontrado") from exc

        evento = await self.repo.get_by_id(event_id)
        if evento is None:
            raise NotFoundError("Evento nao encontrado")
        return evento

    async def _resolve_slug(self, nome: str, exclude_id: uuid.UUID | None = None) -> str:
        base = generate_slug(nome)
        used = await self.repo.list_slugs_starting_with(base, exclude_id=exclude_id)
        return resolve_unique_slug(base, used)

    async def _ensure_unique_name(self, nome: str, exclude_id: uuid.UUID | None = None) -> None:
        existing = await self.repo.get_by_nome(nome, exclude_id=exclude_id)
        if existing is not None:
            raise ConflictError("Ja existe um evento cadastrado com este nome")

    async def create_event(
        self,
        data: EventoCreate,
        created_by: uuid.UUID | None = None,
        actor_role: Role | None = None,
    ) -> Evento:
        await self._ensure_unique_name(data.nome)
        slug = await self._resolve_slug(data.nome)
        payload = data.model_dump()
        if actor_role == Role.PARTICIPANTE:
            payload["status"] = "em_analise"
        evento = Evento(**payload, slug=slug, created_by=created_by)
        return await self.repo.create(evento)

    async def update_event(
        self,
        event_id: uuid.UUID,
        data: EventoUpdate,
        actor_id: uuid.UUID | None = None,
        actor_role: Role | None = None,
    ) -> Evento:
        evento = await self.get_event_by_id(event_id)
        update_data = data.model_dump(exclude_unset=True)
        self._ensure_can_update_event(evento, update_data, actor_id, actor_role)

        if actor_role == Role.PARTICIPANTE and evento.status == "publicado":
            update_data["status"] = "em_analise"

        if "nome" in update_data:
            await self._ensure_unique_name(update_data["nome"], exclude_id=event_id)
            if update_data["nome"] != evento.nome:
                update_data["slug"] = await self._resolve_slug(update_data["nome"], exclude_id=event_id)

        for key, value in update_data.items():
            setattr(evento, key, value)

        return await self.repo.update(evento)

    def _ensure_can_update_event(
        self,
        evento: Evento,
        update_data: dict,
        actor_id: uuid.UUID | None,
        actor_role: Role | None,
    ) -> None:
        if actor_role in (Role.MODERADOR, Role.PARTICIPANTE) and evento.created_by != actor_id:
            raise ForbiddenError("Voce so pode editar eventos criados pela propria conta")

        if actor_role in REVIEW_ROLES:
            return

        new_status = update_data.get("status")
        if evento.status == "em_analise" or (new_status is not None and new_status in REVIEW_STATUSES):
            raise ForbiddenError("Eventos em revisao devem ser analisados por admin ou super_admin")

    async def delete_event(self, event_id: uuid.UUID) -> None:
        evento = await self.get_event_by_id(event_id)
        await self.repo.delete(evento)

    async def publish_event(self, event_id: uuid.UUID) -> Evento:
        evento = await self.get_event_by_id(event_id)
        if evento.status == "em_analise":
            raise ForbiddenError("Eventos em analise devem ser aprovados pela revisao")
        evento.status = "publicado"
        return await self.repo.update(evento)

    async def approve_event(self, event_id: uuid.UUID) -> Evento:
        evento = await self.get_event_by_id(event_id)
        evento.status = "publicado"
        evento.motivo_recusa = None
        return await self.repo.update(evento)

    async def reject_event(self, event_id: uuid.UUID, motivo: str) -> Evento:
        evento = await self.get_event_by_id(event_id)
        evento.status = "recusado"
        evento.motivo_recusa = motivo
        return await self.repo.update(evento)

    async def get_events_by_period(self, periodo: str) -> list[Evento]:
        published = await self.repo.list_by_status("publicado")
        return [e for e in published if e.periodo == periodo]

    async def get_upcoming_events(self, limit: int = 3) -> list[Evento]:
        published = await self.repo.list_by_status("publicado")
        today = date.today()

        upcoming = []
        for evento in published:
            event_date = parse_event_date(evento.data_evento)
            if event_date is not None and event_date >= today:
                upcoming.append(evento)

        upcoming.sort(key=lambda e: e.created_at, reverse=True)
        return upcoming[:limit]

    async def get_event_stats(self) -> EventoStats:
        eventos = await self.repo.list_all()
        return EventoStats(
            total=len(eventos),
            publicados=sum(1 for e in eventos if e.status == "publicado"),
            rascunhos=sum(1 for e in eventos if e.status == "rascunho"),
            noturno=sum(1 for e in eventos if e.periodo == "Noturno"),
            diurno=sum(1 for e in eventos if e.periodo == "Diurno"),
        )

    async def get_recommended_events(self, event_id: uuid.UUID, limit: int = 3) -> list[EventoWithTags]:
        current_event = await self.get_event_by_id(event_id)
        today = date.today()

        published = await self.repo.list_by_status("publicado")
        tags_map = await self.tag_repo.get_event_tags_map()

        current_tags = {tag.id for tag in tags_map.get(current_event.id, [])}
        current_event_date = parse_event_date(current_event.data_evento)

        candidates = []
        for evento in published:
            if evento.id == current_event.id:
                continue
            event_date = parse_event_date(evento.data_evento)
            if event_date is None or event_date < today:
                continue
            candidates.append((evento, event_date))

        def sort_key(item: tuple[Evento, date]) -> tuple[bool, bool, int]:
            evento, event_date = item
            evento_tags = {tag.id for tag in tags_map.get(evento.id, [])}
            has_tag_match = bool(current_tags & evento_tags)

            same_week = False
            if current_event_date is not None:
                same_week = get_iso_week(event_date) == get_iso_week(current_event_date) and get_iso_year(
                    event_date
                ) == get_iso_year(current_event_date)

            days_away = (event_date - today).days
            return (not has_tag_match, not same_week, days_away)

        candidates.sort(key=sort_key)

        results = []
        for evento, _ in candidates[:limit]:
            evento_dict = {c.name: getattr(evento, c.name) for c in evento.__table__.columns}
            evento_dict["tags"] = tags_map.get(evento.id, [])
            results.append(EventoWithTags.model_validate(evento_dict))

        return results

    async def upload_event_image(
        self, event_id: uuid.UUID, filename: str, content: bytes, content_type: str | None
    ) -> Evento:
        evento = await self.get_event_by_id(event_id)
        url = await upload_file("eventos", filename, content, content_type)
        evento.imagem = url
        return await self.repo.update(evento)

    async def delete_event_image(self, event_id: uuid.UUID) -> Evento:
        evento = await self.get_event_by_id(event_id)
        if evento.imagem:
            await remove_by_public_url(evento.imagem)
            evento.imagem = None
            evento = await self.repo.update(evento)
        return evento
