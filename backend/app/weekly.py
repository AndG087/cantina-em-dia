"""Relatório semanal e situação das cinco rotinas pedidas pela gestão.

A semana vai de segunda a domingo e é comparada com a anterior. O relatório pode ser
impresso, copiado para o WhatsApp, baixado em Markdown e guardado como versão entregue.
"""
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .cash import cash_days
from .database import get_session
from .domain import TZ, Input, as_dict, brl, day_start, ddmm, get_or_404, now, qty, today
from .expenses import expense_alerts
from .models import CashSession, Expense, InventoryCount, StockItem, WeeklyReport
from .purchases import pending_orders, receipt_checks
from .school import SHIFTS, WEEKDAYS, calendar_days, calendar_summary, last_check
from .stock import balances

router = APIRouter(prefix='/api', tags=['Relatório semanal'])
DB = Annotated[Session, Depends(get_session)]
STATUS = {'open': 'Normal', 'closed': 'Fechada', 'reduced': 'Movimento reduzido', 'increased': 'Movimento maior'}
INVENTORY_INTERVAL_DAYS = 7


class SaveIn(Input):
    week: date
    note: str = Field(min_length=3, max_length=1000)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def week_totals(db, monday):
    """Totais informados nos fechamentos de caixa e despesas lançadas na semana."""
    start, end = day_start(monday), day_start(monday + timedelta(days=7))
    closed = db.scalars(select(CashSession).where(CashSession.opened_at >= start, CashSession.opened_at < end, CashSession.closed_at.is_not(None))).all()
    expenses = db.scalars(select(Expense).where(Expense.occurred_at >= start, Expense.occurred_at < end)).all()
    cash, pix, card, voucher = (sum(getattr(r, field) or 0 for r in closed) for field in ('cash_sales_cents', 'pix_cents', 'card_cents', 'voucher_cents'))
    return {'sales_cents': cash + pix + card + voucher, 'cash_cents': cash, 'pix_cents': pix, 'card_cents': card, 'voucher_cents': voucher, 'days_closed': len(closed),
            'difference_cents': sum(r.difference_cents for r in closed), 'expenses_cents': sum(e.amount_cents for e in expenses if e.receipt_id is None),
            'purchases_cents': sum(e.amount_cents for e in expenses if e.receipt_id is not None)}


def variation(current, previous):
    if not previous:
        return '—'
    return f'{(current - previous) * 100 / previous:+.1f}%'.replace('.', ',')


def sentence(text):
    text = str(text).strip().replace('|', '/')
    return text if text.endswith(('.', '?', '!')) else text + '.'


