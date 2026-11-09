from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import get_session
from .domain import audit, aware, get_or_404, lock, now, rows
from .models import CashSession, CashEntry, CashHandover, Sale, SaleLine, SalePayment, Settlement, SaleRefund, StockItem, StockMovement, Assignment
from .team import Input, assign, active_employee
from .inventory import Qty, change_stock, valid_quantity
from .purchases import Money
from .pricing import price_at

router = APIRouter(prefix='/api', tags=['Caixa e financeiro'])
DB = Annotated[Session, Depends(get_session)]


class OpenIn(Input):
    employee_id: int
    opened_at: datetime
    opening_cents: Money
    note: str = Field(min_length=3, max_length=500)


class CloseIn(Input):
    occurred_at: datetime
    counted_cents: Money
    reason: str = Field(min_length=3, max_length=500)


class HandoverIn(CloseIn):
    employee_id: int


class CashEntryIn(Input):
    kind: Literal['withdrawal', 'reinforcement']
    amount_cents: Money = Field(gt=0)
    occurred_at: datetime
    note: str = Field(min_length=3, max_length=500)


class SaleLineIn(Input):
    item_id: int
    quantity: Qty = Field(gt=0)
    unit_price_cents: Money


class SalePaymentIn(Input):
    method: Literal['cash', 'pix', 'debit', 'credit']
    amount_cents: Money = Field(gt=0)
    due_date: date | None = None


class SaleIn(Input):
    occurred_at: datetime
    cash_session_id: int | None = None
    note: str = Field(default='', max_length=500)
    discount_cents: Money = 0
    lines: list[SaleLineIn] = Field(min_length=1, max_length=100)
    payments: list[SalePaymentIn] = Field(min_length=1, max_length=10)
    external_id: str | None = Field(default=None, max_length=150)


class SettlementIn(Input):
    payment_id: int
    gross_cents: Money = Field(gt=0)
    fee_cents: Money
    occurred_at: datetime
    reference: str = Field(min_length=3, max_length=150)


class CancelSaleIn(Input):
    reason: str = Field(min_length=3, max_length=500)
    stock_returned: bool = False
    occurred_at: datetime


class RefundIn(Input):
    payment_id: int
    amount_cents: Money = Field(gt=0)
    occurred_at: datetime
    cash_session_id: int | None = None
    reference: str = Field(min_length=3, max_length=150)


def cash_session(db, key):
    lock(db, 501)
    row = db.scalar(select(CashSession).where(CashSession.id == key).with_for_update())
    if not row:
        raise HTTPException(404, 'Caixa não encontrado.')
    if row.closed_at:
        raise HTTPException(409, 'Caixa fechado. Reabra o último caixa para corrigir ou use o caixa atual.')
    return row


def expected_cash(db, session):
    return session.opening_cents + db.scalar(select(func.coalesce(func.sum(CashEntry.amount_cents), 0)).where(CashEntry.session_id == session.id))


def check_cash_time(db, session, instant):
    aware(instant)
    last_handover = db.scalar(select(func.max(CashHandover.occurred_at)).where(CashHandover.session_id == session.id))
    if instant < (last_handover or session.opened_at):
        raise HTTPException(409, 'Data anterior à abertura ou à última passagem conferida do caixa.')


def add_cash_entry(db, session_id, kind, amount, instant, note, reference):
    session = cash_session(db, session_id); check_cash_time(db, session, instant)
    if db.scalar(select(CashEntry.id).where(CashEntry.reference == reference)):
        raise HTTPException(409, 'Operação de caixa já registrada.')
    entry = CashEntry(session_id=session_id, kind=kind, amount_cents=amount, occurred_at=instant, note=note, reference=reference)
    db.add(entry); db.flush()
    balance = session.opening_cents
    for current in db.scalars(select(CashEntry).where(CashEntry.session_id == session_id).order_by(CashEntry.occurred_at, CashEntry.id)):
        balance += current.amount_cents
        if balance < 0:
            raise HTTPException(409, 'Movimento deixaria o dinheiro disponível no caixa negativo.')
    audit(db, 'cash_entry', entry.id, kind, {'amount_cents': amount, 'occurred_at': instant, 'note': note})
    return entry


def check_count_time(db, session, instant):
    check_cash_time(db, session, instant)
    latest = db.scalar(select(func.max(CashEntry.occurred_at)).where(CashEntry.session_id == session.id))
    if latest and latest > instant:
        raise HTTPException(409, 'Há movimentos posteriores a essa contagem. Revise o horário de corte.')


