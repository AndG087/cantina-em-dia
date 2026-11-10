"""Fechamento do caixa com vendas no vale-refeição / alimentação."""
from alembic import op
import sqlalchemy as sa

revision = '0002_vale_refeicao'
down_revision = '0001_inicial'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cash_sessions', sa.Column('voucher_cents', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('cash_sessions', 'voucher_cents')
