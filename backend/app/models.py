from datetime import datetime, date, time

from sqlalchemy import CheckConstraint, DateTime, String, func, ForeignKey, Boolean, Date, Time, JSON, Numeric, UniqueConstraint
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_settings_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(120))
    manager_name: Mapped[str] = mapped_column(String(100), default="")
    timezone: Mapped[str] = mapped_column(String(60), default="America/Sao_Paulo")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(60))
    actor: Mapped[str] = mapped_column(String(100), default="Gerente local")
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (CheckConstraint("weekday >= 0 AND weekday <= 4 AND end_time > start_time", name="valid_shift"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    weekday: Mapped[int]
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)


class ShiftOverride(Base):
    __tablename__ = "shift_overrides"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    day: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(String(300))


class Closure(Base):
    __tablename__ = "closures"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    reason: Mapped[str] = mapped_column(String(300))


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(300))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (CheckConstraint("balance >= 0 AND minimum >= 0 AND unit_cost_cents >= 0", name="nonnegative_stock"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str] = mapped_column(String(10))
    minimum: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    unit_cost_cents: Mapped[int] = mapped_column(default=0)
    sale_price_cents: Mapped[int | None]
    price_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    price_source: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockLot(Base):
    __tablename__ = "stock_lots"
    __table_args__ = (CheckConstraint("balance >= 0", name="nonnegative_lot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    expiry: Mapped[date | None] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost_cents: Mapped[int]
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (UniqueConstraint("reversal_of", name="one_stock_reversal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"), index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("stock_lots.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    kind: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(500))
    unit_cost_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[int | None]
    reversal_of: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"))


class InventoryCount(Base):
    __tablename__ = "inventory_counts"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"))
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    counted: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    difference: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reason: Mapped[str] = mapped_column(String(500))
    movements: Mapped[list] = mapped_column(JSON)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    contact: Mapped[str] = mapped_column(String(150), default="")


class Purchase(Base):
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    requested_by: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseLine(Base):
    __tablename__ = "purchase_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"))
    ordered: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    received: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    estimated_cost_cents: Mapped[int]


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"
    __table_args__ = (UniqueConstraint('supplier_id', 'document', name='unique_supplier_document'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    document: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_cents: Mapped[int]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80))
    amount_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    due_date: Mapped[date | None] = mapped_column(Date)
    paid_by: Mapped[str] = mapped_column(String(30))
    payee: Mapped[str] = mapped_column(String(120))
    document: Mapped[str] = mapped_column(String(150))
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_receipts.id"), unique=True)
    voided: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpensePayment(Base):
    __tablename__ = "expense_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), index=True)
    amount_cents: Mapped[int]
    method: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reference: Mapped[str] = mapped_column(String(150), unique=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