def weekly_report(db, any_day):
    monday, current_day = monday_of(any_day), today()
    sunday = monday + timedelta(days=6)
    if monday > current_day:
        raise HTTPException(422, 'A semana escolhida ainda não começou.')
    start, end = day_start(monday), day_start(sunday + timedelta(days=1))
    totals, previous = week_totals(db, monday), week_totals(db, monday - timedelta(days=7))
    cash = [d for d in cash_days(db, monday, min(sunday, current_day)) if not (d['state'] == 'not_applicable' and d['day'].weekday() >= 5)]
    receipts = receipt_checks(db, start, end)
    alerts = expense_alerts(db, monday, sunday)
    items = {i.id: i for i in db.scalars(select(StockItem))}
    counts = db.scalars(select(InventoryCount).where(InventoryCount.counted_at >= start, InventoryCount.counted_at < end)).all()
    stock = balances(db)
    low = sorted((i for i in items.values() if i.active and stock.get(i.id, 0) <= i.minimum), key=lambda i: i.name)
    upcoming = calendar_summary(db, sunday + timedelta(days=1), 14)
    week_days = [d for d in calendar_days(db, monday, sunday) if d['day'].weekday() < 5]
    orders, check = pending_orders(db), last_check(db)
    pending_cash = [d for d in cash if d['state'] in {'pending', 'outdated'}]
    open_alerts = [a for a in alerts['alerts'] if a['explanation'] is None]
    divergent = [r for r in receipts if not r['ok']]
    actions = []
    if pending_cash:
        actions.append(f"Conferir o caixa de {len(pending_cash)} dia(s): {', '.join(ddmm(d['day']) for d in pending_cash)}.")
    if divergent:
        actions.append(f'Verificar {len(divergent)} nota(s) com divergência.')
    if orders:
        actions.append(f'Acompanhar {len(orders)} pedido(s) com itens a receber.')
    if not counts:
        actions.append('Fazer a contagem do estoque (nenhuma contagem na semana).')
    if low:
        actions.append(f'Repor ou confirmar {len(low)} item(ns) no mínimo ou abaixo dele.')
    if open_alerts:
        actions.append(f'Explicar {len(open_alerts)} gasto(s) fora do padrão.')
    if check is None or check['overdue']:
        actions.append('Averiguar o calendário da escola (cursos, feriados e paralisações).')

    lines = [f'# Relatório semanal · {ddmm(monday)} a {sunday:%d/%m/%Y}', '',
             f"Cantina do Senai Paulista · gerado em {now().astimezone(TZ):%d/%m/%Y %H:%M}" + ('' if sunday < current_day else ' · **semana em andamento**'), '',
             '## Resumo', '', '| Indicador | Semana | Semana anterior | Variação |', '|---|---:|---:|---:|']
    for label, key in [('Vendas informadas nos fechamentos', 'sales_cents'), ('Em dinheiro', 'cash_cents'), ('Pix', 'pix_cents'), ('Cartão', 'card_cents'), ('Voucher', 'voucher_cents'),
                       ('Compras de mercadorias', 'purchases_cents'), ('Outras despesas', 'expenses_cents'), ('Diferenças de caixa', 'difference_cents')]:
        lines.append(f'| {label} | {brl(totals[key])} | {brl(previous[key])} | {variation(totals[key], previous[key])} |')
    lines += ['', '## Caixa: aberturas e fechamentos', '']
    if cash:
        lines += ['| Dia | Calendário | Vendas | Retiradas | Diferença | Conferência |', '|---|---|---:|---:|---:|---|']
        for d in cash:
            review = f" ({'sem ressalvas' if d['review']['status'] == 'ok' else 'com ressalvas'})" if d['state'] == 'reviewed' else ''
            lines.append(f"| {WEEKDAYS[d['day'].weekday()][:3]} {ddmm(d['day'])} | {STATUS[d['calendar_status']]} | {brl(d['cash_sales_cents'] + d['pix_cents'] + d['card_cents'] + d['voucher_cents'])} | "
                         f"{brl(d['withdrawals_cents'])} | {brl(d['difference_cents'])} | {d['state_label']}{review} |")
        issues = [f"- {ddmm(d['day'])}: {sentence(issue)}" for d in cash for issue in d['issues']]
        lines += [''] + (issues or ['Nenhum ponto de atenção nas aberturas e fechamentos.'])
    else:
        lines.append('Nenhum dia a conferir.')
    lines += ['', '## Compras e estoque', '', f"- {len(receipts)} nota(s) recebida(s), {brl(sum(r['total_cents'] for r in receipts))} em mercadorias."]
    lines += [f"- Nota {r['document']} ({r['supplier']}): {' '.join(sentence(i) for i in r['issues'])}" for r in divergent]
    lines += [f"- Pedido #{o['id']} ({o['supplier']}): falta receber {'; '.join(qty(m['missing']) + ' ' + m['unit'] + ' de ' + m['name'] for m in o['missing'])}." for o in orders]
    differences = [c for c in counts if c.difference]
    lines.append(f'- Contagem: {len(counts)} item(ns) contado(s), {len(differences)} com diferença (saídas sem lançamento, como vendas, consumo ou perdas).' if counts else '- Contagem: nenhuma registrada na semana.')
    lines += [f'  - {items[c.item_id].name}: esperado {qty(c.expected)}, contado {qty(c.counted)} {items[c.item_id].unit}. {sentence(c.note)}' for c in differences]
    if low:
        lines.append('- No mínimo ou abaixo: ' + ', '.join(f'{i.name} ({qty(stock.get(i.id, 0))} {i.unit})' for i in low[:15]) + ('…' if len(low) > 15 else '') + '.')
    lines += ['', '## Gastos fora do padrão', '']
    for a in alerts['alerts']:
        explanation = f" Explicação: {sentence(a['explanation']['note'])}" if a['explanation'] else ' **Sem explicação.**'
        lines.append(f"- [{a['kind_label']}] {sentence(a['title'])} {a['detail']}{explanation}")
    if not alerts['alerts']:
        lines.append('Nenhum gasto fora do padrão nos registros da semana.')
    lines += ['', '## Calendário da escola', '', f"- Última averiguação: {check['checked_at'].astimezone(TZ):%d/%m/%Y} ({check['source']})." if check else '- Calendário ainda não averiguado.']
    altered = [d for d in week_days if d['status'] != 'open']
    lines.append('- Nesta semana: ' + ('; '.join(f"{ddmm(d['day'])} {STATUS[d['status']].lower()}" for d in altered) if altered else 'funcionamento normal em todos os dias úteis.'))
    lines.append('- Próximas duas semanas: ' + ('; '.join(f"{e['title']} ({ddmm(e['starts_on'])}, {e['effect_label'].lower()})" for e in upcoming['events']) if upcoming['events'] else 'sem feriados ou paralisações registrados.'))
    active = upcoming['active_courses']
    if active:
        students = [c['students'] for c in active if c['students'] is not None]
        by_shift = '; '.join(f"{label}: {', '.join(c['name'] for c in active if c['shift'] == key)}" for key, label in SHIFTS.items() if any(c['shift'] == key for c in active))
        lines.append(f"- Cursos em andamento: {len(active)}{f' (cerca de {sum(students)} alunos)' if students else ''}. {by_shift}.")
    lines += [f"- Termina em {ddmm(c['ends_on'])}: {c['name']}." for c in upcoming['ending_soon']]
    lines += [f"- Começa em {ddmm(c['starts_on'])}: {c['name']}." for c in upcoming['starting_soon']]
    lines += ['', '## Pendências', ''] + ([f'- [ ] {a}' for a in actions] or ['Nenhuma pendência nos registros.'])
    lines += ['', '---', '', 'Valores conforme os registros lançados. Diferenças e alertas são pontos de conferência, não prova de erro ou desvio.']

    text = [f'*Relatório semanal da cantina* · {ddmm(monday)} a {ddmm(sunday)}', '',
            f"*Vendas:* {brl(totals['sales_cents'])} ({variation(totals['sales_cents'], previous['sales_cents'])} vs. semana anterior)",
            f"Dinheiro {brl(totals['cash_cents'])} · Pix {brl(totals['pix_cents'])} · Cartão {brl(totals['card_cents'])} · Voucher {brl(totals['voucher_cents'])}",
            f"*Compras:* {brl(totals['purchases_cents'])} · *Outras despesas:* {brl(totals['expenses_cents'])}",
            f"*Caixa:* {sum(1 for d in cash if d['state'] == 'reviewed')} dia(s) conferido(s), {len(pending_cash)} pendente(s) · diferenças {brl(totals['difference_cents'])}",
            f"*Notas:* {len(receipts)} recebida(s), {len(divergent)} com divergência · *Estoque:* {len(low)} item(ns) a repor",
            f"*Gastos fora do padrão:* {len(alerts['alerts'])} ({len(open_alerts)} sem explicação)"]
    if upcoming['events']:
        text.append('*Calendário:* ' + '; '.join(f"{e['title']} {ddmm(e['starts_on'])}" for e in upcoming['events'][:4]))
    if actions:
        text += ['', '*Pendências:*'] + [f'• {a}' for a in actions]
    return {'week_start': monday, 'week_end': sunday, 'complete_week': sunday < current_day, 'totals': totals, 'previous': previous,
            'cash_pending_days': len(pending_cash), 'open_alerts': len(open_alerts), 'actions': actions, 'markdown': '\n'.join(lines), 'text': '\n'.join(text)}


