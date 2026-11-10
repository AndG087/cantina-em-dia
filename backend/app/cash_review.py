"""Conferência diária das aberturas e fechamentos de caixa.

Para cada dia, reúne aberturas, passagens e fechamentos e aponta o que precisa de
explicação: dia de funcionamento sem abertura, troco de abertura diferente do valor
contado no fechamento anterior, diferenças de contagem e caixa esquecido aberto.
O gerente registra a conferência; se os registros mudarem depois, ela fica desatualizada.
"""
import hashlib
import json
from datetime import date, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, audit, brl, lock, rows
from .models import CashEntry, CashHandover, CashReview, CashSession, Employee, Sale, SalePayment
from .school import CalendarBook, today
from .team import Input

router = APIRouter(prefix='/api', tags=['Conferência diária do caixa'])
DB = Annotated[Session, Depends(get_session)]
STATES = {'not_applicable': 'Sem movimento esperado', 'in_progress': 'Em andamento', 'pending': 'Aguardando conferência', 'reviewed': 'Conferido', 'outdated': 'Registros alterados após a conferência'}


class ReviewIn(Input):
    day: date
    status: Literal['ok', 'issues']
    note: str = Field(min_length=3, max_length=1000)


def bounds(day):
    start = datetime.combine(day, time(0), TZ)
    return start, start + timedelta(days=1)


def local(value):
    return value.astimezone(TZ).strftime('%d/%m %H:%M')


def session_row(db, s, names):
    from .finance import expected_cash
    return {'id': s.id, 'employee': names.get(s.employee_id), 'opened_by': names.get(s.opened_by_id), 'opened_at': s.opened_at, 'opening_cents': s.opening_cents,
            'closed_at': s.closed_at, 'counted_cents': s.counted_cents, 'expected_cents': s.expected_close_cents if s.closed_at else expected_cash(db, s), 'difference_cents': s.difference_cents}


