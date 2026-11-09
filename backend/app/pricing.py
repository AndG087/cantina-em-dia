"""Regras de preço por vigência, preservando os preços das vendas antigas."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import audit, get_or_404, lock, now, rows
from .models import PriceRule, StockItem, Sale, SaleLine
from .team import Input

router = APIRouter(prefix='/api', tags=['Preços e vigências'])
DB = Annotated[Session, Depends(get_session)]
BASELINE = datetime(1900, 1, 1, tzinfo=timezone.utc)


class PriceIn(Input):
    item_id: int
    effective_from: datetime
    price_cents: int = Field(ge=0, le=2_000_000_000)
    locked: bool
    source: str = Field(min_length=3, max_length=300)
    reason: str = Field(min_length=5, max_length=500)


class ReasonIn(Input):
    reason: str = Field(min_length=5, max_length=500)


def seed_price(db, item):
    if item.kind == 'product':
        db.add(PriceRule(item_id=item.id, effective_from=BASELINE, price_cents=item.sale_price_cents,
                         locked=item.price_locked, source=item.price_source or 'Cadastro inicial sem documento informado', reason='Preço inicial do cadastro'))


def price_at(db, item, instant):
    rule = db.scalar(select(PriceRule).where(PriceRule.item_id == item.id, PriceRule.effective_from <= instant,
                     PriceRule.cancelled_at.is_(None)).order_by(PriceRule.effective_from.desc(), PriceRule.id.desc()).limit(1))
    return {'sale_price_cents': rule.price_cents if rule else item.sale_price_cents,
            'price_locked': rule.locked if rule else item.price_locked, 'price_source': rule.source if rule else item.price_source}


def ensure_no_sales(db, item_id, instant):
    if db.scalar(select(SaleLine.id).join(Sale, Sale.id == SaleLine.sale_id).where(SaleLine.item_id == item_id, Sale.occurred_at >= instant).limit(1)):
        raise HTTPException(409, 'Há vendas desse produto a partir dessa vigência. Escolha uma data posterior às vendas registradas; os preços antigos serão preservados.')


@router.get('/price-rules')
def list_rules(db: DB, item_id: int | None = None):
    query = select(PriceRule)
    if item_id is not None: query = query.where(PriceRule.item_id == item_id)
    return db.scalars(query.order_by(PriceRule.effective_from.desc(), PriceRule.id.desc()).limit(2000)).all()


@router.get('/items/{key}/price')
def quoted_price(key: int, at: datetime, db: DB):
    if at.tzinfo is None: raise HTTPException(422, 'Informe horário com fuso.')
    return price_at(db, get_or_404(db, StockItem, key), at)


@router.post('/price-rules', status_code=201)
def create_rule(data: PriceIn, db: DB):
    lock(db, 502)  # mesmo bloqueio das vendas e da importação de vendas por item
    item = get_or_404(db, StockItem, data.item_id)
    if item.kind != 'product' or not item.active: raise HTTPException(422, 'Selecione um produto ativo para venda.')
    if data.effective_from.tzinfo is None or data.effective_from <= BASELINE:
        raise HTTPException(422, 'Informe uma vigência válida com fuso horário.')
    ensure_no_sales(db, item.id, data.effective_from)
    row = PriceRule(**data.model_dump()); db.add(row); db.flush()
    audit(db, 'price_rule', row.id, 'created', data.model_dump()); db.commit(); return row


@router.post('/price-rules/{key}/cancel')
def cancel_rule(key: int, data: ReasonIn, db: DB):
    lock(db, 502); row = get_or_404(db, PriceRule, key)
    if row.cancelled_at or row.effective_from == BASELINE:
        raise HTTPException(409, 'Regra inicial ou já cancelada. Registre uma nova vigência.')
    ensure_no_sales(db, row.item_id, row.effective_from)
    row.cancelled_at = now(); audit(db, 'price_rule', key, 'cancelled', {'reason': data.reason}); db.commit(); return row
