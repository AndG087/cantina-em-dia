"""Caixa: abertura, fechamento com os totais do dia e conferência diária.

No fechamento, quem está na cantina informa as vendas em dinheiro, Pix e cartão, as
retiradas e o dinheiro contado. Esperado = troco + vendas em dinheiro − retiradas.
A conferência diária aponta o que precisa de explicação; se os dados do dia mudarem
depois de conferidos, a conferência fica desatualizada.
"""
import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, Input, Money, as_dict, aware, brl, day_start, get_or_404, today
from .models import CashReview, CashSession
from .school import CalendarBook

router = APIRouter(prefix='/api', tags=['Caixa'])
DB = Annotated[Session, Depends(get_session)]
STATES = {'not_applicable': 'Sem movimento previsto', 'in_progress': 'Em andamento', 'pending': 'Aguardando conferência',
          'reviewed': 'Conferido', 'outdated': 'Alterado após a conferência'}


class OpenIn(Input):
    opened_at: datetime
    opened_by: str = Field(min_length=2, max_length=100)
    opening_cents: Money
    note: str = Field(default='', max_length=500)


class CloseIn(Input):
    closed_at: datetime
    closed_by: str = Field(min_length=2, max_length=100)
    cash_sales_cents: Money
    pix_cents: Money = 0
    card_cents: Money = 0
    withdrawals_cents: Money = 0
    counted_cents: Money
    note: str = Field(default='', max_length=500)


class ReopenIn(Input):
    reason: str = Field(min_length=3, max_length=300)


class ReviewIn(Input):
    day: date
    status: Literal['ok', 'issues']
    note: str = Field(min_length=3, max_length=1000)


def hour(value):
    return value.astimezone(TZ).strftime('%d/%m %H:%M')


@router.get('/cash-sessions')
def sessions(db: DB):
    return db.scalars(select(CashSession).order_by(CashSession.opened_at.desc()).limit(60)).all()


@router.post('/cash-sessions', status_code=201)
def open_cash(data: OpenIn, db: DB):
    aware(data.opened_at)
    if db.scalar(select(CashSession.id).where(CashSession.closed_at.is_(None))):
        raise HTTPException(409, 'Já existe um caixa aberto. Feche-o antes de abrir outro.')
    last_close = db.scalar(select(func.max(CashSession.closed_at)))
    if last_close and data.opened_at < last_close:
        raise HTTPException(409, 'A abertura deve ser posterior ao último fechamento.')
    row = CashSession(**data.model_dump(), open_guard=1); db.add(row); db.commit(); db.refresh(row)
    return row


@router.post('/cash-sessions/{key}/close')
def close_cash(key: int, data: CloseIn, db: DB):
    aware(data.closed_at)
    row = get_or_404(db, CashSession, key)
    if row.closed_at:
        raise HTTPException(409, 'Esse caixa já foi fechado.')
    if data.closed_at < row.opened_at:
        raise HTTPException(422, 'O fechamento deve ser posterior à abertura.')
    expected = row.opening_cents + data.cash_sales_cents - data.withdrawals_cents
    if expected < 0:
        raise HTTPException(422, 'As retiradas superam o troco mais as vendas em dinheiro. Confira os valores.')
    note = f'{row.note} · {data.note}'.strip(' ·') if data.note else row.note
    for field, value in data.model_dump(exclude={'note'}).items():
        setattr(row, field, value)
    row.note, row.open_guard, row.expected_cents, row.difference_cents = note[:1000], None, expected, data.counted_cents - expected
    db.commit(); db.refresh(row)
    return row


@router.post('/cash-sessions/{key}/reopen')
def reopen_cash(key: int, data: ReopenIn, db: DB):
    """Reabre o último caixa para corrigir o fechamento."""
    row = get_or_404(db, CashSession, key)
    latest = db.scalar(select(CashSession).order_by(CashSession.opened_at.desc()).limit(1))
    if latest.id != key or row.closed_at is None:
        raise HTTPException(409, 'Só é possível reabrir o último caixa fechado.')
    for field in ['closed_at', 'cash_sales_cents', 'pix_cents', 'card_cents', 'withdrawals_cents', 'counted_cents', 'expected_cents', 'difference_cents']:
        setattr(row, field, None)
    row.closed_by, row.open_guard, row.note = '', 1, f'{row.note} · Reaberto: {data.reason}'.strip(' ·')[:1000]
    db.commit(); db.refresh(row)
    return row


