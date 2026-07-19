from pydantic import BaseModel

from app.schemas.audit import AuditLogRead, AuditUser
from app.schemas.evento import EventoRead


class DashboardEventCounts(BaseModel):
    total: int
    hoje: int
    semana: int
    mes: int
    ano: int
    diurno: int
    noturno: int
    meus_eventos: int


class DashboardSummary(BaseModel):
    eventos: DashboardEventCounts
    comunidades: int | None = None
    contribuintes: int | None = None
    fotos: int | None = None
    usuarios: int | None = None
    proximos_eventos: list[EventoRead]
    pendentes_revisao: list[EventoRead]
    atividade_recente: list[AuditLogRead]
    atividade_usuarios: list[AuditUser]
