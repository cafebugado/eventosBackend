"""Adiciona linkedin_url e data_nascimento em user_profiles; adiciona role participante

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("linkedin_url", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("data_nascimento", sa.Date(), nullable=True))

    # Adiciona 'participante' ao enum app_role (nome definido no modelo UserRole)
    op.execute("ALTER TYPE app_role ADD VALUE IF NOT EXISTS 'participante'")


def downgrade() -> None:
    op.drop_column("user_profiles", "data_nascimento")
    op.drop_column("user_profiles", "linkedin_url")
    # Nota: PostgreSQL nao suporta remover valores de enum sem recriar o tipo
