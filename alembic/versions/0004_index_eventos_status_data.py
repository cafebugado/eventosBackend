"""Adiciona indice composto (status, data_evento) na tabela eventos

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-28
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_eventos_status_data_evento",
        "eventos",
        ["status", "data_evento"],
    )


def downgrade() -> None:
    op.drop_index("ix_eventos_status_data_evento", table_name="eventos")
