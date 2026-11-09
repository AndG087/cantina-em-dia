"""Retificações de custo sem sobrescrever o histórico."""
from alembic import op
import sqlalchemy as sa

revision = '0012_cost_revisions'
down_revision = '0011_price_rules'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('cost_revisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lot_id', sa.Integer(), sa.ForeignKey('stock_lots.id'), nullable=False),
        sa.Column('previous_cost_cents', sa.Numeric(18, 6), nullable=False),
        sa.Column('previous_known', sa.Boolean(), nullable=False),
        sa.Column('unit_cost_cents', sa.Numeric(18, 6), nullable=False),
        sa.Column('document', sa.String(300), nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('impact', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('unit_cost_cents >= 0 AND previous_cost_cents >= 0', name='nonnegative_cost_revision'))
    op.create_index('ix_cost_revisions_lot_id', 'cost_revisions', ['lot_id'])


def downgrade():
    op.drop_table('cost_revisions')
