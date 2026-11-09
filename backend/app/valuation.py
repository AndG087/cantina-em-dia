"""Custos gerenciais corrigidos sem reescrever os lançamentos originais."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

from sqlalchemy import select

from .models import CostRevision, StockLot, StockMovement, ProductionRun


def rounded(value):
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def lot_cost(db, lot, cache=None, visiting=None):
    """Consulta apenas a origem do lote movimentado, sem carregar todo o histórico."""
    cache = cache if cache is not None else {}
    if lot.id in cache: return cache[lot.id]
    visited = set(visiting or ())
    if lot.id in visited: raise ValueError('Ciclo inválido no custo dos lotes.')
    visited.add(lot.id)
    revision = db.scalar(select(CostRevision).where(CostRevision.lot_id == lot.id).order_by(CostRevision.id.desc()).limit(1))
    if revision:
        result = (revision.unit_cost_cents, True)
    else:
        output = db.scalar(select(StockMovement).where(StockMovement.lot_id == lot.id, StockMovement.reference_type == 'production_output', StockMovement.quantity > 0).limit(1))
        if output:
            run = db.get(ProductionRun, output.reference_id)
            moves = db.scalars(select(StockMovement).where(StockMovement.reference_type == 'production', StockMovement.reference_id == run.id, StockMovement.quantity < 0)).all()
            values = [(move, lot_cost(db, db.get(StockLot, move.lot_id), cache, visited)) for move in moves]
            total = sum((-move.quantity * cost for move, (cost, _) in values), Decimal(0))
            result = ((total / run.actual_output).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP), bool(values) and all(known for _, (_, known) in values))
        else: result = (lot.unit_cost_cents, lot.cost_known)
    cache[lot.id] = result
    return result


class CostBook:
    def __init__(self, db, override=None):
        db.flush()
        self.lots = {lot.id: lot for lot in db.scalars(select(StockLot))}
        self.movements = list(db.scalars(select(StockMovement).order_by(StockMovement.id)))
        self.runs = {run.id: run for run in db.scalars(select(ProductionRun))}
        self.revisions = list(db.scalars(select(CostRevision).order_by(CostRevision.id)))
        self.overrides = {r.lot_id: (r.unit_cost_cents, True) for r in self.revisions}
        self.overrides.update(override or {})
        self.outputs = {}; self.inputs = defaultdict(list); self.sales = defaultdict(list); self.cache = {}
        for move in self.movements:
            if move.reference_type == 'production_output' and move.quantity > 0: self.outputs[move.lot_id] = move.reference_id
            if move.reference_type in {'production', 'production_loss'} and move.quantity < 0: self.inputs[move.reference_id].append(move)
            if move.reference_type == 'sale' and move.quantity < 0: self.sales[move.reference_id].append(move)

    def lot(self, key, visiting=None):
        if key in self.cache: return self.cache[key]
        visited = set(visiting or ())
        if key in visited: raise ValueError('Ciclo inválido no custo dos lotes.')
        visited.add(key); lot = self.lots[key]
        if key in self.overrides:
            result = self.overrides[key]
        elif key in self.outputs:
            run = self.runs[self.outputs[key]]
            cost, known = self.production(run, visited)
            result = ((cost / run.actual_output).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP), known)
        else:
            result = (lot.unit_cost_cents, lot.cost_known)
        self.cache[key] = result
        return result

    def production(self, run, visiting=None):
        moves = self.inputs[run.id]
        values = [(move, self.lot(move.lot_id, visiting)) for move in moves]
        return sum((-move.quantity * cost for move, (cost, _) in values), Decimal(0)), bool(values) and all(known for _, (_, known) in values)

    def sale(self, sale):
        moves = self.sales[sale.id]
        if not sale.stock_applied or not moves: return sale.cost_cents, False
        values = [(move, self.lot(move.lot_id)) for move in moves]
        return rounded(sum(-move.quantity * cost for move, (cost, _) in values)), all(known for _, (_, known) in values)

    def fingerprint(self):
        value = {'revisions': [r.id for r in self.revisions], 'movements': [m.id for m in self.movements],
                 'lots': [(l.id, str(l.balance)) for l in sorted(self.lots.values(), key=lambda value: value.id)]}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
