from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
import io
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, now, audit, get_or_404, lock, rows
from .models import Sale, SaleLine, SalePayment, Settlement, SaleRefund, Expense, ExpensePayment, StockItem, StockMovement, StockLot, ProductionRun, CashSession, CashHandover, Goal, GoalAssessment
from .purchases import Money
from .team import Input

router = APIRouter(prefix='/api', tags=['Relatórios e meta'])
DB = Annotated[Session, Depends(get_session)]


def period(month):
    try:
        beginning = datetime.strptime(month, '%Y-%m').replace(tzinfo=TZ)
        if beginning.strftime('%Y-%m') != month:
            raise ValueError()
        end = beginning.replace(year=beginning.year + 1, month=1) if beginning.month == 12 else beginning.replace(month=beginning.month + 1)
        return beginning, end
    except (ValueError, OverflowError):
        raise HTTPException(422, 'Informe um mês válido no formato AAAA-MM.')


def rounded(value):
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def monthly_report(db, month):
    start, end = period(month)
    sales = db.scalars(select(Sale).where(Sale.occurred_at >= start, Sale.occurred_at < end)).all()
    expenses = db.scalars(select(Expense).where(Expense.occurred_at >= start, Expense.occurred_at < end, Expense.voided.is_(False))).all()
    movements = db.scalars(select(StockMovement).where(StockMovement.occurred_at >= start, StockMovement.occurred_at < end)).all()
    productions = db.scalars(select(ProductionRun).where(ProductionRun.occurred_at >= start, ProductionRun.occurred_at < end, ProductionRun.voided.is_(False))).all()
    voided_runs = set(db.scalars(select(ProductionRun.id).where(ProductionRun.voided.is_(True))).all())
    valid = [sale for sale in sales if not sale.voided]
    net_sales = sum(s.total_cents for s in valid)
    gross_sales = sum(s.total_cents + s.discount_cents for s in sales)
    cogs = sum(s.cost_cents for s in valid)
    cancellations_cost = sum(s.cost_cents for s in sales if s.voided and not s.stock_returned)
    negative = [m for m in movements if m.quantity < 0 and (m.kind in {'loss', 'staff', 'complimentary', 'adjustment', 'production_loss'}) and not (m.reference_type == 'production' and m.reference_id in voided_runs)]
    losses = rounded(sum(-m.quantity * m.unit_cost_cents for m in negative)) + cancellations_cost
    operating_expenses = sum(e.amount_cents for e in expenses if e.receipt_id is None and e.purpose != 'manager_compensation')
    manager_expenses = sum(e.amount_cents for e in expenses if e.receipt_id is None and e.purpose == 'manager_compensation')
    sale_fees = db.scalar(select(func.coalesce(func.sum(Settlement.fee_cents), 0)).join(SalePayment, Settlement.payment_id == SalePayment.id).join(Sale, SalePayment.sale_id == Sale.id).where(Sale.occurred_at >= start, Sale.occurred_at < end))
    received = db.scalars(select(Settlement).where(Settlement.occurred_at >= start, Settlement.occurred_at < end)).all()
    refunds = db.scalars(select(SaleRefund).where(SaleRefund.occurred_at >= start, SaleRefund.occurred_at < end)).all()
    digital_net = sum(s.gross_cents - s.fee_cents for s in received)
    cash_received = db.scalar(select(func.coalesce(func.sum(SalePayment.amount_cents), 0)).join(Sale, SalePayment.sale_id == Sale.id).where(Sale.occurred_at >= start, Sale.occurred_at < end, SalePayment.method == 'cash'))
    refunds_total = sum(r.amount_cents for r in refunds)
    receipts_net = cash_received + digital_net - refunds_total
    paid = db.scalars(select(ExpensePayment).where(ExpensePayment.occurred_at >= start, ExpensePayment.occurred_at < end)).all()
    recorded_result = net_sales - cogs - losses - operating_expenses - sale_fees
    pending_digital = db.execute(select(SalePayment.id, SalePayment.amount_cents, func.coalesce(func.sum(Settlement.gross_cents), 0)).join(Sale, SalePayment.sale_id == Sale.id).outerjoin(Settlement, Settlement.payment_id == SalePayment.id).where(Sale.occurred_at >= start, Sale.occurred_at < end, Sale.voided.is_(False), SalePayment.method != 'cash').group_by(SalePayment.id)).all()
    missing_settlements = sum(1 for _, total, received_amount in pending_digital if total > received_amount)
    unmapped_sales = sum(1 for s in valid if not s.stock_applied)
    estimated_runs = sum(1 for r in productions if r.input_source != 'measured')
    unknown_costs = sum(1 for s in valid if s.stock_applied and not s.cost_known) + sum(1 for m in negative if not m.cost_known)
    completeness_notes = []
    if unmapped_sales: completeness_notes.append(f'{unmapped_sales} venda(s) importada(s) sem itens ou custo de estoque.')
    if estimated_runs: completeness_notes.append(f'{estimated_runs} produção(ões) com consumo estimado, sem medição confirmada.')
    if missing_settlements: completeness_notes.append(f'{missing_settlements} pagamento(s) digital(is) sem conciliação completa das taxas.')
    if unknown_costs: completeness_notes.append(f'{unknown_costs} registro(s) com custo de estoque ainda não confirmado.')
    complete = not completeness_notes
    closing_stock = rounded(db.scalar(select(func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_cost_cents), 0)).where(StockMovement.occurred_at < end)))
    daily = defaultdict(int)
    for sale in valid:
        daily[sale.occurred_at.astimezone(TZ).date().isoformat()] += sale.total_cents
    series = []
    day = start.date(); last = min((end - timedelta(days=1)).date(), now().astimezone(TZ).date())
    while day <= last:
        series.append({'day': day.isoformat(), 'sales_cents': daily[day.isoformat()]}); day += timedelta(days=1)
    categories = defaultdict(int)
    for expense in expenses:
        categories['Mercadorias (aquisição)' if expense.receipt_id else expense.category] += expense.amount_cents
    products = db.execute(select(StockItem.name, StockItem.unit, func.sum(SaleLine.quantity), func.sum(SaleLine.quantity * SaleLine.unit_price_cents)).join(SaleLine, SaleLine.item_id == StockItem.id).join(Sale, SaleLine.sale_id == Sale.id).where(Sale.occurred_at >= start, Sale.occurred_at < end, Sale.voided.is_(False)).group_by(StockItem.id).order_by(func.sum(SaleLine.quantity * SaleLine.unit_price_cents).desc()).limit(10)).all()
    goal = db.scalar(select(Goal).where(Goal.month == month).order_by(Goal.version.desc()).limit(1))
    bases = {'gross_sales': gross_sales, 'net_sales': net_sales, 'receipts': receipts_net, 'operating_result': recorded_result if complete else None}
    basis = bases.get(goal.basis) if goal else None
    variable = max(0, basis - goal.target_cents) if goal and basis is not None else None
    cash_difference = db.scalar(select(func.coalesce(func.sum(CashSession.difference_cents), 0)).where(CashSession.closed_at >= start, CashSession.closed_at < end))
    handover_difference = db.scalar(select(func.coalesce(func.sum(CashHandover.difference_cents), 0)).where(CashHandover.occurred_at >= start, CashHandover.occurred_at < end))
    return {'month': month, 'generated_at': now(), 'sales_count': len(valid), 'gross_sales_cents': gross_sales, 'sales_cents': net_sales,
            'discount_cents': sum(s.discount_cents for s in sales), 'cancelled_sales_cents': sum(s.total_cents for s in sales if s.voided),
            'cogs_cents': cogs, 'losses_and_staff_cents': losses, 'operating_expenses_cents': operating_expenses, 'manager_expenses_cents': manager_expenses,
            'purchase_expenses_cents': sum(e.amount_cents for e in expenses if e.receipt_id), 'all_expenses_cents': sum(e.amount_cents for e in expenses),
            'fees_cents': sale_fees, 'receipts_net_cents': receipts_net, 'payments_cantina_cents': sum(p.amount_cents for p in paid if p.source == 'cantina'),
            'payments_owner_cents': sum(p.amount_cents for p in paid if p.source == 'owner'), 'cashflow_cents': receipts_net - sum(p.amount_cents for p in paid if p.source == 'cantina'),
            'recorded_result_cents': recorded_result, 'operating_result_cents': recorded_result if complete else None, 'result_after_recorded_compensation_cents': recorded_result - manager_expenses if complete else None,
            'closing_stock_value_cents': closing_stock, 'cash_difference_cents': cash_difference + handover_difference, 'daily': series,
            'expenses_by_category': [{'category': key, 'amount_cents': value} for key, value in categories.items()],
            'top_products': [{'name': name, 'unit': unit, 'quantity': amount, 'gross_cents': rounded(value)} for name, unit, amount, value in products],
            'completeness_notes': completeness_notes, 'result_complete': complete,
            'goal': {'id': goal.id, 'version': goal.version, 'basis': goal.basis, 'target_cents': goal.target_cents, 'agreement': goal.agreement, 'basis_cents': basis, 'variable_cents': variable} if goal else None}


