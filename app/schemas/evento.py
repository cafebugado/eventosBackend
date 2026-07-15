import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.event_date import parse_event_date

Periodo = Literal["Matinal", "Diurno", "Vespertino", "Noturno"]
EventoStatus = Literal["rascunho", "publicado", "arquivado", "em_analise", "recusado"]
EventoDateFilter = Literal["upcoming", "past"]

_DATA_EVENTO_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


class EventoBase(BaseModel):
    nome: str
    descricao: str | None = None
    data_evento: str
    horario: str
    dia_semana: str
    periodo: Periodo | None = None
    link: str
    imagem: str | None = None
    modalidade: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    status: EventoStatus = "publicado"

    @field_validator("data_evento")
    @classmethod
    def validate_data_evento(cls, value: str) -> str:
        if not _DATA_EVENTO_RE.match(value):
            raise ValueError("data_evento deve estar no formato DD/MM/YYYY")
        return value


class EventoCreate(EventoBase):
    @field_validator("data_evento")
    @classmethod
    def validate_data_evento_not_past(cls, value: str) -> str:
        event_date = parse_event_date(value)
        if event_date is not None and event_date < date.today():
            raise ValueError("data_evento não pode ser uma data no passado")
        return value


class EventoUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    data_evento: str | None = None
    horario: str | None = None
    dia_semana: str | None = None
    periodo: Periodo | None = None
    link: str | None = None
    imagem: str | None = None
    modalidade: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    status: EventoStatus | None = None

    @field_validator("data_evento")
    @classmethod
    def validate_data_evento(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not _DATA_EVENTO_RE.match(value):
            raise ValueError("data_evento deve estar no formato DD/MM/YYYY")
        event_date = parse_event_date(value)
        if event_date is not None and event_date < date.today():
            raise ValueError("data_evento não pode ser uma data no passado")
        return value


class EventoRead(EventoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    created_by: uuid.UUID | None = None
    motivo_recusa: str | None = None
    created_at: datetime
    updated_at: datetime


class EventoRejectRequest(BaseModel):
    motivo: str = Field(..., min_length=10, max_length=500)

    @field_validator("motivo")
    @classmethod
    def validate_motivo(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 10:
            raise ValueError("motivo deve ter ao menos 10 caracteres")
        return trimmed


class EventoPage(BaseModel):
    items: list[EventoRead]
    total: int
    page: int
    page_size: int


class EventoWithTags(EventoRead):
    tags: list["TagRead"] = []


class EventoStats(BaseModel):
    total: int
    publicados: int
    rascunhos: int
    noturno: int
    diurno: int


class DiaSemanaCount(BaseModel):
    dia_semana: str
    total: int
    percentual: float


class PeriodoCount(BaseModel):
    periodo: str
    total: int


class ModalidadeCount(BaseModel):
    modalidade: str
    total: int


class CidadeCount(BaseModel):
    cidade: str
    estado: str | None
    total: int


class StatusCount(BaseModel):
    status: str
    total: int


class TagCount(BaseModel):
    tag_id: uuid.UUID
    nome: str
    cor: str
    total: int


class MonthlyCount(BaseModel):
    ano_mes: str
    total: int


class EventoMetrics(BaseModel):
    total_eventos: int
    media_eventos_por_semana: float
    por_dia_semana: list[DiaSemanaCount]
    por_periodo: list[PeriodoCount]
    por_modalidade: list[ModalidadeCount]
    por_cidade: list[CidadeCount]
    por_status: list[StatusCount]
    top_tags: list[TagCount]
    evolucao_mensal: list[MonthlyCount]


from app.schemas.tag import TagRead  # noqa: E402

EventoWithTags.model_rebuild()
