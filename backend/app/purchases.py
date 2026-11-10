"""Compras: pedido ao fornecedor, recebimento com a nota e conferência.

No recebimento, o valor total da nota é obrigatório. Se for diferente da soma dos itens,
é preciso explicar. A mercadoria entra no estoque e vira uma despesa de "Mercadorias".
"""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import Input, Money, Qty, as_dict, aware, brl, get_or_404
from .models import Expense, Purchase, PurchaseLine, PurchaseReceipt, PurchaseReceiptLine, StockItem, Supplier
from .stock import move

router = APIRouter(prefix='/api', tags=['Compras'])
DB = Annotated[Session, Depends(get_session)]
COST_TOLERANCE_PCT = 10


class SupplierIn(Input):
    name: str = Field(min_length=2, max_length=120)


class LineIn(Input):
    item_id: int
    quantity: Qty = Field(gt=0)
    unit_cost_cents: Money


class Lines(Input):
    lines: list[LineIn] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_items(self):
        if len({line.item_id for line in self.lines}) != len(self.lines):
            raise ValueError('Cada item deve aparecer uma única vez.')
        return self


class PurchaseIn(Lines):
    supplier_id: int
    requested_by: str = Field(min_length=2, max_length=100)
    note: str = Field(default='', max_length=500)


class ReceiptIn(Lines):
    document: str = Field(min_length=1, max_length=120)
    occurred_at: datetime
    invoice_total_cents: Money
    invoice_note: str = Field(default='', max_length=500)


class CloseIn(Input):
    reason: str = Field(min_length=3, max_length=300)


def cents(value) -> int:
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@router.get('/suppliers')
def suppliers(db: DB):
    return db.scalars(select(Supplier).order_by(Supplier.name)).all()


@router.post('/suppliers', status_code=201)
def create_supplier(data: SupplierIn, db: DB):
    if db.scalar(select(Supplier.id).where(Supplier.name == data.name)):
        raise HTTPException(409, 'Fornecedor já cadastrado.')
    row = Supplier(name=data.name); db.add(row); db.commit(); db.refresh(row)
    return row


@router.get('/purchases')
def purchases(db: DB):
    lines = {}
    for line in db.scalars(select(PurchaseLine).order_by(PurchaseLine.id)):
        lines.setdefault(line.purchase_id, []).append(line)
    return [as_dict(p, lines=lines.get(p.id, [])) for p in db.scalars(select(Purchase).order_by(Purchase.id.desc()).limit(300))]


@router.post('/purchases', status_code=201)
def create_purchase(data: PurchaseIn, db: DB):
    get_or_404(db, Supplier, data.supplier_id)
    purchase = Purchase(supplier_id=data.supplier_id, requested_by=data.requested_by, note=data.note, status='open')
    db.add(purchase); db.flush()
    for line in data.lines:
        get_or_404(db, StockItem, line.item_id)
        db.add(PurchaseLine(purchase_id=purchase.id, item_id=line.item_id, ordered=line.quantity, received=0, estimated_cost_cents=line.unit_cost_cents))
    db.commit()
    return {'id': purchase.id}


@router.post('/purchases/{key}/receive', status_code=201)
def receive(key: int, data: ReceiptIn, db: DB):
    aware(data.occurred_at)
    purchase = get_or_404(db, Purchase, key)
    if purchase.status not in {'open', 'partial'}:
        raise HTTPException(409, 'Esse pedido já foi recebido ou encerrado.')
    if db.scalar(select(PurchaseReceipt.id).where(PurchaseReceipt.supplier_id == purchase.supplier_id, PurchaseReceipt.document == data.document)):
        raise HTTPException(409, 'Essa nota do fornecedor já foi registrada.')
    total = sum(cents(line.quantity * line.unit_cost_cents) for line in data.lines)
    if data.invoice_total_cents != total and len(data.invoice_note) < 3:
        raise HTTPException(422, f'A nota informa {brl(data.invoice_total_cents)} e os itens somam {brl(total)}. Corrija quantidades e custos ou explique a diferença (desconto, frete, item faltante).')
    receipt = PurchaseReceipt(purchase_id=key, supplier_id=purchase.supplier_id, document=data.document, occurred_at=data.occurred_at,
                              total_cents=total, invoice_total_cents=data.invoice_total_cents, invoice_note=data.invoice_note)
    db.add(receipt); db.flush()
    ordered = {line.item_id: line for line in db.scalars(select(PurchaseLine).where(PurchaseLine.purchase_id == key))}
    for line in data.lines:
        order = ordered.get(line.item_id)
        if not order or order.received + line.quantity > order.ordered:
            raise HTTPException(409, 'Quantidade recebida maior que a pedida ou item fora do pedido.')
        move(db, get_or_404(db, StockItem, line.item_id), line.quantity, 'purchase', f'Nota {data.document}', data.occurred_at, receipt.id)
        db.add(PurchaseReceiptLine(receipt_id=receipt.id, **line.model_dump()))
        order.received += line.quantity
    supplier = get_or_404(db, Supplier, purchase.supplier_id)
    db.add(Expense(description=f'Compra #{key} · {supplier.name}', category='Mercadorias', amount_cents=total, occurred_at=data.occurred_at,
                   payee=supplier.name, document=data.document, receipt_id=receipt.id))
    purchase.status = 'received' if all(line.received == line.ordered for line in ordered.values()) else 'partial'
    db.commit()
    return {'receipt_id': receipt.id, 'total_cents': total, 'status': purchase.status}