def cash_day(db, day, calendar_day, names, current_day):
    start, end = bounds(day)
    opened = db.scalars(select(CashSession).where(CashSession.opened_at >= start, CashSession.opened_at < end).order_by(CashSession.opened_at, CashSession.id)).all()
    carried = db.scalars(select(CashSession).where(CashSession.opened_at < start, (CashSession.closed_at.is_(None)) | (CashSession.closed_at >= start)).order_by(CashSession.opened_at)).all()
    closed = db.scalars(select(CashSession).where(CashSession.closed_at >= start, CashSession.closed_at < end).order_by(CashSession.closed_at)).all()
    handovers = db.scalars(select(CashHandover).where(CashHandover.occurred_at >= start, CashHandover.occurred_at < end).order_by(CashHandover.occurred_at)).all()
    movements = dict(db.execute(select(CashEntry.kind, func.sum(CashEntry.amount_cents)).where(CashEntry.occurred_at >= start, CashEntry.occurred_at < end).group_by(CashEntry.kind)).all())
    methods = dict(db.execute(select(SalePayment.method, func.sum(SalePayment.amount_cents)).join(Sale, SalePayment.sale_id == Sale.id)
                              .where(Sale.occurred_at >= start, Sale.occurred_at < end, Sale.voided.is_(False)).group_by(SalePayment.method)).all())
    sales_count = db.scalar(select(func.count()).select_from(Sale).where(Sale.occurred_at >= start, Sale.occurred_at < end, Sale.voided.is_(False)))
    issues = []
    for session in opened:
        previous = db.scalar(select(CashSession).where(CashSession.closed_at.is_not(None), CashSession.closed_at <= session.opened_at, CashSession.id != session.id)
                             .order_by(CashSession.closed_at.desc(), CashSession.id.desc()).limit(1))
        if previous and previous.counted_cents != session.opening_cents:
            issues.append(f'Caixa #{session.id}: troco de abertura {brl(session.opening_cents)} diferente do contado no fechamento do caixa #{previous.id} '
                          f'({brl(previous.counted_cents)}). Confirme se houve retirada ou depósito sem registro.')
    for session in closed:
        if session.difference_cents:
            issues.append(f'Caixa #{session.id}: diferença de {brl(session.difference_cents)} no fechamento (esperado {brl(session.expected_close_cents)}, contado {brl(session.counted_cents)}).')
    for handover in handovers:
        if handover.difference_cents:
            issues.append(f'Passagem {names.get(handover.from_employee_id)} → {names.get(handover.to_employee_id)} às {local(handover.occurred_at)}: diferença de {brl(handover.difference_cents)}.')
    for session in carried:
        issues.append(f'Caixa #{session.id}, aberto em {local(session.opened_at)}, continuava sem fechamento neste dia.')
    unfinished = [s for s in opened if s.closed_at is None or s.closed_at >= end]
    if day < current_day:
        for session in unfinished:
            issues.append(f'Caixa #{session.id}, aberto às {local(session.opened_at)}, não foi fechado até o fim do dia.')
    worked = bool(opened or carried)
    if calendar_day['cantina_open'] and not worked and day < current_day:
        issues.append('Dia de funcionamento sem abertura de caixa registrada. Registre a abertura ou marque o dia como fechado no calendário.')
    if not calendar_day['cantina_open'] and opened:
        issues.append(f'Caixa aberto em dia previsto como fechado ({"; ".join(calendar_day["reasons"])}). Confira o calendário.')
    summary = {'day': day, 'calendar_status': calendar_day['status'], 'calendar_reasons': calendar_day['reasons'],
               'sessions_opened': [session_row(db, s, names) for s in opened], 'sessions_carried': [session_row(db, s, names) for s in carried],
               'sessions_closed': [s.id for s in closed], 'handovers': len(handovers),
               'cash_sales_cents': movements.get('sale', 0), 'withdrawals_cents': -movements.get('withdrawal', 0), 'reinforcements_cents': movements.get('reinforcement', 0),
               'cash_expenses_cents': -movements.get('expense', 0), 'cash_refunds_cents': -movements.get('refund', 0),
               'closing_difference_cents': sum(s.difference_cents or 0 for s in closed) + sum(h.difference_cents for h in handovers),
               'sales_count': sales_count, 'sales_by_method': {key: methods.get(key, 0) for key in ['cash', 'pix', 'debit', 'credit']}, 'issues': issues}
    # O calendário entra nos apontamentos, mas suas observações informativas não invalidam a conferência.
    tracked = {key: value for key, value in summary.items() if key not in {'calendar_status', 'calendar_reasons'}}
    fingerprint = hashlib.sha256(json.dumps(jsonable_encoder(tracked), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    review = db.scalar(select(CashReview).where(CashReview.day == day).order_by(CashReview.reviewed_at.desc(), CashReview.id.desc()).limit(1))
    if day > current_day or (day == current_day and (unfinished or (calendar_day['cantina_open'] and not worked))):
        state = 'in_progress'
    elif review:
        state = 'reviewed' if review.fingerprint == fingerprint else 'outdated'
    elif not worked and not issues and not sales_count:
        state = 'not_applicable'
    else:
        state = 'pending'
    return {**summary, 'fingerprint': fingerprint, 'state': state, 'state_label': STATES[state],
            'review': {'id': review.id, 'status': review.status, 'note': review.note, 'reviewed_at': review.reviewed_at} if review else None}


def cash_days(db, first, last):
    names = {e.id: e.name for e in db.scalars(select(Employee))}
    book = CalendarBook(db, first, last); current = today()
    result = []; day = first
    while day <= last:
        result.append(cash_day(db, day, book.day(day), names, current)); day += timedelta(days=1)
    return result


@router.get('/cash-reviews/days')
def review_days(db: DB, end: date | None = None, days: int = 14):
    if days < 1 or days > 62:
        raise HTTPException(422, 'Consulte de 1 a 62 dias por vez.')
    last = end or today()
    return list(reversed(cash_days(db, last - timedelta(days=days - 1), last)))


@router.get('/cash-reviews')
def reviews(db: DB):
    return [{'id': r.id, 'day': r.day, 'status': r.status, 'note': r.note, 'reviewed_at': r.reviewed_at} for r in rows(db, CashReview, 500)]


@router.post('/cash-reviews', status_code=201)
def create_review(data: ReviewIn, db: DB):
    lock(db, 501)
    if data.day > today():
        raise HTTPException(422, 'Não é possível conferir um dia futuro.')
    current = cash_days(db, data.day, data.day)[0]
    if current['state'] == 'in_progress':
        raise HTTPException(409, 'O caixa do dia ainda está em andamento. Registre o fechamento antes de conferir.')
    if current['issues'] and data.status == 'ok':
        raise HTTPException(409, 'Há pontos de atenção neste dia. Registre como "conferido com ressalvas" e descreva o encaminhamento.')
    snapshot = jsonable_encoder({key: value for key, value in current.items() if key not in {'review', 'state', 'state_label'}})
    row = CashReview(day=data.day, status=data.status, note=data.note, fingerprint=current['fingerprint'], snapshot=snapshot)
    db.add(row); db.flush(); audit(db, 'cash_review', row.id, 'reviewed', data.model_dump()); db.commit(); db.refresh(row)
    return {'id': row.id, 'day': row.day, 'status': row.status, 'note': row.note, 'reviewed_at': row.reviewed_at}
