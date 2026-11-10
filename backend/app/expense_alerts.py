"""Identificação de gastos fora do padrão.

Regras simples e explicáveis, comparando cada gasto com o histórico registrado:
valor acima do usual na categoria, possível duplicidade, categoria com total acima dos
períodos anteriores e custo unitário de compra acima das compras recentes do mesmo item.
Um alerta é um convite à conferência, não prova de erro ou desvio. O gerente pode
registrar a explicação de cada alerta.
"""
import hashlib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from statistics import median
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, audit, brl, lock
from .models import Expense, ExpenseAlertNote, StockItem, StockLot, StockMovement
from .school import today
from .team import Input

router = APIRouter(prefix='/api', tags=['Gastos fora do padrão'])
DB = Annotated[Session, Depends(get_session)]

LOOKBACK_DAYS = 180
MIN_SAMPLES = 3
ABOVE_USUAL_FACTOR = Decimal('1.5')
HIGH_FACTOR = Decimal('2')
CATEGORY_FACTOR = Decimal('1.3')
CATEGORY_MIN_DIFF_CENTS = 5000
UNIT_COST_PCT = 15
DUPLICATE_DAYS = 7
KINDS = {'above_usual': 'Valor acima do usual', 'duplicate': 'Possível duplicidade', 'category_increase': 'Categoria acima da média',
         'unit_cost': 'Custo de compra mais alto', 'new_category': 'Categoria sem histórico'}
SEVERITY_ORDER = {'high': 0, 'medium': 1, 'info': 2}


class NoteIn(Input):
    alert_key: str = Field(min_length=5, max_length=120, pattern=r'^[a-z_]+:[A-Za-z0-9:_-]+$')
    note: str = Field(min_length=5, max_length=1000)


def bounds(first, last):
    start = datetime.combine(first, time(0), TZ)
    return start, datetime.combine(last + timedelta(days=1), time(0), TZ)


def category_key(category):
    return hashlib.sha1(category.strip().lower().encode()).hexdigest()[:10]


def alert(key, kind, severity, title, detail, occurred_at, amount, reference=None, **links):
    return {'key': key, 'kind': kind, 'kind_label': KINDS[kind], 'severity': severity, 'title': title, 'detail': detail, 'occurred_at': occurred_at,
            'amount_cents': amount, 'reference_cents': reference, 'expense_id': links.get('expense_id'), 'item_id': links.get('item_id'), 'lot_id': links.get('lot_id')}