@router.get('/reports/monthly')
def monthly(db: DB, month: str):
    return monthly_report(db, month)


@router.get('/reports/monthly.csv')
def monthly_csv(db: DB, month: str):
    report = monthly_report(db, month); stream = io.StringIO(); writer = csv.writer(stream, delimiter=';')
    writer.writerow(['mes', 'indicador', 'valor_centavos'])
    for key in ['gross_sales_cents', 'sales_cents', 'cogs_cents', 'losses_and_staff_cents', 'operating_expenses_cents', 'fees_cents', 'operating_result_cents', 'receipts_net_cents', 'cashflow_cents', 'closing_stock_value_cents']:
        writer.writerow([month, key, report[key] if report[key] is not None else 'PENDENTE'])
    return Response('\ufeff' + stream.getvalue(), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="relatorio-{month}.csv"'})


@router.get('/dashboard')
def dashboard(db: DB, month: str | None = None):
    report = monthly_report(db, month or now().astimezone(TZ).strftime('%Y-%m'))
    low = db.scalars(select(StockItem).where(StockItem.active.is_(True), (StockItem.balance < StockItem.minimum) | (StockItem.balance == 0)).order_by(StockItem.name).limit(12)).all()
    expired = db.scalar(select(func.count()).select_from(StockLot).where(StockLot.balance > 0, StockLot.expiry < now().astimezone(TZ).date()))
    pending_expenses = db.scalar(select(func.coalesce(func.sum(Expense.amount_cents), 0)).where(Expense.voided.is_(False))) - db.scalar(select(func.coalesce(func.sum(ExpensePayment.amount_cents), 0)))
    sessions = db.scalars(select(CashSession).where(CashSession.closed_at.is_(None))).all()
    from .team import responsibility
    from .finance import expected_cash
    return {'report': report, 'responsibility': responsibility(db), 'low_stock': low, 'expired_lots': expired, 'pending_expenses_cents': pending_expenses,
            'open_cash_sessions': [{'id': s.id, 'opened_at': s.opened_at, 'expected_cents': expected_cash(db, s)} for s in sessions], 'registered_items': db.scalar(select(func.count()).select_from(StockItem))}


class GoalIn(Input):
    month: str = Field(pattern=r'^\d{4}-\d{2}$')
    basis: Literal['gross_sales', 'net_sales', 'receipts', 'operating_result']
    target_cents: Money
    agreement: str = Field(min_length=5, max_length=1000)


class AssessmentIn(Input):
    month: str = Field(pattern=r'^\d{4}-\d{2}$')
    owner_approved: bool = False
    note: str = Field(min_length=5, max_length=500)


@router.get('/goals')
def goals(db: DB):
    return rows(db, Goal)


@router.post('/goals', status_code=201)
def create_goal(data: GoalIn, db: DB):
    period(data.month); lock(db, 701)
    version = (db.scalar(select(func.max(Goal.version)).where(Goal.month == data.month)) or 0) + 1
    row = Goal(**data.model_dump(), version=version); db.add(row); db.flush(); audit(db, 'goal', row.id, 'version_created', data.model_dump()); db.commit(); return row


@router.post('/goal-assessments', status_code=201)
def assess_goal(data: AssessmentIn, db: DB):
    report = monthly_report(db, data.month); goal = report['goal']
    if not goal:
        raise HTTPException(409, 'Defina a meta e sua base antes de apurar a parcela variável.')
    if goal['basis_cents'] is None:
        raise HTTPException(409, 'Há pendências de custos, produção ou conciliação que impedem apurar a base de resultado.')
    if data.owner_approved and data.month >= now().astimezone(TZ).strftime('%Y-%m'):
        raise HTTPException(409, 'O mês ainda não terminou. Registre uma simulação sem aprovação de fechamento.')
    row = GoalAssessment(goal_id=goal['id'], basis_cents=goal['basis_cents'], variable_cents=goal['variable_cents'], owner_approved=data.owner_approved, note=data.note, report=jsonable_encoder(report))
    db.add(row); db.flush(); audit(db, 'goal_assessment', row.id, 'approved' if data.owner_approved else 'simulated', data.model_dump()); db.commit(); return row


@router.get('/goal-assessments')
def assessments(db: DB):
    return rows(db, GoalAssessment)
