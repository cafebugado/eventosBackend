"""Expande user_profiles: dados pessoais, profissionais, provider e idade minima

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("genero", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("whatsapp", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("provider", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("cargo_atual", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("empresa", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("area_atuacao", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("nivel_experiencia", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("portfolio_url", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("bio", sa.Text(), nullable=True))

    op.create_check_constraint(
        "ck_user_profiles_idade_minima",
        "user_profiles",
        "data_nascimento IS NULL OR data_nascimento <= CURRENT_DATE - INTERVAL '18 years'",
    )
    op.create_check_constraint(
        "ck_user_profiles_genero",
        "user_profiles",
        "genero IS NULL OR genero IN ('Masculino', 'Feminino', 'Outro', 'Prefiro não informar')",
    )
    op.create_check_constraint(
        "ck_user_profiles_nivel_experiencia",
        "user_profiles",
        "nivel_experiencia IS NULL OR nivel_experiencia IN "
        "('Estagiário', 'Júnior', 'Pleno', 'Sênior', 'Especialista/Staff')",
    )
    op.create_check_constraint(
        "ck_user_profiles_provider",
        "user_profiles",
        "provider IS NULL OR provider IN ('email', 'google', 'github')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_profiles_provider", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_nivel_experiencia", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_genero", "user_profiles", type_="check")
    op.drop_constraint("ck_user_profiles_idade_minima", "user_profiles", type_="check")

    op.drop_column("user_profiles", "bio")
    op.drop_column("user_profiles", "portfolio_url")
    op.drop_column("user_profiles", "nivel_experiencia")
    op.drop_column("user_profiles", "area_atuacao")
    op.drop_column("user_profiles", "empresa")
    op.drop_column("user_profiles", "cargo_atual")
    op.drop_column("user_profiles", "provider")
    op.drop_column("user_profiles", "whatsapp")
    op.drop_column("user_profiles", "genero")
