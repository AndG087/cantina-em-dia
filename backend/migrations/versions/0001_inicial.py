"""Estrutura inicial no MySQL: calendário da escola, compras e estoque, caixa, despesas e relatório semanal."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0001_inicial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('cash_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('reviewed_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cash_reviews_day'), 'cash_reviews', ['day'], unique=False)
    op.create_table('cash_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('opened_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('opened_by', sa.String(length=100), nullable=False),
    sa.Column('opening_cents', sa.Integer(), nullable=False),
    sa.Column('open_guard', sa.Integer(), nullable=True),
    sa.Column('closed_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('closed_by', sa.String(length=100), nullable=False),
    sa.Column('cash_sales_cents', sa.Integer(), nullable=True),
    sa.Column('pix_cents', sa.Integer(), nullable=True),
    sa.Column('card_cents', sa.Integer(), nullable=True),
    sa.Column('withdrawals_cents', sa.Integer(), nullable=True),
    sa.Column('counted_cents', sa.Integer(), nullable=True),
    sa.Column('expected_cents', sa.Integer(), nullable=True),
    sa.Column('difference_cents', sa.Integer(), nullable=True),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('open_guard', name='one_open_cash_session')
    )
    op.create_index(op.f('ix_cash_sessions_opened_at'), 'cash_sessions', ['opened_at'], unique=False)
    op.create_table('expense_alert_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alert_key', sa.String(length=120), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alert_key')
    )
    op.create_table('school_calendar_checks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('checked_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.Column('source', sa.String(length=300), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('school_courses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('shift', sa.String(length=20), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('weekdays', sa.JSON(), nullable=False),
    sa.Column('students', sa.Integer(), nullable=True),
    sa.Column('source', sa.String(length=300), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.Column('cancelled_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('cancel_reason', sa.String(length=500), nullable=False),
    sa.CheckConstraint('ends_on >= starts_on AND (students IS NULL OR students >= 0)', name='valid_school_course'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('school_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('effect', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=300), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.Column('cancelled_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('cancel_reason', sa.String(length=500), nullable=False),
    sa.CheckConstraint('ends_on >= starts_on', name='valid_school_event'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stock_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('unit', sa.String(length=10), nullable=False),
    sa.Column('minimum', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.CheckConstraint('minimum >= 0', name='nonnegative_minimum'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('suppliers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('weekly_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('week_start', 'version', name='unique_weekly_report_version')
    )
    op.create_index(op.f('ix_weekly_reports_week_start'), 'weekly_reports', ['week_start'], unique=False)
    op.create_table('inventory_counts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('counted_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('expected', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('counted', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('difference', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['stock_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_counts_counted_at'), 'inventory_counts', ['counted_at'], unique=False)
    op.create_table('purchases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('supplier_id', sa.Integer(), nullable=False),
    sa.Column('requested_by', sa.String(length=100), nullable=False),
    sa.Column('note', sa.String(length=1000), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=False),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('purchase_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('purchase_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('ordered', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('received', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('estimated_cost_cents', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['stock_items.id'], ),
    sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_lines_purchase_id'), 'purchase_lines', ['purchase_id'], unique=False)
    op.create_table('purchase_receipts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('purchase_id', sa.Integer(), nullable=False),
    sa.Column('supplier_id', sa.Integer(), nullable=False),
    sa.Column('document', sa.String(length=120), nullable=False),
    sa.Column('occurred_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('total_cents', sa.Integer(), nullable=False),
    sa.Column('invoice_total_cents', sa.Integer(), nullable=False),
    sa.Column('invoice_note', sa.String(length=500), nullable=False),
    sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('supplier_id', 'document', name='unique_supplier_document')
    )
    op.create_index(op.f('ix_purchase_receipts_occurred_at'), 'purchase_receipts', ['occurred_at'], unique=False)
    op.create_table('expenses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('amount_cents', sa.Integer(), nullable=False),
    sa.Column('occurred_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('payee', sa.String(length=120), nullable=False),
    sa.Column('document', sa.String(length=150), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['receipt_id'], ['purchase_receipts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt_id')
    )
    op.create_index(op.f('ix_expenses_occurred_at'), 'expenses', ['occurred_at'], unique=False)
    op.create_table('purchase_receipt_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('unit_cost_cents', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['stock_items.id'], ),
    sa.ForeignKeyConstraint(['receipt_id'], ['purchase_receipts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_receipt_lines_item_id'), 'purchase_receipt_lines', ['item_id'], unique=False)
    op.create_index(op.f('ix_purchase_receipt_lines_receipt_id'), 'purchase_receipt_lines', ['receipt_id'], unique=False)
    op.create_table('stock_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('occurred_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('receipt_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['item_id'], ['stock_items.id'], ),
    sa.ForeignKeyConstraint(['receipt_id'], ['purchase_receipts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_movements_item_id'), 'stock_movements', ['item_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_occurred_at'), 'stock_movements', ['occurred_at'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_stock_movements_occurred_at'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_item_id'), table_name='stock_movements')
    op.drop_table('stock_movements')
    op.drop_index(op.f('ix_purchase_receipt_lines_receipt_id'), table_name='purchase_receipt_lines')
    op.drop_index(op.f('ix_purchase_receipt_lines_item_id'), table_name='purchase_receipt_lines')
    op.drop_table('purchase_receipt_lines')
    op.drop_index(op.f('ix_expenses_occurred_at'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_purchase_receipts_occurred_at'), table_name='purchase_receipts')
    op.drop_table('purchase_receipts')
    op.drop_index(op.f('ix_purchase_lines_purchase_id'), table_name='purchase_lines')
    op.drop_table('purchase_lines')
    op.drop_table('purchases')
    op.drop_index(op.f('ix_inventory_counts_counted_at'), table_name='inventory_counts')
    op.drop_table('inventory_counts')
    op.drop_index(op.f('ix_weekly_reports_week_start'), table_name='weekly_reports')
    op.drop_table('weekly_reports')
    op.drop_table('suppliers')
    op.drop_table('stock_items')
    op.drop_table('school_events')
    op.drop_table('school_courses')
    op.drop_table('school_calendar_checks')
    op.drop_table('expense_alert_notes')
    op.drop_index(op.f('ix_cash_sessions_opened_at'), table_name='cash_sessions')
    op.drop_table('cash_sessions')
    op.drop_index(op.f('ix_cash_reviews_day'), table_name='cash_reviews')
    op.drop_table('cash_reviews')
