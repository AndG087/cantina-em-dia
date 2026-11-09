from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import audit, get_or_404, lock, rows
from .models import CostRevision, StockLot, Sale
from .team import Input
from .valuation import CostBook, rounded

router = APIRouter(prefix='/api', tags=['Retificação de custos'])
DB = Annotated[Session, Depends(get_session)]


class CostIn(Input):
    lot_id: int
    unit_cost_cents: Decimal = Field(ge=0, le=2_000_000_000, max_digits=16, decimal_places=6)
    confirmed: Literal[True]
    document: str = Field(min_length=3, max_length=300)
    reason: str = Field(min_length=5, max_length=500)


class CommitIn(CostIn):
    expected_fingerprint: str = Field(min_length=64, max_length=64)


def preview(db, data):
    lot = get_or_404(db, StockLot, data.lot_id)
    before = CostBook(db)
    if lot.id in before.outputs:
        raise HTTPException(409, 'Este lote foi produzido na cantina. Corrija os lotes dos ingredientes e embalagens; o produto pronto será recalculado.')
    old, known = before.lot(lot.id)
    if old == data.unit_cost_cents and known: raise HTTPException(409, 'O custo confirmado já corresponde ao informado.')
    after = CostBook(db, {lot.id: (data.unit_cost_cents, True)})
    sales = []
    for sale in db.scalars(select(Sale).order_by(Sale.id)):
        previous, previous_known = before.sale(sale); revised, revised_known = after.sale(sale)
        if (previous, previous_known) != (revised, revised_known):
            sales.append({'id': sale.id, 'before_cents': previous, 'after_cents': revised, 'voided': sale.voided})
    runs = []
    for run in before.runs.values():
        previous, previous_known = before.production(run); revised, revised_known = after.production(run)
        if (previous, previous_known) != (revised, revised_known):
            runs.append({'id': run.id, 'before_cents': rounded(previous), 'after_cents': rounded(revised), 'voided': run.voided})
    affected = {key for key in before.lots if before.lot(key) != after.lot(key)}
    instants = [move.occurred_at for move in before.movements if move.lot_id in affected]
    purchase = any(m.lot_id == lot.id and m.reference_type == 'purchase_receipt' for m in before.movements)
    return {'lot_id': lot.id, 'previous_cost_cents': old, 'previous_known': known, 'unit_cost_cents': data.unit_cost_cents,
            'expected_fingerprint': before.fingerprint(), 'sales': sales, 'productions': runs,
            'earliest_affected_at': min(instants) if instants else lot.received_at,
            'purchase_linked': purchase, 'affected_lots': sorted(affected)}


@router.get('/cost-revisions')
def revisions(db: DB):
    return rows(db, CostRevision)


@router.post('/cost-revisions/preview')
def preview_revision(data: CostIn, db: DB):
    return jsonable_encoder(preview(db, data), custom_encoder={Decimal: str})


@router.post('/cost-revisions', status_code=201)
def create_revision(data: CommitIn, db: DB):
    lock(db, 904)
    result = preview(db, data)
    if result['expected_fingerprint'] != data.expected_fingerprint:
        raise HTTPException(409, 'O estoque ou os custos mudaram desde a prévia. Gere uma nova prévia antes de confirmar.')
    row = CostRevision(lot_id=data.lot_id, previous_cost_cents=result['previous_cost_cents'], previous_known=result['previous_known'],
                       unit_cost_cents=data.unit_cost_cents, document=data.document, reason=data.reason, impact=jsonable_encoder(result, custom_encoder={Decimal: str}))
    db.add(row); db.flush(); audit(db, 'cost_revision', row.id, 'confirmed', jsonable_encoder({**data.model_dump(), 'impact': result}, custom_encoder={Decimal: str})); db.commit(); return row
