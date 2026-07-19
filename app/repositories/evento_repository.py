import re
import uuid
from datetime import date

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento


class EventoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(
        self,
        limit: int | None = None,
        offset: int = 0,
        created_by: uuid.UUID | None = None,
        pending_first: bool = False,
    ) -> list[Evento]:
        stmt = select(Evento).order_by(*self._order_by(pending_first=pending_first))
        if created_by is not None:
            stmt = stmt.where(Evento.created_by == created_by)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_filtered(
        self,
        *,
        status: str | None = None,
        date_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        created_by: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        pending_first: bool = False,
    ) -> tuple[list[Evento], int]:
        stmt = self._apply_filters(
            select(Evento),
            status=status,
            date_filter=date_filter,
            date_from=date_from,
            date_to=date_to,
            search=search,
            created_by=created_by,
        )
        count_stmt = self._apply_filters(
            select(func.count()).select_from(Evento),
            status=status,
            date_filter=date_filter,
            date_from=date_from,
            date_to=date_to,
            search=search,
            created_by=created_by,
        )

        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(*self._order_by(pending_first=pending_first))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    def _apply_filters(
        self,
        stmt: Select[tuple[Evento]] | Select[tuple[int]],
        *,
        status: str | None,
        date_filter: str | None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None,
        created_by: uuid.UUID | None,
    ):
        if status is not None:
            stmt = stmt.where(Evento.status == status)
        if created_by is not None:
            stmt = stmt.where(Evento.created_by == created_by)
        if date_filter is not None:
            event_date_key = self._event_date_key()
            today_key = date.today().isoformat()
            if date_filter == "upcoming":
                stmt = stmt.where(event_date_key >= today_key)
            elif date_filter == "past":
                stmt = stmt.where(event_date_key < today_key)
        if date_from is not None or date_to is not None:
            event_date_key = self._event_date_key()
            if date_from is not None:
                stmt = stmt.where(event_date_key >= date_from)
            if date_to is not None:
                stmt = stmt.where(event_date_key <= date_to)
        if search:
            term = search.strip().lower()
            iso_date_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", term)
            if iso_date_match:
                year, month, day = iso_date_match.groups()
                stmt = stmt.where(Evento.data_evento == f"{day}/{month}/{year}")
            else:
                pattern = f"%{term}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Evento.nome).like(pattern),
                        func.lower(func.coalesce(Evento.descricao, "")).like(pattern),
                        Evento.data_evento.like(f"%{term}%"),
                    )
                )
        return stmt

    def _event_date_key(self):
        return (
            func.substr(Evento.data_evento, 7, 4)
            + "-"
            + func.substr(Evento.data_evento, 4, 2)
            + "-"
            + func.substr(Evento.data_evento, 1, 2)
        )

    def _event_month_key(self):
        return func.substr(Evento.data_evento, 7, 4) + "-" + func.substr(Evento.data_evento, 4, 2)

    def _metrics_filter(self, stmt, *, date_from: str | None, date_to: str | None):
        return self._apply_filters(
            stmt,
            status=None,
            date_filter=None,
            date_from=date_from,
            date_to=date_to,
            search=None,
            created_by=None,
        )

    async def count_by_dia_semana(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str, int]]:
        stmt = self._metrics_filter(
            select(Evento.dia_semana, func.count()).group_by(Evento.dia_semana),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_by_periodo(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str | None, int]]:
        stmt = self._metrics_filter(
            select(Evento.periodo, func.count()).group_by(Evento.periodo),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_by_modalidade(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str | None, int]]:
        stmt = self._metrics_filter(
            select(Evento.modalidade, func.count()).group_by(Evento.modalidade),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_by_cidade(
        self, *, limit: int = 10, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str | None, str | None, int]]:
        stmt = self._metrics_filter(
            select(Evento.cidade, Evento.estado, func.count())
            .where(Evento.cidade.isnot(None))
            .group_by(Evento.cidade, Evento.estado)
            .order_by(func.count().desc())
            .limit(limit),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_by_status(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str, int]]:
        stmt = self._metrics_filter(
            select(Evento.status, func.count()).group_by(Evento.status),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def count_by_month(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str, int]]:
        month_key = self._event_month_key()
        stmt = self._metrics_filter(
            select(month_key.label("ano_mes"), func.count())
            .group_by(month_key)
            .order_by(month_key),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def get_date_bounds(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> tuple[str | None, str | None]:
        date_key = self._event_date_key()
        stmt = self._metrics_filter(
            select(func.min(date_key), func.max(date_key)),
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.db.execute(stmt)
        return result.one()

    def _order_by(self, *, pending_first: bool):
        if not pending_first:
            return (Evento.created_at.desc(),)

        return (
            case((Evento.status == "em_analise", 0), else_=1),
            Evento.created_at.desc(),
        )

    async def count_dashboard_periods(
        self,
        *,
        today: str,
        week_start: str,
        week_end: str,
        month_start: str,
        month_end: str,
        year_start: str,
        year_end: str,
        created_by: uuid.UUID | None = None,
    ) -> dict[str, int]:
        date_key = self._event_date_key()
        totals = {
            "total": func.count(),
            "hoje": func.count(case((date_key == today, 1))),
            "semana": func.count(case((date_key.between(week_start, week_end), 1))),
            "mes": func.count(case((date_key.between(month_start, month_end), 1))),
            "ano": func.count(case((date_key.between(year_start, year_end), 1))),
            "diurno": func.count(case((Evento.periodo == "Diurno", 1))),
            "noturno": func.count(case((Evento.periodo == "Noturno", 1))),
        }
        if created_by is not None:
            totals["meus_eventos"] = func.count(case((Evento.created_by == created_by, 1)))

        stmt = select(*totals.values())
        result = await self.db.execute(stmt)
        row = result.one()
        return dict(zip(totals.keys(), row, strict=True))

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
