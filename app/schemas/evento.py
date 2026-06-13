import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

Periodo = Literal["Matinal", "Diurno", "Vespertino", "Noturno"]
EventoStatus = Literal["rascunho", "publicado", "arquivado"]

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
    pass


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
        if value is not None and not _DATA_EVENTO_RE.match(value):
            raise ValueError("data_evento deve estar no formato DD/MM/YYYY")
        return value


class EventoRead(EventoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime


class EventoWithTags(EventoRead):
    tags: list["TagRead"] = []


class EventoStats(BaseModel):
    total: int
    publicados: int
    rascunhos: int
    noturno: int
    diurno: int


from app.schemas.tag import TagRead  # noqa: E402

EventoWithTags.model_rebuild()
