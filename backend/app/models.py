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
    cost_known: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')


class StockLot(Base):
    __tablename__ = "stock_lots"
    __table_args__ = (CheckConstraint("balance >= 0", name="nonnegative_lot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    expiry: Mapped[date | None] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost_cents: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cost_known: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (UniqueConstraint("reversal_of", name="one_stock_reversal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"), index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("stock_lots.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    kind: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(500))
    unit_cost_cents: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reference_type: Mapped[str | None] = mapped_column(String(40))
    reference_id: Mapped[int | None]
    reversal_of: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id"))
    cost_known: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')


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
    purpose: Mapped[str] = mapped_column(String(40), default='operating', server_default='operating')


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
    cash_session_id: Mapped[int | None] = mapped_column(ForeignKey('cash_sessions.id'))


class CashSession(Base):
    __tablename__ = 'cash_sessions'
    __table_args__ = (UniqueConstraint('open_guard', name='one_open_cash_session'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    opened_by_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    opening_cents: Mapped[int]
    open_guard: Mapped[int | None] = mapped_column(default=1)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counted_cents: Mapped[int | None]
    expected_close_cents: Mapped[int | None]
    difference_cents: Mapped[int | None]
    note: Mapped[str] = mapped_column(String(500))


class CashEntry(Base):
    __tablename__ = 'cash_entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('cash_sessions.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    amount_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(500))
    reference: Mapped[str] = mapped_column(String(150), unique=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CashHandover(Base):
    __tablename__ = 'cash_handovers'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('cash_sessions.id'))
    from_employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    to_employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_cents: Mapped[int]
    counted_cents: Mapped[int]
    difference_cents: Mapped[int]
    reason: Mapped[str] = mapped_column(String(500))


class Sale(Base):
    __tablename__ = 'sales'
    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    total_cents: Mapped[int]
    discount_cents: Mapped[int] = mapped_column(default=0)
    cost_cents: Mapped[int]
    cashier_id: Mapped[int | None] = mapped_column(ForeignKey('employees.id'))
    note: Mapped[str] = mapped_column(String(500))
    external_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    stock_applied: Mapped[bool] = mapped_column(Boolean, default=True)
    voided: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stock_returned: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cost_known: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')


class SaleLine(Base):
    __tablename__ = 'sale_lines'
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey('sales.id'), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price_cents: Mapped[int]


class SalePayment(Base):
    __tablename__ = 'sale_payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey('sales.id'), index=True)
    method: Mapped[str] = mapped_column(String(20))
    amount_cents: Mapped[int]
    due_date: Mapped[date | None] = mapped_column(Date)


class Settlement(Base):
    __tablename__ = 'settlements'
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey('sale_payments.id'), index=True)
    gross_cents: Mapped[int]
    fee_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reference: Mapped[str] = mapped_column(String(150), unique=True)


class SaleRefund(Base):
    __tablename__ = 'sale_refunds'
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey('sale_payments.id'))
    amount_cents: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cash_session_id: Mapped[int | None] = mapped_column(ForeignKey('cash_sessions.id'))
    reference: Mapped[str] = mapped_column(String(150), unique=True)


class Recipe(Base):
    __tablename__ = 'recipes'
    __table_args__ = (UniqueConstraint('product_id', 'version', name='unique_recipe_version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int]
    yield_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    instructions: Mapped[str] = mapped_column(String(3000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeLine(Base):
    __tablename__ = 'recipe_lines'
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class ProductionRun(Base):
    __tablename__ = 'production_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    planned_output: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    actual_output: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    input_source: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(500))
    total_cost_cents: Mapped[int]
    voided: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionInput(Base):
    __tablename__ = 'production_inputs'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('production_runs.id'))
    item_id: Mapped[int] = mapped_column(ForeignKey('stock_items.id'))
    expected: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class PortionStandard(Base):
    __tablename__ = 'portion_standards'
    __table_args__ = (UniqueConstraint('recipe_id', 'component', name='unique_portion_component'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'))
    component: Mapped[str] = mapped_column(String(100))
    target_g: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    tolerance_g: Mapped[Decimal] = mapped_column(Numeric(12, 3))


class PortionSample(Base):
    __tablename__ = 'portion_samples'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('production_runs.id'))
    standard_id: Mapped[int] = mapped_column(ForeignKey('portion_standards.id'))
    measured_g: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(300))


class Goal(Base):
    __tablename__ = 'goals'
    __table_args__ = (UniqueConstraint('month', 'version', name='unique_month_goal_version'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    version: Mapped[int]
    basis: Mapped[str] = mapped_column(String(40))
    target_cents: Mapped[int]
    agreement: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoalAssessment(Base):
    __tablename__ = 'goal_assessments'
    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey('goals.id'))
    basis_cents: Mapped[int]
    variable_cents: Mapped[int]
    owner_approved: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(String(500))
    report: Mapped[dict] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
