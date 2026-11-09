from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import get_session
from .domain import aware, audit, get_or_404, lock, quantity, rows, now
from .inventory import Qty, ReasonIn, change_stock, valid_quantity
from .models import Recipe, RecipeLine, ProductionRun, ProductionInput, PortionStandard, PortionSample, StockItem, StockMovement
from .team import Input

router = APIRouter(prefix='/api', tags=['Produção'])
DB = Annotated[Session, Depends(get_session)]


class IngredientIn(Input):
    item_id: int
    quantity: Qty = Field(gt=0)


class RecipeIn(Input):
    product_id: int
    name: str = Field(min_length=2, max_length=120)
    yield_quantity: Qty = Field(gt=0)
    instructions: str = Field(min_length=3, max_length=3000)
    lines: list[IngredientIn] = Field(min_length=1, max_length=100)


class ProductionIn(Input):
    recipe_id: int
    planned_output: Qty = Field(gt=0)
    actual_output: Qty = Field(ge=0)
    occurred_at: datetime
    input_source: Literal['measured', 'recipe_estimate']
    inputs: list[IngredientIn] = Field(default_factory=list, max_length=100)
    lot_code: str = Field(default='', max_length=100)
    expiry: date | None = None
    note: str = Field(min_length=3, max_length=500)


class PortionStandardIn(Input):
    recipe_id: int
    component: str = Field(min_length=2, max_length=100)
    target_g: Qty = Field(gt=0, le=1_000_000)
    tolerance_g: Qty = Field(ge=0, le=1_000_000)


class SampleIn(Input):
    run_id: int
    standard_id: int
    measured_g: Qty = Field(gt=0, le=1_000_000)
    occurred_at: datetime
    note: str = Field(min_length=3, max_length=300)


@router.get('/recipes')
def recipes(db: DB):
    return [{'id': r.id, 'name': r.name, 'product_id': r.product_id, 'version': r.version, 'yield_quantity': r.yield_quantity, 'instructions': r.instructions,
             'lines': db.scalars(select(RecipeLine).where(RecipeLine.recipe_id == r.id)).all()} for r in rows(db, Recipe)]


@router.post('/recipes', status_code=201)
def create_recipe(data: RecipeIn, db: DB):
    lock(db, 601); product = get_or_404(db, StockItem, data.product_id)
    if product.kind != 'product' or not product.active:
        raise HTTPException(422, 'A saída da receita deve ser um produto ativo para venda.')
    valid_quantity(product, data.yield_quantity)
    if len({line.item_id for line in data.lines}) != len(data.lines):
        raise HTTPException(422, 'Ingrediente repetido na receita.')
    version = (db.scalar(select(func.max(Recipe.version)).where(Recipe.product_id == data.product_id)) or 0) + 1
    recipe = Recipe(**data.model_dump(exclude={'lines'}), version=version); db.add(recipe); db.flush()
    for line in data.lines:
        item = get_or_404(db, StockItem, line.item_id); valid_quantity(item, line.quantity)
        if item.id == product.id or item.kind == 'product' or not item.active:
            raise HTTPException(422, 'Use ingredientes e embalagens ativos nos componentes da receita.')
        db.add(RecipeLine(recipe_id=recipe.id, **line.model_dump()))
    audit(db, 'recipe', recipe.id, 'version_created', data.model_dump()); db.commit()
    return recipe


