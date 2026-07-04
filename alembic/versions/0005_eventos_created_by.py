"""Adiciona criador aos eventos

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("eventos", sa.Column("created_by", sa.UUID(), nullable=True))
    op.create_index("ix_eventos_created_by", "eventos", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_eventos_created_by", table_name="eventos")
    op.drop_column("eventos", "created_by")
