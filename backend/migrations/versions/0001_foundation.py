"""Configuração inicial, sem dados operacionais inventados."""
from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_name", sa.String(100), nullable=False),
        sa.Column("location", sa.String(120), nullable=False),
        sa.Column("manager_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("timezone", sa.String(60), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="single_settings_row"),
    )
    op.bulk_insert(table, [{"id": 1, "business_name": "Cantina em Dia", "location": "SENAI · Paulista"}])


def downgrade():
    op.drop_table("app_settings")
