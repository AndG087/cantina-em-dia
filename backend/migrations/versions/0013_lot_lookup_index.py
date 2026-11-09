"""Índice para consultar o custo do lote sem varrer os movimentos."""
from alembic import op

revision = '0013_lot_lookup_index'
down_revision = '0012_cost_revisions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_stock_movements_lot_id', 'stock_movements', ['lot_id'])


def downgrade():
    op.drop_index('ix_stock_movements_lot_id', table_name='stock_movements')
