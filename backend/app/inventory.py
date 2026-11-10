from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import get_session
from .domain import audit, aware, get_or_404, quantity, rows, TZ, lock
from .models import StockItem, StockLot, StockMovement, InventoryCount
from .team import Input
from .pricing import price_at, seed_price

router = APIRouter(prefix="/api", tags=["Estoque"])
DB = Annotated[Session, Depends(get_session)]
Qty = Annotated[Decimal, Field(max_digits=14, decimal_places=3)]


class ItemIn(Input):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    kind: Literal["product", "ingredient", "packaging"]
    unit: Literal["un", "kg", "L"]
    minimum: Qty = Field(default=Decimal(0), ge=0)
    unit_cost_cents: int = Field(default=0, ge=0)
    sale_price_cents: int | None = Field(default=None, ge=0)
    price_locked: bool = False
    price_source: str = Field(default="", max_length=300)
    active: bool = True
    cost_known: bool = False


class MovementIn(Input):
    item_id: int
    kind: Literal["opening", "incoming", "consumption", "loss", "staff", "complimentary", "supplier_return"]
    quantity: Qty = Field(gt=0)
    occurred_at: datetime
    reason: str = Field(min_length=3, max_length=500)
    lot_code: str = Field(default="", max_length=100)
    expiry: date | None = None
    unit_cost_cents: int | None = Field(default=None, ge=0)


class CountIn(Input):
    item_id: int
    counted_at: datetime
    counted: Qty = Field(ge=0)
    expected: Qty
    reason: str = Field(min_length=3, max_length=500)


class ReasonIn(Input):
    reason: str = Field(min_length=3, max_length=500)


def item_locked(db, key):
    item = db.scalar(select(StockItem).where(StockItem.id == key).with_for_update())
    if not item:
        raise HTTPException(404, "Produto não encontrado.")
    return item


def valid_quantity(item, amount):
    if item.unit == 'un' and amount != amount.to_integral_value():
        raise HTTPException(422, "Itens em unidade exigem quantidades inteiras.")


def change_stock(db, item_id, amount, kind, reason, occurred_at, *, lot_code="", expiry=None, unit_cost_cents=None, reference_type=None, reference_id=None, specific_lot=None, reversal_of=None, cost_known_override=None):
    aware(occurred_at); lock(db, 904)
    item = item_locked(db, item_id)
    if not item.active and kind not in {'reversal', 'sale_return'}:
        raise HTTPException(409, "O item está inativo.")
    amount = quantity(amount); valid_quantity(item, amount)
    if not amount:
        return []
    if item.balance + amount < 0:
        raise HTTPException(409, f"Estoque insuficiente: {item.name}.")
    results = []
    if amount > 0:
        if specific_lot:
            lot = db.get(StockLot, specific_lot); lot.balance += amount
        else:
            lot = StockLot(item_id=item.id, code=lot_code or 'Sem identificação', expiry=expiry, balance=amount,
                           unit_cost_cents=item.unit_cost_cents if unit_cost_cents is None else unit_cost_cents, received_at=occurred_at,
                           cost_known=cost_known_override if cost_known_override is not None else (unit_cost_cents is not None or item.cost_known))
            db.add(lot); db.flush()
        pieces = [(lot, amount)]
    else:
        query = select(StockLot).where(StockLot.item_id == item_id, StockLot.balance > 0, StockLot.received_at <= occurred_at)
        if specific_lot:
            query = query.where(StockLot.id == specific_lot)
        if kind not in {'loss', 'supplier_return', 'adjustment', 'reversal'}:
            query = query.where((StockLot.expiry.is_(None)) | (StockLot.expiry >= occurred_at.astimezone(TZ).date()))
        lots = db.scalars(query.order_by(StockLot.expiry.asc().nulls_last(), StockLot.received_at, StockLot.id).with_for_update()).all()
        remaining = -amount; pieces = []
        for lot in lots:
            used = min(lot.balance, remaining)
            if used:
                lot.balance -= used; remaining -= used; pieces.append((lot, -used))
            if not remaining:
                break
        if remaining:
            raise HTTPException(409, f"Não há lote disponível nessa data para {item.name}. Confira validade, recebimento e quantidades.")
    item.balance += amount
    from .valuation import lot_cost
    costs = {}
    for lot, part in pieces:
        effective_cost, effective_known = lot_cost(db, lot, costs)
        movement = StockMovement(item_id=item_id, lot_id=lot.id, quantity=part, kind=kind, reason=reason, unit_cost_cents=effective_cost, occurred_at=occurred_at,
                                 reference_type=reference_type, reference_id=reference_id, reversal_of=reversal_of, cost_known=effective_known)
        db.add(movement); db.flush(); results.append(movement)
        audit(db, 'stock', movement.id, kind, {'item_id': item_id, 'quantity': part, 'reason': reason, 'reference': reference_type})
    # Lançamentos tardios não podem criar estoque negativo em um instante anterior.
    db.flush(); running = Decimal(0)
    for movement in db.scalars(select(StockMovement).where(StockMovement.item_id == item_id).order_by(StockMovement.occurred_at, StockMovement.id)):
        running += movement.quantity
        if running < 0:
            raise HTTPException(409, "O lançamento deixaria um saldo histórico negativo. Confira a data da ocorrência.")
    return results


