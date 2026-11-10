"""Rotina de acompanhamento: calendário escolar, conferências e relatório semanal."""
from alembic import op
import sqlalchemy as sa

revision = '0014_rotina_acompanhamento'
down_revision = '0013_lot_lookup_index'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('purchase_receipts', sa.Column('invoice_total_cents', sa.Integer(), nullable=True))
    op.add_column('purchase_receipts', sa.Column('invoice_note', sa.String(500), server_default='', nullable=False))
    op.create_table('school_courses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('shift', sa.String(20), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('weekdays', sa.JSON(), nullable=False),
        sa.Column('students', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(300), nullable=False),
        sa.Column('note', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_reason', sa.String(500), server_default='', nullable=False),
        sa.CheckConstraint('ends_on >= starts_on AND (students IS NULL OR students >= 0)', name='valid_school_course'))
    op.create_table('school_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('kind', sa.String(30), nullable=False),
        sa.Column('title', sa.String(150), nullable=False),
        sa.Column('starts_on', sa.Date(), nullable=False),
        sa.Column('ends_on', sa.Date(), nullable=False),
        sa.Column('effect', sa.String(20), nullable=False),
        sa.Column('source', sa.String(300), nullable=False),
        sa.Column('note', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_reason', sa.String(500), server_default='', nullable=False),
        sa.CheckConstraint('ends_on >= starts_on', name='valid_school_event'))
    op.create_index('ix_school_events_starts_on', 'school_events', ['starts_on'])
    op.create_index('ix_school_events_ends_on', 'school_events', ['ends_on'])
    op.create_table('school_calendar_checks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('source', sa.String(300), nullable=False),
        sa.Column('note', sa.String(1000), nullable=False))
    op.create_table('cash_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('note', sa.String(1000), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_cash_reviews_day', 'cash_reviews', ['day'])
    op.create_table('expense_alert_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('alert_key', sa.String(120), nullable=False, unique=True),
        sa.Column('note', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('weekly_reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(1000), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('week_start', 'version', name='unique_weekly_report_version'))
    op.create_index('ix_weekly_reports_week_start', 'weekly_reports', ['week_start'])


def downgrade():
    op.drop_table('weekly_reports')
    op.drop_table('expense_alert_notes')
    op.drop_index('ix_cash_reviews_day', table_name='cash_reviews')
    op.drop_table('cash_reviews')
    op.drop_table('school_calendar_checks')
    op.drop_table('school_events')
    op.drop_table('school_courses')
    op.drop_column('purchase_receipts', 'invoice_note')
    op.drop_column('purchase_receipts', 'invoice_total_cents')