@router.get('/cash-sessions')
def cash_sessions(db: DB):
    return [{'id': c.id, 'opened_by_id': c.opened_by_id, 'employee_id': c.employee_id, 'opened_at': c.opened_at, 'opening_cents': c.opening_cents,
             'closed_at': c.closed_at, 'counted_cents': c.counted_cents, 'difference_cents': c.difference_cents, 'expected_cents': c.expected_close_cents if c.closed_at else expected_cash(db, c), 'note': c.note} for c in rows(db, CashSession)]


@router.post('/cash-sessions', status_code=201)
def open_cash(data: OpenIn, db: DB):
    aware(data.opened_at); lock(db, 501); active_employee(db, data.employee_id)
    if db.scalar(select(CashSession.id).where(CashSession.closed_at.is_(None))):
        raise HTTPException(409, 'Já existe um caixa aberto.')
    latest = db.scalar(select(func.max(CashSession.closed_at)))
    if latest and data.opened_at < latest:
        raise HTTPException(409, 'A abertura deve ser posterior ao último fechamento.')
    assign(db, data.employee_id, data.opened_at, 'Abertura de caixa: ' + data.note[:250])
    row = CashSession(opened_by_id=data.employee_id, employee_id=data.employee_id, opened_at=data.opened_at, opening_cents=data.opening_cents, note=data.note)
    db.add(row); db.flush(); audit(db, 'cash_session', row.id, 'opened', data.model_dump()); db.commit()
    return row


@router.post('/cash-sessions/{key}/entries', status_code=201)
def manual_cash_entry(key: int, data: CashEntryIn, db: DB):
    amount = data.amount_cents if data.kind == 'reinforcement' else -data.amount_cents
    row = add_cash_entry(db, key, data.kind, amount, data.occurred_at, data.note, f'manual:{uuid4()}'); db.commit()
    return row


@router.post('/cash-sessions/{key}/handover', status_code=201)
def handover(key: int, data: HandoverIn, db: DB):
    session = cash_session(db, key); active_employee(db, data.employee_id); check_count_time(db, session, data.occurred_at)
    expected = expected_cash(db, session); difference = data.counted_cents - expected
    row = CashHandover(session_id=key, from_employee_id=session.employee_id, to_employee_id=data.employee_id, occurred_at=data.occurred_at, expected_cents=expected, counted_cents=data.counted_cents, difference_cents=difference, reason=data.reason)
    db.add(row); db.flush()
    if difference:
        add_cash_entry(db, key, 'count_difference', difference, data.occurred_at, data.reason, f'handover:{row.id}')
    assign(db, data.employee_id, data.occurred_at, 'Passagem conferida: ' + data.reason[:250])
    session.employee_id = data.employee_id
    audit(db, 'handover', row.id, 'counted', data.model_dump()); db.commit()
    return row


@router.post('/cash-sessions/{key}/close')
def close_cash(key: int, data: CloseIn, db: DB):
    session = cash_session(db, key); check_count_time(db, session, data.occurred_at)
    expected = expected_cash(db, session)
    session.closed_at = data.occurred_at; session.open_guard = None; session.counted_cents = data.counted_cents
    session.expected_close_cents = expected; session.difference_cents = data.counted_cents - expected
    assignment = db.scalar(select(Assignment).where(Assignment.ended_at.is_(None)).order_by(Assignment.started_at.desc()).limit(1))
    if assignment and assignment.started_at <= data.occurred_at:
        assignment.ended_at = data.occurred_at
    audit(db, 'cash_session', key, 'closed', {**data.model_dump(), 'expected_cents': expected, 'difference_cents': session.difference_cents}); db.commit()
    return session


@router.post('/cash-sessions/{key}/reopen')
def reopen_cash(key: int, data: CancelSaleIn, db: DB):
    lock(db, 501); session = get_or_404(db, CashSession, key)
    latest = db.scalar(select(CashSession).order_by(CashSession.opened_at.desc(), CashSession.id.desc()).limit(1))
    if latest.id != key or session.closed_at is None:
        raise HTTPException(409, 'Só é possível reabrir o último caixa encerrado, sem outro caixa posterior.')
    audit(db, 'cash_session', key, 'reopened', {'reason': data.reason, 'previous_close': session.closed_at, 'previous_count': session.counted_cents, 'previous_difference': session.difference_cents})
    session.closed_at = None; session.open_guard = 1; session.counted_cents = None; session.expected_close_cents = None; session.difference_cents = None
    db.commit(); return session


