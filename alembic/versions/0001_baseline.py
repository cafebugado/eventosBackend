"""Baseline - schema existente criado pelas migrations 001-018 do Supabase

Revision ID: 0001
Revises:
Create Date: 2026-06-12

Esta revisao nao executa DDL: o schema do Postgres ja existe (criado pelas
migrations SQL do projeto Supabase original). Apos configurar DATABASE_URL,
execute `alembic stamp 0001` para marcar o banco como atualizado sem
recriar as tabelas. Futuras evolucoes de schema devem ser criadas como
novas revisoes a partir desta baseline.
"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