@router.get('/items')
def items(db: DB):
    from .domain import now
    return [{**{c.name: getattr(item, c.name) for c in StockItem.__table__.columns}, **price_at(db, item, now())} for item in rows(db, StockItem, 2000)]


@router.post('/items', status_code=201)
def create_item(data: ItemIn, db: DB):
    lock(db, 201)
    if db.scalar(select(StockItem.id).where(StockItem.sku == data.sku)):
        raise HTTPException(409, 'Já existe um item com esse código.')
    values = data.model_dump(); values['cost_known'] = data.cost_known or data.unit_cost_cents > 0
    item = StockItem(**values); db.add(item); db.flush()
    seed_price(db, item)
    audit(db, 'item', item.id, 'created', data.model_dump()); db.commit(); db.refresh(item)
    return item


@router.put('/items/{key}')
def update_item(key: int, data: ItemIn, db: DB):
    item = item_locked(db, key)
    duplicate = db.scalar(select(StockItem.id).where(StockItem.sku == data.sku, StockItem.id != key))
    if duplicate:
        raise HTTPException(409, 'Código já utilizado.')
    has_movements = db.scalar(select(StockMovement.id).where(StockMovement.item_id == key).limit(1))
    if has_movements and (data.unit != item.unit or data.kind != item.kind):
        raise HTTPException(409, 'Unidade e tipo não podem mudar depois de movimentar o estoque.')
    from .domain import now
    current_price = price_at(db, item, now())
    if any(getattr(data, field) != value for field, value in current_price.items()):
        raise HTTPException(409, 'Para alterar preço, origem ou regra de licitação, use Preços e custos e registre uma nova vigência.')
    before = {key: getattr(item, key) for key in data.model_fields}
    for field, value in data.model_dump().items():
        if field not in current_price: setattr(item, field, value)
    item.cost_known = data.cost_known or data.unit_cost_cents > 0
    audit(db, 'item', key, 'updated', {'before': before, 'after': data.model_dump()}); db.commit(); db.refresh(item)
    return item


@router.get('/stock-movements')
def movements(db: DB):
    return db.scalars(select(StockMovement).order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc()).limit(500)).all()


@router.post('/stock-movements', status_code=201)
def create_movement(data: MovementIn, db: DB):
    amount = data.quantity if data.kind in {'opening', 'incoming'} else -data.quantity
    result = change_stock(db, data.item_id, amount, data.kind, data.reason, data.occurred_at, lot_code=data.lot_code, expiry=data.expiry, unit_cost_cents=data.unit_cost_cents)
    db.commit()
    return result


@router.post('/stock-movements/{key}/reverse', status_code=201)
def reverse_movement(key: int, data: ReasonIn, db: DB):
    original = get_or_404(db, StockMovement, key); item_locked(db, original.item_id)
    if original.reversal_of or db.scalar(select(StockMovement.id).where(StockMovement.reversal_of == key)):
        raise HTTPException(409, 'Este movimento já foi estornado ou é um estorno.')
    if original.reference_type:
        raise HTTPException(409, 'Corrija pela operação de origem para manter os registros vinculados.')
    from .domain import now
    result = change_stock(db, original.item_id, -original.quantity, 'reversal', data.reason, now(), specific_lot=original.lot_id, reversal_of=key)
    db.commit()
    return result


