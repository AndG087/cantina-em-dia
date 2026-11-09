"""Preços com vigência e origem documentada."""
from alembic import op
import sqlalchemy as sa

revision = '0011_price_rules'
down_revision = '0010_backups'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('price_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('stock_items.id'), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=True),
        sa.Column('locked', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(300), nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('price_cents IS NULL OR price_cents >= 0', name='nonnegative_price_rule'))
    op.create_index('ix_price_rules_item_id', 'price_rules', ['item_id'])
    op.create_index('ix_price_rules_effective_from', 'price_rules', ['effective_from'])
    op.execute("""INSERT INTO price_rules(item_id,effective_from,price_cents,locked,source,reason)
        SELECT id, '1900-01-01T00:00:00Z', sale_price_cents,price_locked,
        COALESCE(NULLIF(price_source,''),'Cadastro inicial sem documento informado'),'Preço inicial preservado na migração'
        FROM stock_items WHERE kind='product'""")


def downgrade():
    op.drop_table('price_rules')