@router.get('/cash-entries')
def cash_entries(db: DB):
    return rows(db, CashEntry)


@router.get('/cash-handovers')
def cash_handovers(db: DB):
    return rows(db, CashHandover)


def create_sale_record(db, data):
    aware(data.occurred_at); lock(db, 502)
    if len({line.item_id for line in data.lines}) != len(data.lines):
        raise HTTPException(422, 'Item repetido na venda.')
    if data.external_id and db.scalar(select(Sale.id).where(Sale.external_id == data.external_id)):
        raise HTTPException(409, 'Essa referência de venda já existe.')
    subtotal = 0; discountable = 0
    for line in data.lines:
        item = get_or_404(db, StockItem, line.item_id)
        if item.kind != 'product' or not item.active:
            raise HTTPException(422, 'Selecione um produto ativo para venda.')
        valid_quantity(item, line.quantity)
        price = price_at(db, item, data.occurred_at)
        if price['price_locked'] and price['sale_price_cents'] != line.unit_price_cents:
            raise HTTPException(409, 'Preço diferente do valor fixado pela licitação.')
        value = int((line.quantity * line.unit_price_cents).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        subtotal += value
        if not price['price_locked']:
            discountable += value
    if data.discount_cents > discountable:
        raise HTTPException(422, 'Desconto excede o valor dos itens com preço livre.')
    total = subtotal - data.discount_cents
    if total <= 0 or total > 2_000_000_000 or sum(p.amount_cents for p in data.payments) != total:
        raise HTTPException(422, 'A soma dos pagamentos deve corresponder ao total da venda, após descontos.')
    session = None
    if data.cash_session_id is not None:
        session = cash_session(db, data.cash_session_id); check_cash_time(db, session, data.occurred_at)
    elif any(p.method == 'cash' for p in data.payments):
        raise HTTPException(422, 'Selecione o caixa aberto para vendas em dinheiro.')
    sale = Sale(occurred_at=data.occurred_at, total_cents=total, discount_cents=data.discount_cents, cost_cents=0, cashier_id=session.employee_id if session else None, note=data.note, external_id=data.external_id)
    db.add(sale); db.flush(); cost = Decimal(0); cost_known = True
    for line in sorted(data.lines, key=lambda value: value.item_id):
        moved = change_stock(db, line.item_id, -line.quantity, 'sale', f'Venda #{sale.id}', data.occurred_at, reference_type='sale', reference_id=sale.id)
        cost += sum(-m.quantity * m.unit_cost_cents for m in moved)
        cost_known = cost_known and all(m.cost_known for m in moved)
        db.add(SaleLine(sale_id=sale.id, **line.model_dump()))
    sale.cost_cents = int(cost.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    sale.cost_known = cost_known
    for payment in data.payments:
        row = SalePayment(sale_id=sale.id, **payment.model_dump()); db.add(row); db.flush()
        if payment.method == 'cash':
            add_cash_entry(db, session.id, 'sale', payment.amount_cents, data.occurred_at, f'Venda #{sale.id}', f'sale_payment:{row.id}')
    audit(db, 'sale', sale.id, 'created', {'total_cents': total, 'occurred_at': data.occurred_at})
    return sale


@router.post('/sales', status_code=201)
def sale(data: SaleIn, db: DB):
    sale = create_sale_record(db, data); db.commit(); return sale


@router.get('/sales')
def sales(db: DB):
    result = []
    for sale in rows(db, Sale):
        payments = db.scalars(select(SalePayment).where(SalePayment.sale_id == sale.id)).all()
        result.append({'id': sale.id, 'occurred_at': sale.occurred_at, 'total_cents': sale.total_cents, 'cost_cents': sale.cost_cents, 'voided': sale.voided, 'stock_returned': sale.stock_returned, 'stock_applied': sale.stock_applied, 'note': sale.note, 'external_id': sale.external_id, 'payments': payments})
    return result


@router.get('/sale-payments')
def sale_payments(db: DB):
    result = []
    for p in rows(db, SalePayment):
        settled = p.amount_cents if p.method == 'cash' else db.scalar(select(func.coalesce(func.sum(Settlement.gross_cents), 0)).where(Settlement.payment_id == p.id))
        refunded = db.scalar(select(func.coalesce(func.sum(SaleRefund.amount_cents), 0)).where(SaleRefund.payment_id == p.id))
        cancelled = get_or_404(db, Sale, p.sale_id).voided
        result.append({'id': p.id, 'sale_id': p.sale_id, 'method': p.method, 'amount_cents': p.amount_cents, 'due_date': p.due_date, 'received_gross_cents': settled, 'pending_cents': 0 if cancelled else p.amount_cents - settled, 'refunded_cents': refunded, 'refund_pending_cents': max(0, settled - refunded) if cancelled else 0, 'sale_voided': cancelled})
    return result


@router.post('/settlements', status_code=201)
def settle(data: SettlementIn, db: DB):
    row = record_settlement(db, data); db.commit(); return row


def record_settlement(db, data):
    aware(data.occurred_at); lock(db, 502)
    payment = get_or_404(db, SalePayment, data.payment_id); sale = get_or_404(db, Sale, payment.sale_id)
    if payment.method == 'cash' or data.fee_cents > data.gross_cents or data.occurred_at < sale.occurred_at:
        raise HTTPException(422, 'Confira forma de pagamento, taxa e data do recebimento.')
    received = db.scalar(select(func.coalesce(func.sum(Settlement.gross_cents), 0)).where(Settlement.payment_id == payment.id))
    if received + data.gross_cents > payment.amount_cents:
        raise HTTPException(409, 'Recebimento excede a venda.')
    if db.scalar(select(Settlement.id).where(Settlement.reference == data.reference)):
        raise HTTPException(409, 'Comprovante de recebimento já lançado.')
    row = Settlement(**data.model_dump()); db.add(row); db.flush(); audit(db, 'settlement', row.id, 'received', data.model_dump()); return row


@router.get('/settlements')
def settlements(db: DB):
    return rows(db, Settlement)


@router.post('/sales/{key}/cancel')
def cancel_sale(key: int, data: CancelSaleIn, db: DB):
    aware(data.occurred_at); lock(db, 502); sale = get_or_404(db, Sale, key)
    if sale.voided or data.occurred_at < sale.occurred_at:
        raise HTTPException(409, 'Venda já cancelada ou data de cancelamento anterior à venda.')
    if data.stock_returned and sale.stock_applied:
        for movement in db.scalars(select(StockMovement).where(StockMovement.reference_type == 'sale', StockMovement.reference_id == key).order_by(StockMovement.item_id)):
            change_stock(db, movement.item_id, -movement.quantity, 'sale_return', data.reason, data.occurred_at, specific_lot=movement.lot_id, reference_type='sale_return', reference_id=key)
    sale.voided = True; sale.cancelled_at = data.occurred_at; sale.stock_returned = data.stock_returned
    audit(db, 'sale', key, 'cancelled', data.model_dump()); db.commit(); return sale


@router.post('/sale-refunds', status_code=201)
def refund(data: RefundIn, db: DB):
    aware(data.occurred_at); lock(db, 502); payment = get_or_404(db, SalePayment, data.payment_id); sale = get_or_404(db, Sale, payment.sale_id)
    if not sale.voided or data.occurred_at < sale.occurred_at:
        raise HTTPException(409, 'Cancele a venda antes de registrar a devolução do dinheiro.')
    if db.scalar(select(SaleRefund.id).where(SaleRefund.reference == data.reference)):
        raise HTTPException(409, 'Devolução já registrada.')
    received = payment.amount_cents if payment.method == 'cash' else db.scalar(select(func.coalesce(func.sum(Settlement.gross_cents), 0)).where(Settlement.payment_id == payment.id))
    refunded = db.scalar(select(func.coalesce(func.sum(SaleRefund.amount_cents), 0)).where(SaleRefund.payment_id == payment.id))
    if refunded + data.amount_cents > received:
        raise HTTPException(409, 'Devolução excede o valor efetivamente recebido e ainda não devolvido.')
    row = SaleRefund(**data.model_dump()); db.add(row); db.flush()
    if payment.method == 'cash':
        if data.cash_session_id is None:
            raise HTTPException(422, 'Informe o caixa usado para devolver o dinheiro.')
        add_cash_entry(db, data.cash_session_id, 'refund', -data.amount_cents, data.occurred_at, f'Devolução da venda #{sale.id}', f'refund:{row.id}')
    audit(db, 'refund', row.id, 'refunded', data.model_dump()); db.commit(); return row
