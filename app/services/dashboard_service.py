import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evento import Evento
from app.rbac.permissions import PERMISSIONS
from app.rbac.roles import Role
from app.repositories.comunidade_repository import ComunidadeRepository
from app.repositories.contribuinte_repository import ContribuinteRepository
from app.repositories.evento_repository import EventoRepository
from app.repositories.galeria_repository import GaleriaRepository
from app.repositories.user_repository import UserRepository
from app.schemas.audit import AuditLogRead, AuditUser
from app.schemas.dashboard import DashboardEventCounts, DashboardSummary
from app.schemas.evento import EventoRead
from app.services.audit_service import AuditService
from app.services.evento_service import EventoService

REVIEW_ROLES = {Role.SUPER_ADMIN, Role.ADMIN}


def _week_range(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def _month_range(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    next_month = start.replace(day=28) + timedelta(days=4)
    end = next_month.replace(day=1) - timedelta(days=1)
    return start, end


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evento_repo = EventoRepository(db)
        self.comunidade_repo = ComunidadeRepository(db)
        self.contribuinte_repo = ContribuinteRepository(db)
        self.galeria_repo = GaleriaRepository(db)
        self.user_repo = UserRepository(db)
        self.evento_service = EventoService(db)
        self.audit_service = AuditService(db)

    async def get_summary(self, *, user_id: uuid.UUID, role: Role) -> DashboardSummary:
        today = date.today()
        week_start, week_end = _week_range(today)
        month_start, month_end = _month_range(today)
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        can_review = role in REVIEW_ROLES
        can_manage_comunidades = role in PERMISSIONS["canManageComunidades"]
        can_manage_contributors = role in PERMISSIONS["canManageContributors"]
        can_manage_galeria = role in PERMISSIONS["canManageGaleria"]
        can_manage_users = role in PERMISSIONS["canManageUsers"]

        counts_task = self.evento_repo.count_dashboard_periods(
            today=today.isoformat(),
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            month_start=month_start.isoformat(),
            month_end=month_end.isoformat(),
            year_start=year_start.isoformat(),
            year_end=year_end.isoformat(),
            created_by=user_id,
        )
        upcoming_task = self.evento_service.get_upcoming_events(5)
        pending_review_task = self._get_pending_review(can_review)
        comunidades_task = self._count_or_none(self.comunidade_repo.count_all, can_manage_comunidades)
        contribuintes_task = self._count_or_none(
            self.contribuinte_repo.count_all, can_manage_contributors
        )
        fotos_task = self._count_or_none(self.galeria_repo.count_fotos, can_manage_galeria)
        usuarios_task = self._count_or_none(self.user_repo.count_all, can_manage_users)
        activity_task = self._get_recent_activity(can_manage_users)

        results = await asyncio.gather(
            counts_task,
            upcoming_task,
            pending_review_task,
            comunidades_task,
            contribuintes_task,
            fotos_task,
            usuarios_task,
            activity_task,
        )
        counts = cast(dict[str, int], results[0])
        upcoming = cast(list[Evento], results[1])
        pending_review = cast(list[Evento], results[2])
        comunidades_count = cast("int | None", results[3])
        contribuintes_count = cast("int | None", results[4])
        fotos_count = cast("int | None", results[5])
        usuarios_count = cast("int | None", results[6])
        atividade_recente, atividade_usuarios = cast(
            "tuple[list[AuditLogRead], list[AuditUser]]", results[7]
        )

        return DashboardSummary(
            eventos=DashboardEventCounts(**counts),
            comunidades=comunidades_count,
            contribuintes=contribuintes_count,
            fotos=fotos_count,
            usuarios=usuarios_count,
            proximos_eventos=[EventoRead.model_validate(e) for e in upcoming],
            pendentes_revisao=[EventoRead.model_validate(e) for e in pending_review],
            atividade_recente=atividade_recente,
            atividade_usuarios=atividade_usuarios,
        )

    async def _count_or_none(
        self, count_fn: "Callable[[], Awaitable[int]]", enabled: bool
    ) -> int | None:
        if not enabled:
            return None
        return await count_fn()

    async def _get_pending_review(self, can_review: bool) -> list[Evento]:
        if not can_review:
            return []
        eventos, _ = await self.evento_service.get_events_page(
            page=1, page_size=5, status="em_analise"
        )
        return eventos

    async def _get_recent_activity(
        self, can_manage_users: bool
    ) -> tuple[list[AuditLogRead], list[AuditUser]]:
        if not can_manage_users:
            return [], []
        items, _ = await self.audit_service.get_audit_logs(page=1, page_size=5)
        users = await self.audit_service.get_audit_users()
        return (
            [AuditLogRead.model_validate(i) for i in items],
            [AuditUser(**u) for u in users],
        )