@router.get('/reports/weekly')
def weekly(db: DB, week: date | None = None):
    return weekly_report(db, week or today())


@router.get('/reports/weekly.md')
def weekly_markdown(db: DB, week: date | None = None):
    report = weekly_report(db, week or today())
    return Response(report['markdown'], media_type='text/markdown; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="relatorio-semanal-{report["week_start"]}.md"'})


@router.get('/weekly-reports')
def saved(db: DB):
    rows = db.scalars(select(WeeklyReport).order_by(WeeklyReport.id.desc()).limit(100))
    return [{'id': r.id, 'week_start': r.week_start, 'version': r.version, 'note': r.note, 'created_at': r.created_at} for r in rows]


@router.get('/weekly-reports/{key}')
def saved_detail(key: int, db: DB):
    row = get_or_404(db, WeeklyReport, key)
    return as_dict(row, markdown=row.snapshot['markdown'], text=row.snapshot['text'])


@router.post('/weekly-reports', status_code=201)
def save_report(data: SaveIn, db: DB):
    report = weekly_report(db, data.week)
    version = (db.scalar(select(func.max(WeeklyReport.version)).where(WeeklyReport.week_start == report['week_start'])) or 0) + 1
    row = WeeklyReport(week_start=report['week_start'], version=version, note=data.note, snapshot=jsonable_encoder(report))
    db.add(row); db.commit(); db.refresh(row)
    return {'id': row.id, 'week_start': row.week_start, 'version': row.version}


