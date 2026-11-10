"""Despesas e identificação de gastos fora do padrão.

Regras simples, comparando cada gasto com o histórico registrado. Um alerta é um
convite à conferência, não prova de erro. O gerente registra a explicação.
"""
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import Input, Money, aware, brl, day_start, get_or_404, today
from .models import Expense, ExpenseAlertNote, PurchaseReceipt, PurchaseReceiptLine, StockItem

router = APIRouter(prefix='/api', tags=['Despesas'])
DB = Annotated[Session, Depends(get_session)]

LOOKBACK = timedelta(days=180)
MIN_SAMPLES = 3
ABOVE_USUAL = Decimal('1.5')
CATEGORY_INCREASE = Decimal('1.3')
CATEGORY_MIN_DIFF_CENTS = 5000
UNIT_COST_INCREASE = Decimal('1.15')
DUPLICATE_WINDOW = timedelta(days=7)
KINDS = {'above_usual': 'Valor acima do usual', 'duplicate': 'Possível duplicidade', 'category_increase': 'Categoria acima da média', 'unit_cost': 'Compra mais cara'}
CRITERIA = (f'Despesa 50% acima da mediana da categoria (mínimo de {MIN_SAMPLES} lançamentos em 180 dias); mesmo favorecido e valor em até 7 dias; '
            f'categoria 30% acima da média dos períodos anteriores (e ao menos {brl(CATEGORY_MIN_DIFF_CENTS)} a mais); custo de compra 15% acima das últimas compras do item.')


class ExpenseIn(Input):
    description: str = Field(min_length=3, max_length=300)
    category: str = Field(min_length=2, max_length=80)
    amount_cents: Money = Field(gt=0)
    occurred_at: datetime
    payee: str = Field(min_length=2, max_length=120)
    document: str = Field(min_length=1, max_length=150)


class NoteIn(Input):
    alert_key: str = Field(min_length=5, max_length=120, pattern=r'^[a-z_]+:[A-Za-z0-9:_-]+$')
    note: str = Field(min_length=5, max_length=1000)


@router.get('/expenses')
def expenses(db: DB):
    return db.scalars(select(Expense).order_by(Expense.occurred_at.desc(), Expense.id.desc()).limit(300)).all()


