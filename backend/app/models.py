from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def created_at():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# Calendário da escola

class SchoolCourse(Base):
    __tablename__ = 'school_courses'
    __table_args__ = (CheckConstraint('ends_on >= starts_on AND (students IS NULL OR students >= 0)', name='valid_school_course'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    shift: Mapped[str] = mapped_column(String(20))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    weekdays: Mapped[list] = mapped_column(JSON)
    students: Mapped[int | None]
    source: Mapped[str] = mapped_column(String(300))
    note: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str] = mapped_column(String(500), default='')


class SchoolEvent(Base):
    __tablename__ = 'school_events'
    __table_args__ = (CheckConstraint('ends_on >= starts_on', name='valid_school_event'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(150))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    effect: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(300))
    note: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at()
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str] = mapped_column(String(500), default='')


class SchoolCalendarCheck(Base):
    __tablename__ = 'school_calendar_checks'
    id: Mapped[int] = mapped_column(primary_key=True)
    checked_at: Mapped[datetime] = created_at()
    source: Mapped[str] = mapped_column(String(300))
    note: Mapped[str] = mapped_column(String(1000))


# Compras e estoque

class Supplier(Base):
    __tablename__ = 'suppliers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class StockItem(Base):
    __tablename__ = 'stock_items'
    __table_args__ = (CheckConstraint('minimum >= 0', name='nonnegative_minimum'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(10))
    minimum: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Purchase(Base):
    __tablename__ = 'purchases'
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'))
    requested_by: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default='open')
    created_at: Mapped[datetime] = created_at()


class PurchaseLine(Base):
    __tablename__ = 'purchase_lines'
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey('purchases.id'), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    ordered: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    received: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    estimated_cost_cents: Mapped[int]


class PurchaseReceipt(Base):
    __tablename__ = 'purchase_receipts'
    __table_args__ = (UniqueConstraint('supplier_id', 'document', name='unique_supplier_document'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey('purchases.id'))
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'))
    document: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    total_cents: Mapped[int]
    invoice_total_cents: Mapped[int]
    invoice_note: Mapped[str] = mapped_column(String(500))


class PurchaseReceiptLine(Base):
    __tablename__ = 'purchase_receipt_lines'
    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey('purchase_receipts.id'), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost_cents: Mapped[int]


class StockMovement(Base):
    __tablename__ = 'stock_movements'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    kind: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey('purchase_receipts.id'))


class InventoryCount(Base):
    __tablename__ = 'inventory_counts'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expected: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    counted: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    difference: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    note: Mapped[str] = mapped_column(String(500))


# Despesas

class Expense(Base):
    __tablename__ = 'expenses'
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80))
    amount_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payee: Mapped[str] = mapped_column(String(120))
    document: Mapped[str] = mapped_column(String(150))
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey('purchase_receipts.id'), unique=True)


class ExpenseAlertNote(Base):
    __tablename__ = 'expense_alert_notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_key: Mapped[str] = mapped_column(String(120), unique=True)
    note: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = created_at()


# Caixa

class CashSession(Base):
    """Uma abertura e o fechamento correspondente, com os totais informados no fim do dia."""
    __tablename__ = 'cash_sessions'
    __table_args__ = (UniqueConstraint('open_guard', name='one_open_cash_session'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    opened_by: Mapped[str] = mapped_column(String(100))
    opening_cents: Mapped[int]
    open_guard: Mapped[int | None] = mapped_column(default=1)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[str] = mapped_column(String(100), default='')
    cash_sales_cents: Mapped[int | None]
    pix_cents: Mapped[int | None]
    card_cents: Mapped[int | None]
    withdrawals_cents: Mapped[int | None]
    counted_cents: Mapped[int | None]
    expected_cents: Mapped[int | None]
    difference_cents: Mapped[int | None]
    note: Mapped[str] = mapped_column(String(1000), default='')


class CashReview(Base):
    __tablename__ = 'cash_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(1000))
    fingerprint: Mapped[str] = mapped_column(String(64))
    reviewed_at: Mapped[datetime] = created_at()


# Relatório semanal

class WeeklyReport(Base):
    __tablename__ = 'weekly_reports'
    __table_args__ = (UniqueConstraint('week_start', 'version', name='unique_weekly_report_version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    version: Mapped[int]
    note: Mapped[str] = mapped_column(String(1000))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at()