@router.get('/routine')
def routine(db: DB):
    """Situação das cinco rotinas: ok (em dia), attention (atenção) ou pending (pendente)."""
    current_day = today()
    check = last_check(db)
    window = calendar_summary(db, current_day, 14)
    if check is None:
        calendar = ('pending', 'Ainda não averiguado. Confirme cursos, feriados e paralisações com a escola.')
    else:
        age = check['age_days']
        when = 'hoje' if age == 0 else 'ontem' if age == 1 else f'há {age} dias'
        calendar = ('attention' if check['overdue'] else 'ok',
                    f"Averiguado {when}. {len(window['active_courses'])} curso(s) em andamento; {len(window['events'])} evento(s) nos próximos 14 dias.")
    week_ago = day_start(current_day - timedelta(days=7))
    divergent = sum(1 for r in receipt_checks(db, week_ago, day_start(current_day + timedelta(days=1))) if not r['ok'])
    orders = len(pending_orders(db))
    last_count = db.scalar(select(func.max(InventoryCount.counted_at)))
    age = (current_day - last_count.astimezone(TZ).date()).days if last_count else None
    purchases = ('pending' if last_count is None else 'attention' if divergent or age > INVENTORY_INTERVAL_DAYS else 'ok',
                 f"{orders} pedido(s) com itens a receber; {divergent} nota(s) com divergência em 7 dias; "
                 + (f'última contagem há {age} dia(s).' if last_count else 'nenhuma contagem de estoque registrada.'))
    pending = [d for d in cash_days(db, current_day - timedelta(days=7), current_day - timedelta(days=1)) if d['state'] in {'pending', 'outdated'}]
    cash = ('attention', f"{len(pending)} dia(s) aguardando conferência: {', '.join(ddmm(d['day']) for d in pending)}.") if pending else ('ok', 'Últimos 7 dias conferidos ou sem movimento previsto.')
    last_week = monday_of(current_day) - timedelta(days=7)
    report = db.scalar(select(WeeklyReport).where(WeeklyReport.week_start == last_week).order_by(WeeklyReport.version.desc()).limit(1))
    weekly = ('ok', f"Semana de {ddmm(last_week)} entregue em {report.created_at.astimezone(TZ):%d/%m}.") if report else (
        'pending', f'Preparar e entregar o relatório da semana de {ddmm(last_week)} a {ddmm(last_week + timedelta(days=6))}.')
    open_alerts = expense_alerts(db, current_day - timedelta(days=29), current_day)['open_count']
    expenses = ('attention', f'{open_alerts} alerta(s) sem explicação nos últimos 30 dias.') if open_alerts else ('ok', 'Nenhum alerta pendente nos últimos 30 dias.')
    rows = [('calendar', 'school', 'Calendário da escola', calendar), ('purchases', 'purchases', 'Compras, notas e estoque', purchases),
            ('cash', 'cash', 'Caixa: aberturas e fechamentos', cash), ('weekly', 'weekly', 'Relatório semanal', weekly), ('expenses', 'expenses', 'Gastos fora do padrão', expenses)]
    return [{'id': key, 'page': page, 'title': title, 'status': status, 'detail': detail} for key, page, title, (status, detail) in rows]