@router.post('/expenses', status_code=201)
def create_expense(data: ExpenseIn, db: DB):
    aware(data.occurred_at)
    if db.scalar(select(Expense.id).where(Expense.document == data.document, Expense.payee == data.payee)):
        raise HTTPException(409, 'Documento já lançado para esse favorecido.')
    row = Expense(**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return row


@router.delete('/expenses/{key}', status_code=204)
def delete_expense(key: int, db: DB):
    row = get_or_404(db, Expense, key)
    if row.receipt_id:
        raise HTTPException(409, 'Despesa de compra vem do recebimento da nota e não pode ser apagada aqui.')
    db.delete(row); db.commit()
    return Response(status_code=204)


def alert(key, kind, severity, title, detail, when, amount, reference):
    return {'key': key, 'kind': kind, 'kind_label': KINDS[kind], 'severity': severity, 'title': title, 'detail': detail,
            'occurred_at': when, 'amount_cents': amount, 'reference_cents': reference}


def expense_alerts(db, first: date, last: date):
    start, end = day_start(first), day_start(last + timedelta(days=1))
    history = db.scalars(select(Expense).where(Expense.occurred_at >= start - LOOKBACK, Expense.occurred_at < end).order_by(Expense.occurred_at, Expense.id)).all()
    window = [e for e in history if e.occurred_at >= start]
    manual = [e for e in history if e.receipt_id is None]
    same = lambda a, b: a.strip().lower() == b.strip().lower()
    alerts = []
    for expense in window:
        if expense.receipt_id is None:
            prior = [e.amount_cents for e in manual if e.id != expense.id and same(e.category, expense.category) and expense.occurred_at - LOOKBACK <= e.occurred_at <= expense.occurred_at]
            usual = int(median(prior)) if len(prior) >= MIN_SAMPLES else 0
            if usual and expense.amount_cents >= usual * ABOVE_USUAL:
                times = f'{Decimal(expense.amount_cents) / usual:.1f}'.replace('.', ',')
                alerts.append(alert(f'above_usual:{expense.id}', 'above_usual', 'high' if expense.amount_cents >= usual * 2 else 'medium', f'{expense.description}: {brl(expense.amount_cents)}',
                                    f'{times}x o valor usual de {expense.category} (mediana de {brl(usual)} em {len(prior)} lançamentos).', expense.occurred_at, expense.amount_cents, usual))
        for twin in [e for e in history if e.id < expense.id and e.amount_cents == expense.amount_cents and same(e.payee, expense.payee) and abs(e.occurred_at - expense.occurred_at) <= DUPLICATE_WINDOW]:
            alerts.append(alert(f'duplicate:{twin.id}:{expense.id}', 'duplicate', 'high', f'{expense.payee}: {brl(expense.amount_cents)} lançado duas vezes?',
                                f'Despesas com documentos {twin.document} e {expense.document}, mesmo favorecido e valor em até 7 dias.', expense.occurred_at, expense.amount_cents, twin.amount_cents))
    # Categorias: compara o período com os anteriores de mesma duração (só despesas manuais; mercadorias variam com a reposição).
    length = end - start
    first_record = db.scalar(select(func.min(Expense.occurred_at)))
    previous = [(start - length * k, start - length * (k - 1)) for k in (1, 2, 3)] if length <= timedelta(days=62) and first_record else []
    previous = [w for w in previous if w[0] >= first_record - timedelta(days=1)]
    totals = {}
    for expense in window:
        if expense.receipt_id is None:
            totals[expense.category.strip()] = totals.get(expense.category.strip(), 0) + expense.amount_cents
    for category, current in totals.items():
        if not previous:
            break
        average = Decimal(sum(e.amount_cents for e in manual for w in previous if same(e.category, category) and w[0] <= e.occurred_at < w[1])) / len(previous)
        if average and current >= average * CATEGORY_INCREASE and current - average >= CATEGORY_MIN_DIFF_CENTS:
            key = hashlib.sha1(category.lower().encode()).hexdigest()[:10]
            alerts.append(alert(f'category_increase:{key}:{first.isoformat()}:{last.isoformat()}', 'category_increase', 'medium', f'{category}: {brl(current)} no período',
                                f'{(current / average - 1) * 100:.0f}% acima da média de {brl(int(average))} em {len(previous)} período(s) anterior(es).', end - timedelta(seconds=1), current, int(average)))
    # Compras: custo por unidade comparado às três compras anteriores do mesmo item.
    bought = db.execute(select(PurchaseReceiptLine, PurchaseReceipt.occurred_at, StockItem).join(PurchaseReceipt, PurchaseReceiptLine.receipt_id == PurchaseReceipt.id)
                        .join(StockItem, PurchaseReceiptLine.item_id == StockItem.id).where(PurchaseReceipt.occurred_at >= start, PurchaseReceipt.occurred_at < end)).all()
    for line, when, item in bought:
        earlier = db.scalars(select(PurchaseReceiptLine.unit_cost_cents).join(PurchaseReceipt, PurchaseReceiptLine.receipt_id == PurchaseReceipt.id)
                             .where(PurchaseReceiptLine.item_id == item.id, PurchaseReceiptLine.id != line.id, PurchaseReceipt.occurred_at <= when, PurchaseReceipt.occurred_at >= when - LOOKBACK)
                             .order_by(PurchaseReceipt.occurred_at.desc()).limit(3)).all()
        average = Decimal(sum(earlier)) / len(earlier) if earlier else 0
        if average and line.unit_cost_cents >= average * UNIT_COST_INCREASE:
            alerts.append(alert(f'unit_cost:{line.id}', 'unit_cost', 'high' if line.unit_cost_cents >= average * Decimal('1.3') else 'medium', f'{item.name}: {brl(line.unit_cost_cents)} por {item.unit}',
                                f'{(line.unit_cost_cents / average - 1) * 100:.0f}% acima da média das últimas {len(earlier)} compra(s) ({brl(int(average))}).', when, line.unit_cost_cents, int(average)))
    notes = {n.alert_key: n for n in db.scalars(select(ExpenseAlertNote).where(ExpenseAlertNote.alert_key.in_([a['key'] for a in alerts])))} if alerts else {}
    for item in alerts:
        note = notes.get(item['key'])
        item['explanation'] = {'note': note.note, 'created_at': note.created_at} if note else None
    alerts.sort(key=lambda a: (a['explanation'] is not None, a['severity'] != 'high', -a['occurred_at'].timestamp()))
    return {'start': first, 'end': last, 'alerts': alerts, 'open_count': sum(1 for a in alerts if a['explanation'] is None), 'criteria': CRITERIA}


@router.get('/expense-alerts')
def alerts(db: DB, start: date | None = None, end: date | None = None):
    last = end or today()
    first = start or last - timedelta(days=29)
    if first > last or (last - first).days > 366:
        raise HTTPException(422, 'Informe um período válido de até um ano.')
    return expense_alerts(db, first, last)


@router.post('/expense-alerts/notes', status_code=201)
def explain(data: NoteIn, db: DB):
    if data.alert_key.split(':', 1)[0] not in KINDS:
        raise HTTPException(422, 'Alerta desconhecido.')
    if db.scalar(select(ExpenseAlertNote.id).where(ExpenseAlertNote.alert_key == data.alert_key)):
        raise HTTPException(409, 'Esse alerta já tem explicação.')
    row = ExpenseAlertNote(**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return row
