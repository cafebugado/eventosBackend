import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evento_tag import EventoTag


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (
        CheckConstraint(
            "periodo IN ('Matinal','Diurno','Vespertino','Noturno')",
            name="ck_eventos_periodo",
        ),
        CheckConstraint(
            "status IN ('rascunho','publicado','arquivado','em_analise','recusado')",
            name="ck_eventos_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_evento: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    horario: Mapped[str] = mapped_column(Text, nullable=False)
    dia_semana: Mapped[str] = mapped_column(Text, nullable=False)
    periodo: Mapped[str | None] = mapped_column(String, nullable=True)
    link: Mapped[str] = mapped_column(Text, nullable=False)
    imagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    modalidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    endereco: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="publicado", index=True)
    # FK logica para auth.users(id) (schema gerenciado pelo Supabase Auth, sem constraint local)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evento_tags: Mapped[list["EventoTag"]] = relationship(
        back_populates="evento", cascade="all, delete-orphan"
    )