@router.post('/purchases/{key}/close')
def close(key: int, data: CloseIn, db: DB):
    """Encerra um pedido sem esperar o restante (ex.: o fornecedor não tinha o item)."""
    purchase = get_or_404(db, Purchase, key)
    if purchase.status not in {'open', 'partial'}:
        raise HTTPException(409, 'Esse pedido já foi recebido ou encerrado.')
    purchase.status = 'closed'
    purchase.note = f'{purchase.note} · Encerrado: {data.reason}'.strip(' ·')[:1000]
    db.commit()
    return {'id': key, 'status': purchase.status}


def receipt_checks(db, start=None, end=None):
    """Confere cada nota: valor da nota x soma dos itens e custo real x estimado no pedido."""
    query = select(PurchaseReceipt).order_by(PurchaseReceipt.occurred_at.desc()).limit(300)
    if start is not None:
        query = query.where(PurchaseReceipt.occurred_at >= start, PurchaseReceipt.occurred_at < end)
    receipts = db.scalars(query).all()
    names = {s.id: s.name for s in db.scalars(select(Supplier))}
    items = {i.id: i for i in db.scalars(select(StockItem))}
    result = []
    for receipt in receipts:
        estimates = {line.item_id: line.estimated_cost_cents for line in db.scalars(select(PurchaseLine).where(PurchaseLine.purchase_id == receipt.purchase_id))}
        lines, issues = [], []
        difference = receipt.invoice_total_cents - receipt.total_cents
        if difference:
            issues.append(f'Nota {brl(receipt.invoice_total_cents)} x itens {brl(receipt.total_cents)} (diferença {brl(difference)}). Justificativa: {receipt.invoice_note}')
        for line in db.scalars(select(PurchaseReceiptLine).where(PurchaseReceiptLine.receipt_id == receipt.id)):
            item, estimate = items[line.item_id], estimates.get(line.item_id)
            variation = round((line.unit_cost_cents - estimate) * 100 / estimate, 1) if estimate else None
            if variation is not None and variation >= COST_TOLERANCE_PCT:
                issues.append(f'{item.name}: custo {brl(line.unit_cost_cents)} por {item.unit}, {variation:.0f}% acima do estimado ({brl(estimate)}).')
            lines.append({'name': item.name, 'unit': item.unit, 'quantity': line.quantity, 'unit_cost_cents': line.unit_cost_cents, 'cost_variation_pct': variation})
        result.append(as_dict(receipt, supplier=names[receipt.supplier_id], invoice_difference_cents=difference, lines=lines, issues=issues, ok=not issues))
    return result


def pending_orders(db):
    """Pedidos com itens que ainda não chegaram."""
    names = {s.id: s.name for s in db.scalars(select(Supplier))}
    items = {i.id: i for i in db.scalars(select(StockItem))}
    result = []
    for purchase in db.scalars(select(Purchase).where(Purchase.status.in_(['open', 'partial'])).order_by(Purchase.created_at)):
        missing = [{'name': items[line.item_id].name, 'unit': items[line.item_id].unit, 'missing': line.ordered - line.received}
                   for line in db.scalars(select(PurchaseLine).where(PurchaseLine.purchase_id == purchase.id)) if line.received < line.ordered]
        result.append({'id': purchase.id, 'supplier': names[purchase.supplier_id], 'requested_by': purchase.requested_by, 'created_at': purchase.created_at, 'missing': missing})
    return result


@router.get('/purchase-receipts')
def purchase_receipts(db: DB):
    return {'receipts': receipt_checks(db), 'pending_orders': pending_orders(db), 'cost_tolerance_pct': COST_TOLERANCE_PCT}