@router.get('/stock-lots')
def lots(db: DB, include_empty: bool = False):
    from .valuation import CostBook
    costs = CostBook(db)
    query = select(StockLot)
    if not include_empty: query = query.where(StockLot.balance > 0)
    return [{**{c.name: getattr(lot, c.name) for c in StockLot.__table__.columns},
             'original_unit_cost_cents': lot.unit_cost_cents, 'unit_cost_cents': costs.lot(lot.id)[0], 'cost_known': costs.lot(lot.id)[1],
             'produced': lot.id in costs.outputs} for lot in db.scalars(query.order_by(StockLot.id.desc()).limit(2000))]


@router.get('/inventory-counts')
def counts(db: DB):
    return rows(db, InventoryCount)


def record_count(db, data: CountIn):
    aware(data.counted_at); item = item_locked(db, data.item_id); valid_quantity(item, data.counted)
    expected = db.scalar(select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(StockMovement.item_id == item.id, StockMovement.occurred_at <= data.counted_at))
    if expected != data.expected:
        raise HTTPException(409, f'O saldo de {item.name} nessa data mudou. Saldo esperado atual: {expected} {item.unit}. Confira novamente.')
    difference = data.counted - expected
    result = change_stock(db, item.id, difference, 'adjustment', data.reason, data.counted_at, reference_type='inventory')
    row = InventoryCount(item_id=item.id, counted_at=data.counted_at, expected=expected, counted=data.counted, difference=difference, reason=data.reason, movements=[m.id for m in result])
    db.add(row); db.flush()
    for movement in result:
        movement.reference_id = row.id
    audit(db, 'inventory', row.id, 'counted', data.model_dump())
    return row


@router.post('/inventory-counts', status_code=201)
def create_count(data: CountIn, db: DB):
    row = record_count(db, data); db.commit(); db.refresh(row)
    return row


class SheetLineIn(Input):
    item_id: int
    expected: Qty
    counted: Qty = Field(ge=0)


class SheetIn(Input):
    counted_at: datetime
    reason: str = Field(min_length=3, max_length=500)
    lines: list[SheetLineIn] = Field(min_length=1, max_length=500)


@router.get('/inventory-sheet')
def inventory_sheet(db: DB, at: datetime | None = None, kind: Literal['product', 'ingredient', 'packaging'] | None = None):
    """Folha de contagem: itens ativos com o saldo esperado no horário de corte."""
    from .domain import now
    instant = at or now()
    if instant.tzinfo is None:
        raise HTTPException(422, 'Informe o fuso horário.')
    query = select(StockItem).where(StockItem.active.is_(True))
    if kind:
        query = query.where(StockItem.kind == kind)
    items = db.scalars(query.order_by(StockItem.category, StockItem.name)).all()
    balances = dict(db.execute(select(StockMovement.item_id, func.sum(StockMovement.quantity)).where(StockMovement.occurred_at <= instant).group_by(StockMovement.item_id)).all())
    return {'at': instant, 'items': [{'id': i.id, 'sku': i.sku, 'name': i.name, 'category': i.category, 'kind': i.kind, 'unit': i.unit,
                                      'expected': quantity(balances.get(i.id, 0)), 'minimum': i.minimum} for i in items]}


@router.post('/inventory-counts/batch', status_code=201)
def batch_count(data: SheetIn, db: DB):
    """Inventário completo em uma única transação: se um item falhar, nada é gravado."""
    if len({line.item_id for line in data.lines}) != len(data.lines):
        raise HTTPException(422, 'Cada item deve aparecer uma única vez na folha de contagem.')
    results = [record_count(db, CountIn(item_id=line.item_id, counted_at=data.counted_at, counted=line.counted, expected=line.expected, reason=data.reason))
               for line in sorted(data.lines, key=lambda value: value.item_id)]
    db.commit()
    return {'counted': len(results), 'with_difference': sum(1 for r in results if r.difference), 'ids': [r.id for r in results]}