@router.post('/production-runs', status_code=201)
def produce(data: ProductionIn, db: DB):
    aware(data.occurred_at); lock(db, 601)
    recipe = get_or_404(db, Recipe, data.recipe_id); product = get_or_404(db, StockItem, recipe.product_id)
    valid_quantity(product, data.planned_output); valid_quantity(product, data.actual_output)
    lines = db.scalars(select(RecipeLine).where(RecipeLine.recipe_id == recipe.id).order_by(RecipeLine.item_id)).all()
    expected = {line.item_id: quantity(line.quantity * data.planned_output / recipe.yield_quantity) for line in lines}
    if data.input_source == 'measured':
        if len({line.item_id for line in data.inputs}) != len(data.inputs) or {line.item_id for line in data.inputs} != set(expected):
            raise HTTPException(422, 'Informe a quantidade medida de todos os ingredientes e embalagens, sem repetição.')
        inputs = {line.item_id: line.quantity for line in data.inputs}
    else:
        inputs = expected
    run = ProductionRun(recipe_id=recipe.id, planned_output=data.planned_output, actual_output=data.actual_output, occurred_at=data.occurred_at, input_source=data.input_source, note=data.note, total_cost_cents=0)
    db.add(run); db.flush(); cost = Decimal(0); cost_known = True
    for item_id, amount in sorted(inputs.items()):
        if amount <= 0:
            raise HTTPException(422, 'Quantidade estimada arredondou para zero; revise o tamanho do lote ou use medidas reais.')
        changes = change_stock(db, item_id, -amount, 'production' if data.actual_output else 'production_loss', data.note, data.occurred_at, reference_type='production', reference_id=run.id)
        cost += sum(-m.quantity * m.unit_cost_cents for m in changes)
        cost_known = cost_known and all(m.cost_known for m in changes)
        db.add(ProductionInput(run_id=run.id, item_id=item_id, expected=expected[item_id], quantity=amount))
    run.total_cost_cents = int(cost.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if data.actual_output > 0:
        unit_cost = (cost / data.actual_output).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        change_stock(db, product.id, data.actual_output, 'production_output', f'Produção #{run.id}: {data.note}', data.occurred_at, lot_code=data.lot_code or f'Produção #{run.id}', expiry=data.expiry,
                     unit_cost_cents=unit_cost, reference_type='production_output', reference_id=run.id, cost_known_override=cost_known)
    audit(db, 'production', run.id, 'produced', data.model_dump()); db.commit()
    return run


@router.get('/production-runs')
def production_runs(db: DB):
    from .valuation import CostBook, rounded
    costs = CostBook(db)
    return [{'id': r.id, 'recipe_id': r.recipe_id, 'planned_output': r.planned_output, 'actual_output': r.actual_output, 'occurred_at': r.occurred_at,
             'input_source': r.input_source, 'note': r.note, 'total_cost_cents': rounded(costs.production(r)[0]), 'original_total_cost_cents': r.total_cost_cents, 'voided': r.voided,
             'inputs': db.scalars(select(ProductionInput).where(ProductionInput.run_id == r.id)).all()} for r in rows(db, ProductionRun)]


@router.post('/production-runs/{key}/cancel')
def cancel_production(key: int, data: ReasonIn, db: DB):
    lock(db, 601); run = get_or_404(db, ProductionRun, key)
    if run.voided:
        raise HTTPException(409, 'Produção já cancelada.')
    outputs = db.scalars(select(StockMovement).where(StockMovement.reference_type == 'production_output', StockMovement.reference_id == key)).all()
    for moved in outputs:
        change_stock(db, moved.item_id, -moved.quantity, 'reversal', data.reason, now(), specific_lot=moved.lot_id, reference_type='production_cancel', reference_id=key)
    inputs = db.scalars(select(StockMovement).where(StockMovement.reference_type == 'production', StockMovement.reference_id == key).order_by(StockMovement.item_id)).all()
    for moved in inputs:
        change_stock(db, moved.item_id, -moved.quantity, 'reversal', data.reason, now(), specific_lot=moved.lot_id, reference_type='production_cancel', reference_id=key)
    run.voided = True; audit(db, 'production', key, 'cancelled', {'reason': data.reason}); db.commit(); return run


@router.get('/portion-standards')
def standards(db: DB):
    return rows(db, PortionStandard)


@router.post('/portion-standards', status_code=201)
def add_standard(data: PortionStandardIn, db: DB):
    lock(db, 601); get_or_404(db, Recipe, data.recipe_id)
    if db.scalar(select(PortionStandard.id).where(PortionStandard.recipe_id == data.recipe_id, PortionStandard.component == data.component)):
        raise HTTPException(409, 'Esse componente já tem padrão nessa versão de receita. Crie outra versão para alterar o padrão.')
    row = PortionStandard(**data.model_dump()); db.add(row); db.flush(); audit(db, 'portion_standard', row.id, 'created', data.model_dump()); db.commit(); return row


@router.post('/portion-samples', status_code=201)
def sample(data: SampleIn, db: DB):
    aware(data.occurred_at); run = get_or_404(db, ProductionRun, data.run_id); standard = get_or_404(db, PortionStandard, data.standard_id)
    if run.voided or standard.recipe_id != run.recipe_id or data.occurred_at < run.occurred_at:
        raise HTTPException(422, 'Confira a receita, o lote e a data da pesagem.')
    row = PortionSample(**data.model_dump()); db.add(row); db.flush(); audit(db, 'portion_sample', row.id, 'weighed', data.model_dump()); db.commit(); return row


@router.get('/portion-samples')
def samples(db: DB):
    result = []
    for sample in rows(db, PortionSample):
        standard = get_or_404(db, PortionStandard, sample.standard_id)
        result.append({'id': sample.id, 'run_id': sample.run_id, 'component': standard.component, 'target_g': standard.target_g, 'measured_g': sample.measured_g,
                       'difference_g': sample.measured_g - standard.target_g, 'outside_tolerance': abs(sample.measured_g - standard.target_g) > standard.tolerance_g, 'occurred_at': sample.occurred_at, 'note': sample.note})
    return result
