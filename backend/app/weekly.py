"""Relatório semanal da gestão e situação das rotinas de acompanhamento.

O relatório reúne, para uma semana de segunda a domingo: vendas comparadas à semana
anterior, conferência diária do caixa, compras e notas, inventário, gastos fora do padrão
e o calendário da escola. Ele é gerado a partir dos registros e pode ser impresso,
copiado para o WhatsApp e guardado como versão entregue.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .cash_review import cash_days
from .database import get_session
from .domain import TZ, audit, brl, get_or_404, lock, now, rows
from .expense_alerts import expense_alerts
from .models import AppSettings, InventoryCount, Sale, SalePayment, StockItem, StockLot, WeeklyReport
from .purchases import pending_orders, receipt_checks
from .reports import period_report
from .school import SHIFTS, WEEKDAYS, calendar_days, calendar_summary, last_check, today
from .team import Input

router = APIRouter(prefix='/api', tags=['Relatório semanal'])
DB = Annotated[Session, Depends(get_session)]
METHODS = {'cash': 'Dinheiro', 'pix': 'Pix', 'debit': 'Débito', 'credit': 'Crédito'}
STATUS_LABELS = {'open': 'Funcionamento normal', 'closed': 'Fechada', 'reduced': 'Movimento reduzido', 'increased': 'Movimento maior'}
INVENTORY_INTERVAL_DAYS = 7


class SaveIn(Input):
    week: date
    note: str = Field(min_length=3, max_length=1000)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def instant(day):
    return datetime.combine(day, time(0), TZ)


def ddmm(day):
    return day.strftime('%d/%m')


def full(day):
    return day.strftime('%d/%m/%Y')


def pct(current, previous):
    if not previous:
        return None
    return round((current - previous) * 100 / previous, 1)


def pct_text(value):
    return '—' if value is None else f"{value:+.1f}%".replace('.', ',')


def quantity(value):
    text = format(Decimal(str(value)).normalize(), 'f')
    return text.replace('.', ',')


def age_text(days):
    return 'hoje' if days == 0 else 'ontem' if days == 1 else f'há {days} dias'


def sentence(value):
    text = str(value).strip()
    return text if text.endswith(('.', '!', '?')) else text + '.'


def cell(value):
    return str(value).replace('|', '/').replace('\n', ' ')


def weekly_report(db, any_day):
    monday = monday_of(any_day); sunday = monday + timedelta(days=6); current_day = today()
    if monday > current_day:
        raise HTTPException(422, 'A semana escolhida ainda não começou.')
    start, end = instant(monday), instant(sunday + timedelta(days=1))
    current = period_report(db, start, end)
    previous = period_report(db, start - timedelta(days=7), start)
    methods = dict(db.execute(select(SalePayment.method, func.sum(SalePayment.amount_cents)).join(Sale, SalePayment.sale_id == Sale.id)
                              .where(Sale.occurred_at >= start, Sale.occurred_at < end, Sale.voided.is_(False)).group_by(SalePayment.method)).all())
    cash = cash_days(db, monday, min(sunday, current_day))
    cash = [d for d in cash if not (d['state'] == 'not_applicable' and d['day'].weekday() >= 5)]
    receipts = receipt_checks(db, start, end)
    alerts = expense_alerts(db, monday, sunday)
    items = {i.id: i for i in db.scalars(select(StockItem))}
    counts = db.scalars(select(InventoryCount).where(InventoryCount.counted_at >= start, InventoryCount.counted_at < end).order_by(InventoryCount.counted_at)).all()
    low = [i for i in items.values() if i.active and (i.balance < i.minimum or i.balance == 0)]
    low.sort(key=lambda i: (i.balance > 0, i.name))
    expired = db.scalar(select(func.count()).select_from(StockLot).where(StockLot.balance > 0, StockLot.expiry < current_day))
    expiring = db.execute(select(StockLot, StockItem).join(StockItem, StockLot.item_id == StockItem.id)
                          .where(StockLot.balance > 0, StockLot.expiry >= current_day, StockLot.expiry <= current_day + timedelta(days=7)).order_by(StockLot.expiry)).all()
    week_days = [d for d in calendar_days(db, monday, sunday) if d['day'].weekday() < 5]
    next_monday = sunday + timedelta(days=1)
    upcoming = calendar_summary(db, next_monday, 14)
    sales = {'current': current['sales_cents'], 'previous': previous['sales_cents'], 'variation_pct': pct(current['sales_cents'], previous['sales_cents'])}
    pending_cash = [d for d in cash if d['state'] in {'pending', 'outdated'}]
    open_alerts = [a for a in alerts['alerts'] if a['explanation'] is None and a['severity'] != 'info']
    divergent = [r for r in receipts if r['status'] == 'divergent']
    missing_invoice = [r for r in receipts if r['status'] == 'missing_invoice']
    orders = pending_orders(db)
    check = last_check(db)
    actions = []
    if pending_cash:
        actions.append(f'Conferir o caixa de {len(pending_cash)} dia(s): ' + ', '.join(ddmm(d['day']) for d in pending_cash) + '.')
    if open_alerts:
        actions.append(f'Explicar {len(open_alerts)} gasto(s) fora do padrão.')
    if divergent:
        actions.append(f'Verificar {len(divergent)} nota(s) com divergência de valor ou custo.')
    if missing_invoice:
        actions.append(f'Informar o valor total de {len(missing_invoice)} nota(s) recebida(s) para conferência.')
    if orders:
        actions.append(f'Acompanhar {len(orders)} pedido(s) de compra aguardando aprovação ou entrega.')
    if low:
        actions.append(f'Repor ou confirmar {len(low)} item(ns) sem saldo ou abaixo do mínimo.')
    if expired:
        actions.append(f'Dar destino a {expired} lote(s) vencido(s) com saldo.')
    if not counts:
        actions.append('Fazer contagem física do estoque (nenhuma contagem registrada na semana).')
    if check is None or check['overdue']:
        actions.append('Averiguar o calendário da escola (cursos, feriados e paralisações).')
    for note in current['completeness_notes']:
        actions.append(note)
    settings = db.get(AppSettings, 1)
    report = {'week_start': monday, 'week_end': sunday, 'label': f'{ddmm(monday)} a {full(sunday)}', 'complete_week': sunday < current_day, 'generated_at': now(),
              'business_name': settings.business_name if settings else 'Cantina em Dia', 'location': settings.location if settings else '',
              'current': current, 'previous': previous, 'sales': sales,
              'payment_mix': {key: methods.get(key, 0) for key in METHODS},
              'cash_days': cash, 'cash_pending_days': len(pending_cash), 'cash_reviewed_days': sum(1 for d in cash if d['state'] == 'reviewed'),
              'receipts': receipts, 'pending_orders': orders,
              'inventory_counts': [{'item': items[c.item_id].name, 'unit': items[c.item_id].unit, 'counted_at': c.counted_at, 'expected': c.expected, 'counted': c.counted, 'difference': c.difference, 'reason': c.reason} for c in counts],
              'low_stock': [{'name': i.name, 'unit': i.unit, 'balance': i.balance, 'minimum': i.minimum} for i in low],
              'expired_lots': expired, 'expiring_lots': [{'item': item.name, 'code': lot.code, 'expiry': lot.expiry, 'balance': lot.balance, 'unit': item.unit} for lot, item in expiring],
              'expense_alerts': alerts, 'open_alerts': len(open_alerts),
              'calendar': {'week_days': week_days, 'upcoming': upcoming, 'last_check': check},
              'actions': actions}
    report['markdown'] = render_markdown(report)
    report['text'] = render_text(report)
    return report


def render_markdown(r):
    c, p = r['current'], r['previous']
    ticket = lambda data: brl(data['sales_cents'] // data['sales_count']) if data['sales_count'] else '—'
    lines = [f"# Relatório semanal · {r['label']}", '',
             f"{cell(r['business_name'])}{' · ' + cell(r['location']) if r['location'] else ''} · gerado em {r['generated_at'].astimezone(TZ).strftime('%d/%m/%Y %H:%M')}"
             + ('' if r['complete_week'] else ' · **semana em andamento**'), '',
             '## Resumo da semana', '', '| Indicador | Semana | Semana anterior | Variação |', '|---|---:|---:|---:|']
    for label, key in [('Vendas após descontos e cancelamentos', 'sales_cents'), ('Recebimentos líquidos', 'receipts_net_cents'), ('Despesas lançadas (inclui mercadorias)', 'all_expenses_cents'),
                       ('Perdas, consumo da equipe e ajustes', 'losses_and_staff_cents'), ('Diferenças de caixa', 'cash_difference_cents')]:
        lines.append(f"| {label} | {brl(c[key])} | {brl(p[key])} | {pct_text(pct(c[key], p[key]))} |")
    lines.append(f"| Pedidos registrados | {c['sales_count']} | {p['sales_count']} | {pct_text(pct(c['sales_count'], p['sales_count']))} |")
    lines.append(f"| Ticket médio | {ticket(c)} | {ticket(p)} | — |")
    lines.append(f"| Resultado gerencial registrado | {brl(c['recorded_result_cents'])} | {brl(p['recorded_result_cents'])} | — |")
    lines += ['', 'Formas de pagamento: ' + ' · '.join(f"{label} {brl(r['payment_mix'][key])}" for key, label in METHODS.items()) + '.', '']
    lines += ['## Caixa: aberturas, fechamentos e conferência diária', '']
    if r['cash_days']:
        lines += ['| Dia | Calendário | Vendas em dinheiro | Retiradas | Diferença | Conferência |', '|---|---|---:|---:|---:|---|']
        for d in r['cash_days']:
            review = d['review']
            status = d['state_label'] + (f" ({'sem ressalvas' if review['status'] == 'ok' else 'com ressalvas'})" if review and d['state'] == 'reviewed' else '')
            lines.append(f"| {WEEKDAYS[d['day'].weekday()][:3]} {ddmm(d['day'])} | {STATUS_LABELS[d['calendar_status']]} | {brl(d['cash_sales_cents'])} | {brl(d['withdrawals_cents'])} | {brl(d['closing_difference_cents'])} | {status} |")
        issues = [f"{ddmm(d['day'])}: {issue}" for d in r['cash_days'] for issue in d['issues']]
        lines += [''] + ([f'- {cell(i)}' for i in issues] if issues else ['Nenhum ponto de atenção nas aberturas e fechamentos registrados.'])
    else:
        lines.append('Nenhum dia a conferir nesta semana.')
    lines += ['', '## Compras, notas e estoque', '']
    total = sum(x['items_total_cents'] for x in r['receipts'])
    lines.append(f"- Recebimentos: {len(r['receipts'])} nota(s), {brl(total)} em mercadorias.")
    for receipt in r['receipts']:
        if receipt['issues']:
            lines.append(f"- Nota {cell(receipt['document'])} ({cell(receipt['supplier'])}): " + ' '.join(sentence(cell(i)) for i in receipt['issues']))
        elif receipt['status'] == 'missing_invoice':
            lines.append(f"- Nota {cell(receipt['document'])} ({cell(receipt['supplier'])}): valor total da nota não informado.")
    for order in r['pending_orders']:
        missing = '; '.join(f"{cell(m['name'])} {quantity(m['missing'])} {m['unit']}" for m in order['missing'])
        lines.append(f"- Pedido #{order['id']} ({cell(order['supplier'])}): {'aguardando aprovação' if order['status'] == 'requested' else 'falta receber ' + missing}.")
    counted = r['inventory_counts']
    differences = [x for x in counted if x['difference']]
    lines.append(f"- Contagem física: {len(counted)} item(ns) contado(s), {len(differences)} com diferença." if counted else '- Contagem física: nenhuma registrada na semana.')
    for x in differences:
        lines.append(f"  - {cell(x['item'])}: esperado {quantity(x['expected'])}, contado {quantity(x['counted'])} {x['unit']} (diferença {quantity(x['difference'])}). {cell(x['reason'])}")
    if r['low_stock']:
        names = ', '.join(f"{cell(i['name'])} ({quantity(i['balance'])} {i['unit']})" for i in r['low_stock'][:15])
        lines.append(f"- Sem saldo ou abaixo do mínimo: {names}{' e outros' if len(r['low_stock']) > 15 else ''}.")
    if r['expired_lots']:
        lines.append(f"- {r['expired_lots']} lote(s) vencido(s) ainda com saldo.")
    for lot in r['expiring_lots']:
        lines.append(f"- Vence em {ddmm(lot['expiry'])}: {cell(lot['item'])}, lote {cell(lot['code'])}, {quantity(lot['balance'])} {lot['unit']}.")
    lines += ['', '## Gastos fora do padrão', '']
    found = r['expense_alerts']['alerts']
    if found:
        for a in found:
            explanation = f" Explicação: {cell(a['explanation']['note'])}" if a['explanation'] else (' **Sem explicação registrada.**' if a['severity'] != 'info' else '')
            lines.append(f"- [{a['kind_label']}] {sentence(cell(a['title']))} {cell(a['detail'])}{explanation}")
    else:
        lines.append('Nenhum gasto fora do padrão identificado nos registros da semana.')
    if r['expense_alerts']['insufficient_history']:
        lines.append(f"\nCategorias ainda sem histórico suficiente para comparação: {', '.join(cell(x) for x in r['expense_alerts']['insufficient_history'])}.")
    cal = r['calendar']; check = cal['last_check']; upcoming = cal['upcoming']
    lines += ['', '## Calendário da escola', '',
              f"- Última averiguação: {full(check['checked_at'].astimezone(TZ).date())} ({cell(check['source'])})." if check else '- Calendário ainda não averiguado com a escola.']
    altered = [d for d in cal['week_days'] if d['status'] != 'open']
    lines.append('- Nesta semana: ' + ('; '.join(f"{ddmm(d['day'])} {STATUS_LABELS[d['status']].lower()} ({cell(', '.join(d['reasons']))})" for d in altered) if altered else 'funcionamento normal previsto em todos os dias úteis.'))
    lines.append('- Próximas duas semanas: ' + ('; '.join(f"{cell(e['title'])} ({ddmm(e['starts_on'])}{'–' + ddmm(e['ends_on']) if e['ends_on'] != e['starts_on'] else ''}, {e['effect_label'].lower()})" for e in upcoming['events']) if upcoming['events'] else 'nenhum feriado, recesso ou paralisação registrado.'))
    active = upcoming['active_courses']
    if active:
        by_shift = '; '.join(f"{label}: {', '.join(cell(x['name']) for x in active if x['shift'] == key)}" for key, label in SHIFTS.items() if any(x['shift'] == key for x in active))
        students = [x['students'] for x in active if x['students'] is not None]
        lines.append(f"- Cursos em andamento: {len(active)}{f' (cerca de {sum(students)} alunos informados)' if students else ''}. {by_shift}.")
    else:
        lines.append('- Nenhum curso em andamento cadastrado.')
    for x in upcoming['ending_soon']:
        lines.append(f"- Termina em {ddmm(x['ends_on'])}: {cell(x['name'])} ({x['shift_label'].lower()}).")
    for x in upcoming['starting_soon']:
        lines.append(f"- Começa em {ddmm(x['starts_on'])}: {cell(x['name'])} ({x['shift_label'].lower()}).")
    lines += ['', '## Pendências e próximos passos', '']
    lines += [f'- [ ] {cell(a)}' for a in r['actions']] or ['Nenhuma pendência identificada nos registros.']
    lines += ['', '---', '', 'Valores conforme os registros lançados no sistema. Diferenças e alertas indicam pontos de conferência, não prova de erro ou desvio.']
    return '\n'.join(lines)


def render_text(r):
    c = r['current']; mix = r['payment_mix']
    lines = [f"*Relatório semanal · {r['business_name']}*", f"Semana de {r['label']}{'' if r['complete_week'] else ' (em andamento)'}", '',
             f"*Vendas:* {brl(c['sales_cents'])} em {c['sales_count']} pedido(s) · {pct_text(r['sales']['variation_pct'])} vs. semana anterior",
             f"Dinheiro {brl(mix['cash'])} · Pix {brl(mix['pix'])} · Cartão {brl(mix['debit'] + mix['credit'])}",
             f"*Despesas lançadas:* {brl(c['all_expenses_cents'])}",
             f"*Caixa:* {r['cash_reviewed_days']} dia(s) conferido(s), {r['cash_pending_days']} pendente(s) · diferenças {brl(c['cash_difference_cents'])}",
             f"*Compras:* {len(r['receipts'])} nota(s), {sum(1 for x in r['receipts'] if x['status'] == 'divergent')} com divergência · {len(r['pending_orders'])} pedido(s) em aberto",
             f"*Estoque:* {len(r['inventory_counts'])} item(ns) contado(s) · {len(r['low_stock'])} abaixo do mínimo",
             f"*Gastos fora do padrão:* {len(r['expense_alerts']['alerts'])} alerta(s), {r['open_alerts']} sem explicação"]
    events = r['calendar']['upcoming']['events']
    if events:
        lines.append('*Calendário:* ' + '; '.join(f"{e['title']} {ddmm(e['starts_on'])} ({e['effect_label'].lower()})" for e in events[:4]))
    if r['actions']:
        lines += ['', '*Pendências:*'] + [f'• {a}' for a in r['actions'][:8]]
    return '\n'.join(lines)


@router.get('/reports/weekly')
def weekly(db: DB, week: date | None = None):
    return weekly_report(db, week or today())


@router.get('/reports/weekly.md')
def weekly_markdown(db: DB, week: date | None = None):
    report = weekly_report(db, week or today())
    return Response(report['markdown'], media_type='text/markdown; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="relatorio-semanal-{report["week_start"]}.md"'})


@router.get('/weekly-reports')
def saved(db: DB):
    return [{'id': r.id, 'week_start': r.week_start, 'version': r.version, 'note': r.note, 'created_at': r.created_at,
             'complete_week': r.snapshot.get('complete_week'), 'sales_cents': r.snapshot.get('current', {}).get('sales_cents'), 'actions': len(r.snapshot.get('actions', []))} for r in rows(db, WeeklyReport, 200)]


@router.get('/weekly-reports/{key}')
def saved_detail(key: int, db: DB):
    row = get_or_404(db, WeeklyReport, key)
    return {'id': row.id, 'week_start': row.week_start, 'version': row.version, 'note': row.note, 'created_at': row.created_at, 'markdown': row.snapshot.get('markdown', ''), 'text': row.snapshot.get('text', '')}


@router.post('/weekly-reports', status_code=201)
def save_report(data: SaveIn, db: DB):
    lock(db, 1201)
    report = weekly_report(db, data.week)
    version = (db.scalar(select(func.max(WeeklyReport.version)).where(WeeklyReport.week_start == report['week_start'])) or 0) + 1
    row = WeeklyReport(week_start=report['week_start'], version=version, note=data.note, snapshot=jsonable_encoder(report))
    db.add(row); db.flush(); audit(db, 'weekly_report', row.id, 'saved', {'week_start': report['week_start'], 'version': version, 'note': data.note}); db.commit(); db.refresh(row)
    return {'id': row.id, 'week_start': row.week_start, 'version': row.version, 'created_at': row.created_at}


@router.get('/routine')
def routine(db: DB):
    """Situação das cinco rotinas de acompanhamento exigidas pela gestão."""
    current_day = today(); result = []
    check = last_check(db)
    window = calendar_summary(db, current_day, 14)
    events = len(window['events'])
    if check is None:
        result.append({'id': 'calendar', 'page': 'school', 'title': 'Calendário da escola', 'status': 'pending', 'detail': 'Ainda não averiguado. Confirme cursos em andamento, feriados e paralisações com a escola.'})
    else:
        result.append({'id': 'calendar', 'page': 'school', 'title': 'Calendário da escola', 'status': 'attention' if check['overdue'] else 'ok',
                       'detail': f"Averiguado {age_text(check['age_days'])}. {len(window['active_courses'])} curso(s) em andamento; {events} evento(s) nos próximos 14 dias."})
    last_count = db.scalar(select(func.max(InventoryCount.counted_at)))
    week_ago = instant(current_day - timedelta(days=7))
    receipts = receipt_checks(db, week_ago, instant(current_day + timedelta(days=1)))
    divergent = sum(1 for r in receipts if r['status'] != 'ok')
    orders = len(pending_orders(db))
    count_age = (current_day - last_count.astimezone(TZ).date()).days if last_count else None
    parts = [f'{orders} pedido(s) em aberto', f'{divergent} nota(s) a verificar nos últimos 7 dias',
             f'última contagem física há {count_age} dia(s)' if last_count else 'nenhuma contagem física registrada']
    status = 'pending' if last_count is None else 'attention' if divergent or count_age > INVENTORY_INTERVAL_DAYS else 'ok'
    result.append({'id': 'purchases', 'page': 'purchases', 'title': 'Compras, notas e inventário', 'status': status, 'detail': ('; '.join(parts) + '.')[:1].upper() + ('; '.join(parts) + '.')[1:]})
    days = cash_days(db, current_day - timedelta(days=7), current_day - timedelta(days=1))
    pending = [d for d in days if d['state'] in {'pending', 'outdated'}]
    result.append({'id': 'cash', 'page': 'cash', 'title': 'Caixa: aberturas e fechamentos', 'status': 'attention' if pending else 'ok',
                   'detail': (f"{len(pending)} dia(s) aguardando conferência: " + ', '.join(ddmm(d['day']) for d in pending) + '.') if pending else 'Últimos 7 dias conferidos ou sem movimento previsto.'})
    last_week = monday_of(current_day) - timedelta(days=7)
    saved_report = db.scalar(select(WeeklyReport).where(WeeklyReport.week_start == last_week).order_by(WeeklyReport.version.desc()).limit(1))
    result.append({'id': 'weekly', 'page': 'weekly', 'title': 'Relatório semanal', 'status': 'ok' if saved_report else 'pending',
                   'detail': f"Semana de {ddmm(last_week)} entregue em {saved_report.created_at.astimezone(TZ).strftime('%d/%m')}." if saved_report else f"Preparar e registrar o relatório da semana de {ddmm(last_week)} a {ddmm(last_week + timedelta(days=6))}."})
    alerts = expense_alerts(db, current_day - timedelta(days=29), current_day)
    result.append({'id': 'expenses', 'page': 'finance', 'title': 'Gastos fora do padrão', 'status': 'attention' if alerts['open_count'] else 'ok',
                   'detail': f"{alerts['open_count']} alerta(s) sem explicação nos últimos 30 dias." if alerts['open_count'] else 'Nenhum alerta pendente nos últimos 30 dias.'})
    return result
