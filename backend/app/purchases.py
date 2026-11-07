from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import get_session
from .domain import audit, aware, get_or_404, lock, rows
from .inventory import Qty, change_stock, valid_quantity, ReasonIn
from .models import Supplier, Purchase, PurchaseLine, PurchaseReceipt, StockItem, Expense, ExpensePayment
from .team import Input

router = APIRouter(prefix='/api', tags=['Compras e despesas'])
DB = Annotated[Session, Depends(get_session)]
Money = Annotated[int, Field(ge=0, le=2_000_000_000)]


class SupplierIn(Input):
    name: str = Field(min_length=2, max_length=120)
    contact: str = Field(default='', max_length=150)


class PurchaseLineIn(Input):
    item_id: int
    quantity: Qty = Field(gt=0)
    unit_cost_cents: Money


class PurchaseIn(Input):
    supplier_id: int
    requested_by: str = Field(min_length=2, max_length=100)
    note: str = Field(default='', max_length=500)
    lines: list[PurchaseLineIn] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_items(self):
        if len({line.item_id for line in self.lines}) != len(self.lines):
            raise ValueError('Cada item deve aparecer uma única vez no pedido.')
        return self


class ReceiptLineIn(PurchaseLineIn):
    lot_code: str = Field(default='', max_length=100)
    expiry: date | None = None


class ReceiptIn(Input):
    document: str = Field(min_length=1, max_length=120)
    occurred_at: datetime
    paid_by: Literal['employee', 'cantina', 'owner', 'unpaid']
    payer_name: str = Field(default='', max_length=120)
    payment_method: Literal['pix', 'bank'] = 'pix'
    lines: list[ReceiptLineIn] = Field(min_length=1, max_length=100)


class ExpenseIn(Input):
    description: str = Field(min_length=3, max_length=300)
    category: str = Field(min_length=2, max_length=80)
    amount_cents: Money = Field(gt=0)
    occurred_at: datetime
    due_date: date | None = None
    paid_by: Literal['employee', 'cantina', 'owner', 'unpaid']
    payee: str = Field(min_length=2, max_length=120)
    document: str = Field(min_length=1, max_length=150)


class PaymentIn(Input):
    amount_cents: Money = Field(gt=0)
    method: Literal['pix', 'bank', 'cash']
    source: Literal['cantina', 'owner'] = 'cantina'
    occurred_at: datetime
    reference: str = Field(min_length=3, max_length=150)
    cash_session_id: int | None = None


def paid_total(db, key):
    return db.scalar(select(func.coalesce(func.sum(ExpensePayment.amount_cents), 0)).where(ExpensePayment.expense_id == key))


def record_payment(db, expense, data):
    aware(data.occurred_at); lock(db, 402)
    db.refresh(expense)
    if expense.voided:
        raise HTTPException(409, 'Despesa cancelada.')
    if data.occurred_at < expense.occurred_at:
        raise HTTPException(422, 'Pagamento não pode ser anterior à despesa.')
    if db.scalar(select(ExpensePayment.id).where(ExpensePayment.reference == data.reference)):
        raise HTTPException(409, 'Comprovante de pagamento já registrado.')
    if paid_total(db, expense.id) + data.amount_cents > expense.amount_cents:
        raise HTTPException(409, 'Pagamento excede o saldo pendente.')
    payment = ExpensePayment(expense_id=expense.id, **data.model_dump())
    db.add(payment); db.flush()
    if data.method == 'cash':
        if data.cash_session_id is None or data.source != 'cantina':
            raise HTTPException(422, 'Pagamento em espécie exige um caixa aberto e origem cantina.')
        from .finance import add_cash_entry
        add_cash_entry(db, data.cash_session_id, 'expense', -data.amount_cents, data.occurred_at, f'Despesa #{expense.id}: {expense.description}', f'expense_payment:{payment.id}')
    audit(db, 'expense_payment', payment.id, 'paid', data.model_dump())
    return payment


@router.get('/suppliers')
def suppliers(db: DB):
    return rows(db, Supplier, 2000)


@router.post('/suppliers', status_code=201)
def create_supplier(data: SupplierIn, db: DB):
    lock(db, 401)
    if db.scalar(select(Supplier.id).where(Supplier.name == data.name)):
        raise HTTPException(409, 'Fornecedor já cadastrado.')
    row = Supplier(**data.model_dump()); db.add(row); db.flush(); audit(db, 'supplier', row.id, 'created', data.model_dump())
    db.commit(); return row


@router.get('/purchases')
def purchases(db: DB):
    result = []
    for purchase in rows(db, Purchase):
        lines = db.scalars(select(PurchaseLine).where(PurchaseLine.purchase_id == purchase.id).order_by(PurchaseLine.id)).all()
        result.append({'id': purchase.id, 'supplier_id': purchase.supplier_id, 'requested_by': purchase.requested_by, 'note': purchase.note, 'status': purchase.status, 'created_at': purchase.created_at, 'lines': lines})
    return result


@router.post('/purchases', status_code=201)
def create_purchase(data: PurchaseIn, db: DB):
    get_or_404(db, Supplier, data.supplier_id)
    purchase = Purchase(**data.model_dump(exclude={'lines'})); db.add(purchase); db.flush()
    for line in data.lines:
        item = get_or_404(db, StockItem, line.item_id); valid_quantity(item, line.quantity)
        db.add(PurchaseLine(purchase_id=purchase.id, item_id=line.item_id, ordered=line.quantity, estimated_cost_cents=line.unit_cost_cents))
    audit(db, 'purchase', purchase.id, 'requested', data.model_dump()); db.commit()
    return {'id': purchase.id}