def expense_alerts(db, first, last):
    start, end = bounds(first, last)
    lookback = timedelta(days=LOOKBACK_DAYS)
    history = db.scalars(select(Expense).where(Expense.voided.is_(False), Expense.occurred_at >= start - lookback, Expense.occurred_at < end).order_by(Expense.occurred_at, Expense.id)).all()
    window = [e for e in history if e.occurred_at >= start]
    manual = [e for e in history if e.receipt_id is None]
    alerts = []; thin = set()
    for expense in window:
        if expense.receipt_id is not None:
            continue
        category = expense.category.strip().lower()
        earlier = [e for e in manual if e.id != expense.id and e.occurred_at <= expense.occurred_at and e.occurred_at >= expense.occurred_at - lookback]
        prior = [e.amount_cents for e in earlier if e.category.strip().lower() == category]
        if len(prior) >= MIN_SAMPLES:
            usual = int(median(prior))
            if usual and expense.amount_cents >= usual * ABOVE_USUAL_FACTOR:
                times = Decimal(expense.amount_cents) / usual
                alerts.append(alert(f'above_usual:{expense.id}', 'above_usual', 'high' if times >= HIGH_FACTOR else 'medium',
                                    f'{expense.description}: {brl(expense.amount_cents)}',
                                    f'{times:.1f}'.replace('.', ',') + f'x o valor usual de {expense.category} (mediana de {brl(usual)} em {len(prior)} lançamentos dos últimos {LOOKBACK_DAYS} dias).',
                                    expense.occurred_at, expense.amount_cents, usual, expense_id=expense.id))
        else:
            thin.add(expense.category.strip())
            if not prior and len(earlier) >= MIN_SAMPLES:
                alerts.append(alert(f'new_category:{expense.id}', 'new_category', 'info', f'{expense.description}: {brl(expense.amount_cents)}',
                                    f'Primeira despesa em "{expense.category}" nos últimos {LOOKBACK_DAYS} dias. Confirme se a categoria está correta.',
                                    expense.occurred_at, expense.amount_cents, expense_id=expense.id))
    for expense in window:
        payee = expense.payee.strip().lower()
        twins = [e for e in history if e.id < expense.id and e.amount_cents == expense.amount_cents and e.payee.strip().lower() == payee
                 and abs(e.occurred_at - expense.occurred_at) <= timedelta(days=DUPLICATE_DAYS)]
        for twin in twins:
            alerts.append(alert(f'duplicate:{twin.id}:{expense.id}', 'duplicate', 'high', f'{expense.payee}: {brl(expense.amount_cents)} lançado duas vezes?',
                                f'Despesas #{twin.id} ({twin.document}) e #{expense.id} ({expense.document}) têm mesmo favorecido e valor em até {DUPLICATE_DAYS} dias.',
                                expense.occurred_at, expense.amount_cents, twin.amount_cents, expense_id=expense.id))
    length = end - start
    if length <= timedelta(days=62):
        first_record = db.scalar(select(func.min(Expense.occurred_at)).where(Expense.voided.is_(False)))
        windows = [(start - length * k, start - length * (k - 1)) for k in (1, 2, 3)]
        windows = [w for w in windows if first_record is not None and w[0] >= first_record - timedelta(days=1) and w[0] >= start - lookback]
        totals = {}
        # Compras de mercadorias variam com a reposição; o custo delas é avaliado item a item.
        for expense in window:
            if expense.receipt_id is not None:
                continue
            totals.setdefault(expense.category.strip(), 0)
            totals[expense.category.strip()] += expense.amount_cents
        for category, current in totals.items():
            if not windows:
                break
            previous = [sum(e.amount_cents for e in history if e.receipt_id is None and e.category.strip().lower() == category.lower() and w[0] <= e.occurred_at < w[1]) for w in windows]
            average = Decimal(sum(previous)) / len(previous)
            if average and current >= average * CATEGORY_FACTOR and current - average >= CATEGORY_MIN_DIFF_CENTS:
                alerts.append(alert(f'category_increase:{category_key(category)}:{first.isoformat()}:{last.isoformat()}', 'category_increase', 'medium',
                                    f'{category}: {brl(current)} no período', f'{(current / average - 1) * 100:.0f}% acima da média de {brl(int(average))} em {len(previous)} período(s) anterior(es) de mesma duração.',
                                    end - timedelta(seconds=1), current, int(average)))
    received = db.execute(select(StockMovement, StockLot, StockItem).join(StockLot, StockMovement.lot_id == StockLot.id).join(StockItem, StockMovement.item_id == StockItem.id)
                          .where(StockMovement.reference_type == 'purchase_receipt', StockMovement.occurred_at >= start, StockMovement.occurred_at < end)).all()
    for movement, lot, item in received:
        earlier = db.scalars(select(StockLot.unit_cost_cents).join(StockMovement, StockMovement.lot_id == StockLot.id)
                             .where(StockMovement.reference_type == 'purchase_receipt', StockLot.item_id == item.id, StockLot.id != lot.id,
                                    StockLot.received_at <= lot.received_at, StockLot.received_at >= lot.received_at - lookback)
                             .order_by(StockLot.received_at.desc(), StockLot.id.desc()).limit(3)).all()
        if not earlier:
            continue
        average = sum(Decimal(v) for v in earlier) / len(earlier)
        cost = Decimal(lot.unit_cost_cents)
        if average and cost >= average * (1 + Decimal(UNIT_COST_PCT) / 100):
            alerts.append(alert(f'unit_cost:{lot.id}', 'unit_cost', 'high' if cost >= average * Decimal('1.3') else 'medium',
                                f'{item.name}: {brl(int(cost))} por {item.unit}', f'{(cost / average - 1) * 100:.0f}% acima da média das últimas {len(earlier)} compra(s) ({brl(int(average))}). Confira a nota e o fornecedor.',
                                movement.occurred_at, int(cost), int(average), item_id=item.id, lot_id=lot.id))
    notes = {n.alert_key: n for n in db.scalars(select(ExpenseAlertNote).where(ExpenseAlertNote.alert_key.in_([a['key'] for a in alerts])))} if alerts else {}
    for item in alerts:
        note = notes.get(item['key'])
        item['explanation'] = {'note': note.note, 'created_at': note.created_at} if note else None
    alerts.sort(key=lambda a: (a['explanation'] is not None, SEVERITY_ORDER[a['severity']], -a['occurred_at'].timestamp()))
    return {'start': first, 'end': last, 'alerts': alerts, 'open_count': sum(1 for a in alerts if a['explanation'] is None and a['severity'] != 'info'),
            'insufficient_history': sorted(thin),
            'thresholds': {'lookback_days': LOOKBACK_DAYS, 'min_samples': MIN_SAMPLES, 'above_usual_pct': int((ABOVE_USUAL_FACTOR - 1) * 100), 'category_pct': int((CATEGORY_FACTOR - 1) * 100),
                           'category_min_diff_cents': CATEGORY_MIN_DIFF_CENTS, 'unit_cost_pct': UNIT_COST_PCT, 'duplicate_days': DUPLICATE_DAYS}}


@router.get('/expense-alerts')
def alerts(db: DB, start: date | None = None, end: date | None = None):
    last = end or today(); first = start or last - timedelta(days=29)
    if first > last or (last - first).days > 366:
        raise HTTPException(422, 'Informe um período válido de até um ano.')
    return expense_alerts(db, first, last)


@router.post('/expense-alerts/notes', status_code=201)
def explain(data: NoteIn, db: DB):
    lock(db, 402)
    if data.alert_key.split(':', 1)[0] not in KINDS:
        raise HTTPException(422, 'Alerta desconhecido.')
    if db.scalar(select(ExpenseAlertNote.id).where(ExpenseAlertNote.alert_key == data.alert_key)):
        raise HTTPException(409, 'Esse alerta já tem uma explicação registrada.')
    row = ExpenseAlertNote(**data.model_dump()); db.add(row); db.flush()
    audit(db, 'expense_alert', row.id, 'explained', data.model_dump()); db.commit(); db.refresh(row)
    return row