def cash_day(db, day, calendar_day, current_day):
    start, end = day_start(day), day_start(day + timedelta(days=1))
    opened = db.scalars(select(CashSession).where(CashSession.opened_at >= start, CashSession.opened_at < end).order_by(CashSession.opened_at)).all()
    carried = db.scalars(select(CashSession).where(CashSession.opened_at < start, CashSession.closed_at.is_(None) | (CashSession.closed_at >= start))).all()
    issues = []
    for row in opened:
        previous = db.scalar(select(CashSession).where(CashSession.closed_at.is_not(None), CashSession.closed_at <= row.opened_at).order_by(CashSession.closed_at.desc()).limit(1))
        if previous and previous.counted_cents != row.opening_cents:
            issues.append(f'Troco de abertura {brl(row.opening_cents)} diferente do contado no fechamento anterior ({brl(previous.counted_cents)}). '
                          'Confirme se houve retirada ou depósito sem registro.')
        if row.difference_cents:
            issues.append(f'Diferença de {brl(row.difference_cents)} no fechamento (esperado {brl(row.expected_cents)}, contado {brl(row.counted_cents)}).')
        if day < current_day and (row.closed_at is None or row.closed_at >= end):
            issues.append(f'Caixa aberto às {hour(row.opened_at)} não foi fechado no mesmo dia.')
    for row in carried:
        issues.append(f'Caixa aberto em {hour(row.opened_at)} continuava sem fechamento.')
    worked = bool(opened or carried)
    if calendar_day['cantina_open'] and not worked and day < current_day:
        issues.append('Dia de funcionamento sem abertura de caixa. Registre a abertura ou marque o dia como fechado no calendário.')
    if not calendar_day['cantina_open'] and opened:
        issues.append(f'Caixa aberto em dia previsto como fechado ({"; ".join(calendar_day["reasons"])}).')
    closed = [row for row in opened if row.closed_at]
    summary = {'day': day, 'sessions': [as_dict(row) for row in opened], 'carried': [row.id for row in carried],
               'cash_sales_cents': sum(r.cash_sales_cents for r in closed), 'pix_cents': sum(r.pix_cents for r in closed), 'card_cents': sum(r.card_cents for r in closed),
               'withdrawals_cents': sum(r.withdrawals_cents for r in closed), 'difference_cents': sum(r.difference_cents for r in closed), 'issues': issues}
    fingerprint = hashlib.sha256(json.dumps(jsonable_encoder(summary), sort_keys=True).encode()).hexdigest()
    review = db.scalar(select(CashReview).where(CashReview.day == day).order_by(CashReview.reviewed_at.desc(), CashReview.id.desc()).limit(1))
    unfinished = any(row.closed_at is None for row in opened)
    if day > current_day or (day == current_day and (unfinished or (calendar_day['cantina_open'] and not worked))):
        state = 'in_progress'
    elif review:
        state = 'reviewed' if review.fingerprint == fingerprint else 'outdated'
    elif not worked and not issues:
        state = 'not_applicable'
    else:
        state = 'pending'
    return {**summary, 'calendar_status': calendar_day['status'], 'fingerprint': fingerprint, 'state': state, 'state_label': STATES[state],
            'review': {'status': review.status, 'note': review.note, 'reviewed_at': review.reviewed_at} if review else None}


def cash_days(db, first, last):
    book, current = CalendarBook(db, first, last), today()
    return [cash_day(db, first + timedelta(days=n), book.day(first + timedelta(days=n)), current) for n in range((last - first).days + 1)]


@router.get('/cash-reviews/days')
def review_days(db: DB, end: date | None = None, days: int = 14):
    if not 1 <= days <= 62:
        raise HTTPException(422, 'Consulte de 1 a 62 dias por vez.')
    last = end or today()
    return list(reversed(cash_days(db, last - timedelta(days=days - 1), last)))


@router.post('/cash-reviews', status_code=201)
def create_review(data: ReviewIn, db: DB):
    if data.day > today():
        raise HTTPException(422, 'Não é possível conferir um dia futuro.')
    current = cash_days(db, data.day, data.day)[0]
    if current['state'] == 'in_progress':
        raise HTTPException(409, 'O caixa do dia ainda está em andamento. Registre o fechamento antes de conferir.')
    if current['issues'] and data.status == 'ok':
        raise HTTPException(409, 'Há pontos de atenção neste dia. Registre como "conferido com ressalvas" e descreva o encaminhamento.')
    row = CashReview(day=data.day, status=data.status, note=data.note, fingerprint=current['fingerprint'])
    db.add(row); db.commit(); db.refresh(row)
    return row
