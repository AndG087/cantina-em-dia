"""Custos gerenciais corrigidos sem reescrever os lançamentos originais."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

from sqlalchemy import select

from .models import CostRevision, StockLot, StockMovement, ProductionRun


def rounded(value):
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


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