@router.post('/purchases/{key}/approve')
def approve_purchase(key: int, db: DB):
    lock(db, 401); purchase = get_or_404(db, Purchase, key)
    if purchase.status != 'requested':
        raise HTTPException(409, 'O pedido não está aguardando aprovação.')
    purchase.status = 'approved'; audit(db, 'purchase', key, 'approved', {}); db.commit()
    return purchase


@router.post('/purchases/{key}/receive', status_code=201)
def receive_purchase(key: int, data: ReceiptIn, db: DB):
    aware(data.occurred_at); lock(db, 401)
    purchase = get_or_404(db, Purchase, key)
    if purchase.status not in {'approved', 'partial'}:
        raise HTTPException(409, 'Aprove o pedido antes de receber mercadorias.')
    if len({line.item_id for line in data.lines}) != len(data.lines):
        raise HTTPException(422, 'Item repetido no recebimento.')
    if data.paid_by == 'employee' and len(data.payer_name) < 2:
        raise HTTPException(422, 'Identifique quem adiantou o dinheiro.')
    if db.scalar(select(PurchaseReceipt.id).where(PurchaseReceipt.supplier_id == purchase.supplier_id, PurchaseReceipt.document == data.document)):
        raise HTTPException(409, 'Esse documento do fornecedor já foi registrado.')
    total = sum(int((line.quantity * line.unit_cost_cents).quantize(Decimal(1), rounding=ROUND_HALF_UP)) for line in data.lines)
    if total > 2_000_000_000:
        raise HTTPException(422, 'Valor total acima do limite permitido.')
    receipt = PurchaseReceipt(purchase_id=key, supplier_id=purchase.supplier_id, document=data.document, occurred_at=data.occurred_at, total_cents=total)
    db.add(receipt); db.flush()
    for line in sorted(data.lines, key=lambda value: value.item_id):
        ordered = db.scalar(select(PurchaseLine).where(PurchaseLine.purchase_id == key, PurchaseLine.item_id == line.item_id))
        if not ordered or ordered.received + line.quantity > ordered.ordered:
            raise HTTPException(409, 'Quantidade recebida excede o pedido ou item não pertence a ele.')
        change_stock(db, line.item_id, line.quantity, 'incoming', f'Compra #{key} · {data.document}', data.occurred_at, lot_code=line.lot_code, expiry=line.expiry, unit_cost_cents=line.unit_cost_cents, reference_type='purchase_receipt', reference_id=receipt.id)
        ordered.received += line.quantity
    supplier = get_or_404(db, Supplier, purchase.supplier_id)
    expense = Expense(description=f'Compra #{key} · {supplier.name}', category='Mercadorias', amount_cents=total, occurred_at=data.occurred_at, paid_by=data.paid_by,
                      payee=data.payer_name if data.paid_by == 'employee' else supplier.name, document=data.document, receipt_id=receipt.id)
    db.add(expense); db.flush()
    if data.paid_by in {'cantina', 'owner'} and total:
        record_payment(db, expense, PaymentIn(amount_cents=total, method=data.payment_method, source=data.paid_by, occurred_at=data.occurred_at, reference=f'receipt:{receipt.id}:payment'))
    all_lines = db.scalars(select(PurchaseLine).where(PurchaseLine.purchase_id == key)).all()
    purchase.status = 'received' if all(line.received == line.ordered for line in all_lines) else 'partial'
    audit(db, 'receipt', receipt.id, 'received', data.model_dump()); db.commit()
    return {'receipt_id': receipt.id, 'expense_id': expense.id, 'total_cents': total, 'status': purchase.status}


@router.get('/expenses')
def expenses(db: DB):
    return [{'id': e.id, 'description': e.description, 'category': e.category, 'amount_cents': e.amount_cents, 'occurred_at': e.occurred_at,
             'due_date': e.due_date, 'paid_by': e.paid_by, 'payee': e.payee, 'document': e.document, 'receipt_id': e.receipt_id, 'voided': e.voided,
             'paid_cents': paid_total(db, e.id), 'pending_cents': 0 if e.voided else e.amount_cents - paid_total(db, e.id)} for e in rows(db, Expense)]


@router.post('/expenses', status_code=201)
def create_expense(data: ExpenseIn, db: DB):
    aware(data.occurred_at); lock(db, 402)
    if db.scalar(select(Expense.id).where(Expense.document == data.document, Expense.payee == data.payee, Expense.voided.is_(False))):
        raise HTTPException(409, 'Documento já lançado para esse favorecido. Confira antes de duplicar.')
    expense = Expense(**data.model_dump()); db.add(expense); db.flush()
    audit(db, 'expense', expense.id, 'created', data.model_dump()); db.commit()
    return expense


@router.post('/expenses/{key}/payments', status_code=201)
def payment(key: int, data: PaymentIn, db: DB):
    expense = get_or_404(db, Expense, key)
    payment = record_payment(db, expense, data); db.commit()
    return payment


@router.get('/expense-payments')
def payments(db: DB):
    return rows(db, ExpensePayment)


@router.post('/expenses/{key}/cancel')
def cancel_expense(key: int, data: ReasonIn, db: DB):
    lock(db, 402); expense = get_or_404(db, Expense, key)
    if expense.receipt_id or paid_total(db, key) or expense.voided:
        raise HTTPException(409, 'Só é possível cancelar uma despesa manual ainda não paga. Para mercadorias, preserve o vínculo com o recebimento.')
    expense.voided = True; audit(db, 'expense', key, 'cancelled', {'reason': data.reason}); db.commit()
    return expense
