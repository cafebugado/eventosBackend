"""Adiciona status de revisao aos eventos

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_eventos_status", "eventos", type_="check")
    op.create_check_constraint(
        "ck_eventos_status",
        "eventos",
        "status IN ('rascunho','publicado','arquivado','em_analise','recusado')",
    )


def downgrade() -> None:
    op.execute("UPDATE eventos SET status = 'rascunho' WHERE status IN ('em_analise','recusado')")
    op.drop_constraint("ck_eventos_status", "eventos", type_="check")
    op.create_check_constraint(
        "ck_eventos_status",
        "eventos",
        "status IN ('rascunho','publicado','arquivado')",
    )
