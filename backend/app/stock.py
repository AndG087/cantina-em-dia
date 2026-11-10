"""Estoque: itens, entradas e saídas avulsas e inventário pela folha de contagem.

O saldo de cada item é sempre a soma dos seus movimentos, sem valor guardado à parte.
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import Input, Qty, as_dict, aware, get_or_404, now, qty
from .models import InventoryCount, StockItem, StockMovement

router = APIRouter(prefix='/api', tags=['Estoque'])
DB = Annotated[Session, Depends(get_session)]
KINDS = {'entry': 'Entrada avulsa', 'output': 'Saída / consumo', 'loss': 'Perda', 'purchase': 'Compra recebida', 'count': 'Ajuste de inventário'}


class ItemIn(Input):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    unit: Literal['un', 'kg', 'L']
    minimum: Qty = Field(default=Decimal(0), ge=0)
    active: bool = True


class MovementIn(Input):
    item_id: int
    kind: Literal['entry', 'output', 'loss']
    quantity: Qty = Field(gt=0)
    occurred_at: datetime
    reason: str = Field(min_length=3, max_length=500)


class CountLineIn(Input):
    item_id: int
    expected: Qty
    counted: Qty = Field(ge=0)


class CountIn(Input):
    counted_at: datetime
    note: str = Field(min_length=3, max_length=500)
    lines: list[CountLineIn] = Field(min_length=1, max_length=500)


def balances(db, until=None) -> dict[int, Decimal]:
    query = select(StockMovement.item_id, func.sum(StockMovement.quantity)).group_by(StockMovement.item_id)
    if until is not None:
        query = query.where(StockMovement.occurred_at <= until)
    return dict(db.execute(query).all())


def move(db, item, amount, kind, reason, occurred_at, receipt_id=None):
    """Registra um movimento, sem permitir saldo negativo nem fração de item em unidade."""
    aware(occurred_at)
    if not item.active:
        raise HTTPException(409, f'{item.name} está inativo.')
    if item.unit == 'un' and amount != amount.to_integral_value():
        raise HTTPException(422, f'{item.name} é contado em unidades inteiras.')
    if amount < 0 and balances(db).get(item.id, 0) + amount < 0:
        raise HTTPException(409, f'Estoque insuficiente de {item.name}.')
    db.add(StockMovement(item_id=item.id, quantity=amount, kind=kind, reason=reason, occurred_at=occurred_at, receipt_id=receipt_id))


@router.get('/items')
def items(db: DB):
    current = balances(db)
    return [as_dict(i, balance=current.get(i.id, Decimal(0))) for i in db.scalars(select(StockItem).order_by(StockItem.category, StockItem.name))]


@router.post('/items', status_code=201)
def create_item(data: ItemIn, db: DB):
    if db.scalar(select(StockItem.id).where(func.lower(StockItem.name) == data.name.lower())):
        raise HTTPException(409, 'Já existe um item com esse nome.')
    row = StockItem(**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return row


@router.put('/items/{key}')
def update_item(key: int, data: ItemIn, db: DB):
    row = get_or_404(db, StockItem, key)
    if db.scalar(select(StockItem.id).where(func.lower(StockItem.name) == data.name.lower(), StockItem.id != key)):
        raise HTTPException(409, 'Já existe um item com esse nome.')
    if data.unit != row.unit and db.scalar(select(StockMovement.id).where(StockMovement.item_id == key).limit(1)):
        raise HTTPException(409, 'A unidade não pode mudar depois de movimentar o item.')
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    db.commit(); db.refresh(row)
    return row


@router.get('/stock-movements')
def movements(db: DB):
    return db.scalars(select(StockMovement).order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc()).limit(300)).all()


@router.post('/stock-movements', status_code=201)
def create_movement(data: MovementIn, db: DB):
    amount = data.quantity if data.kind == 'entry' else -data.quantity
    move(db, get_or_404(db, StockItem, data.item_id), amount, data.kind, data.reason, data.occurred_at)
    db.commit()
    return {'ok': True}


@router.get('/inventory-sheet')
def inventory_sheet(db: DB, at: datetime | None = None):
    """Folha de contagem: itens ativos com o saldo esperado no horário de corte."""
    instant = at or now()
    if instant.tzinfo is None:
        raise HTTPException(422, 'Informe o fuso horário.')
    expected = balances(db, instant)
    rows = db.scalars(select(StockItem).where(StockItem.active.is_(True)).order_by(StockItem.category, StockItem.name))
    return {'at': instant, 'items': [as_dict(i, expected=expected.get(i.id, Decimal(0))) for i in rows]}


@router.post('/inventory-counts', status_code=201)
def count(data: CountIn, db: DB):
    """Grava a contagem de todos os itens preenchidos juntos: se um falhar, nada é gravado."""
    aware(data.counted_at)
    if len({line.item_id for line in data.lines}) != len(data.lines):
        raise HTTPException(422, 'Cada item deve aparecer uma única vez na contagem.')
    expected = balances(db, data.counted_at)
    differences = 0
    for line in sorted(data.lines, key=lambda value: value.item_id):
        item = get_or_404(db, StockItem, line.item_id)
        before = expected.get(item.id, Decimal(0))
        if before != line.expected:
            raise HTTPException(409, f'O saldo de {item.name} mudou para {qty(before)} {item.unit}. Recarregue a folha.')
        difference = line.counted - before
        if difference:
            differences += 1
            move(db, item, difference, 'count', data.note, data.counted_at)
        db.add(InventoryCount(item_id=item.id, counted_at=data.counted_at, expected=before, counted=line.counted, difference=difference, note=data.note))
    db.commit()
    return {'counted': len(data.lines), 'with_difference': differences}


@router.get('/inventory-counts')
def counts(db: DB):
    return db.scalars(select(InventoryCount).order_by(InventoryCount.counted_at.desc(), InventoryCount.id.desc()).limit(300)).all()
