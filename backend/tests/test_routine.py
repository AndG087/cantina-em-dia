"""Rotinas de acompanhamento: calendário escolar, notas, inventário, caixa diário, gastos e relatório semanal."""
from test_team import person
from test_inventory import item, movement
from test_purchases import order


def event(client, **extra):
    data = {'kind': 'holiday', 'title': 'Feriado municipal', 'starts_on': '2026-11-05', 'ends_on': '2026-11-05', 'effect': 'closed', 'source': 'Secretaria do Senai', **extra}
    return client.post('/api/school/events', json=data)


def expense(client, amount, day, payee='Distribuidora de gás', document=None, category='Gás'):
    response = client.post('/api/expenses', json={'description': f'{category} {day}', 'category': category, 'amount_cents': amount, 'occurred_at': f'{day}T10:00:00-03:00',
                                                   'paid_by': 'unpaid', 'payee': payee, 'document': document or f'DOC-{day}-{amount}'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_school_calendar_courses_events_and_closed_days(client):
    course = {'name': 'Técnico em Eletrotécnica', 'shift': 'evening', 'starts_on': '2026-08-01', 'ends_on': '2026-11-20', 'students': 30, 'source': 'Quadro de turmas da secretaria'}
    assert client.post('/api/school/courses', json={**course, 'ends_on': '2026-07-01'}).status_code == 422
    created = client.post('/api/school/courses', json=course)
    assert created.status_code == 201 and created.json()['weekdays'] == [0, 1, 2, 3, 4]
    assert client.post('/api/school/courses', json={**course, 'name': 'Aprendizagem industrial', 'shift': 'morning', 'students': None, 'weekdays': [0, 2]}).status_code == 201
    assert event(client).status_code == 201
    assert event(client).status_code == 409
    strike = event(client, kind='strike', title='Paralisação dos docentes', starts_on='2026-11-09', ends_on='2026-11-10', effect='reduced').json()
    calendar = client.get('/api/school/calendar', params={'start': '2026-11-02', 'days': 9}).json()
    days = {d['day']: d for d in calendar['days']}
    assert days['2026-11-02']['status'] == 'open' and days['2026-11-02']['courses_count'] == 2
    assert days['2026-11-02']['students_estimate'] == 30 and days['2026-11-02']['students_complete'] is False
    assert days['2026-11-03']['courses_by_shift']['morning'] == [] and days['2026-11-03']['courses_count'] == 1
    assert days['2026-11-05']['status'] == 'closed' and days['2026-11-07']['status'] == 'closed'
    assert days['2026-11-09']['status'] == 'reduced'
    assert {e['title'] for e in calendar['events']} == {'Feriado municipal', 'Paralisação dos docentes'}
    assert client.get('/api/cash-responsibility', params={'at': '2026-11-05T10:00:00-03:00'}).json()['closed'] is True
    assert client.post(f"/api/school/events/{strike['id']}/cancel", json={'reason': 'Paralisação suspensa'}).status_code == 200
    assert client.get('/api/school/calendar', params={'start': '2026-11-09', 'days': 1}).json()['days'][0]['status'] == 'open'
    assert client.get('/api/school/calendar').json()['last_check'] is None
    assert client.post('/api/school/checks', json={'source': 'Conversa com a coordenação', 'note': 'Sem novas turmas'}).status_code == 201
    check = client.get('/api/school/calendar').json()['last_check']
    assert check['age_days'] == 0 and check['overdue'] is False


def test_invoice_check_and_cost_above_estimate(client):
    key = item(client); purchase = order(client, key)
    receipt = {'document': 'NF-10', 'occurred_at': '2026-11-02T12:00:00-03:00', 'paid_by': 'unpaid', 'lines': [{'item_id': key, 'quantity': '4', 'unit_cost_cents': 600}], 'invoice_total_cents': 2500}
    refused = client.post(f'/api/purchases/{purchase}/receive', json=receipt)
    assert refused.status_code == 422 and 'R$ 25,00' in refused.json()['detail'] and 'R$ 24,00' in refused.json()['detail']
    assert client.get('/api/expenses').json() == []
    assert client.post(f'/api/purchases/{purchase}/receive', json={**receipt, 'invoice_note': 'Frete de R$ 1,00 cobrado na nota'}).status_code == 201
    exact = {**receipt, 'document': 'NF-11', 'invoice_total_cents': 2000, 'lines': [{'item_id': key, 'quantity': '4', 'unit_cost_cents': 500}]}
    assert client.post(f'/api/purchases/{purchase}/receive', json=exact).status_code == 201
    checks = client.get('/api/purchase-receipts').json()
    by_document = {r['document']: r for r in checks['receipts']}
    divergent = by_document['NF-10']
    assert divergent['status'] == 'divergent' and divergent['invoice_difference_cents'] == 100
    assert any('20% acima do estimado' in issue for issue in divergent['issues'])
    assert by_document['NF-11']['status'] == 'ok' and by_document['NF-11']['lines'][0]['cost_variation_pct'] == 0
    assert float(checks['pending_orders'][0]['missing'][0]['missing']) == 2


def test_inventory_sheet_batch_is_atomic(client):
    first = item(client); second = item(client, 'FEIJAO')
    movement(client, first, 10); movement(client, second, 5)
    sheet = client.get('/api/inventory-sheet', params={'at': '2026-11-02T18:00:00-03:00'}).json()
    expected = {i['id']: i['expected'] for i in sheet['items']}
    assert float(expected[first]) == 10 and float(expected[second]) == 5
    batch = {'counted_at': '2026-11-02T18:00:00-03:00', 'reason': 'Inventário semanal acompanhado', 'lines': [{'item_id': first, 'expected': '10', 'counted': '9'}, {'item_id': second, 'expected': '4', 'counted': '5'}]}
    assert client.post('/api/inventory-counts/batch', json=batch).status_code == 409
    assert client.get('/api/inventory-counts').json() == []
    batch['lines'][1]['expected'] = '5'
    response = client.post('/api/inventory-counts/batch', json=batch)
    assert response.status_code == 201 and response.json()['counted'] == 2 and response.json()['with_difference'] == 1
    balances = {i['id']: float(i['balance']) for i in client.get('/api/items').json()}
    assert balances[first] == 9 and balances[second] == 5


def test_daily_cash_review_points_out_gaps(client):
    employee = person(client)
    first = client.post('/api/cash-sessions', json={'employee_id': employee, 'opened_at': '2026-11-02T08:00:00-03:00', 'opening_cents': 1000, 'note': 'Troco contado'}).json()['id']
    assert client.post(f'/api/cash-sessions/{first}/close', json={'occurred_at': '2026-11-02T18:00:00-03:00', 'counted_cents': 900, 'reason': 'Fechamento noturno'}).status_code == 200
    second = client.post('/api/cash-sessions', json={'employee_id': employee, 'opened_at': '2026-11-03T08:00:00-03:00', 'opening_cents': 1000, 'note': 'Troco contado'}).json()['id']
    assert client.post(f'/api/cash-sessions/{second}/close', json={'occurred_at': '2026-11-03T18:00:00-03:00', 'counted_cents': 1000, 'reason': 'Fechamento noturno'}).status_code == 200
    assert event(client).status_code == 201
    days = {d['day']: d for d in client.get('/api/cash-reviews/days', params={'end': '2026-11-05', 'days': 4}).json()}
    assert days['2026-11-05']['state'] == 'not_applicable' and days['2026-11-05']['issues'] == []
    assert any('sem abertura' in issue for issue in days['2026-11-04']['issues'])
    assert any('troco de abertura R$ 10,00' in issue for issue in days['2026-11-03']['issues'])
    assert any('-R$ 1,00' in issue for issue in days['2026-11-02']['issues'])
    assert days['2026-11-03']['state'] == 'pending'
    review = {'day': '2026-11-03', 'status': 'ok', 'note': 'Conferido com a Dona Gel'}
    assert client.post('/api/cash-reviews', json=review).status_code == 409
    assert client.post('/api/cash-reviews', json={**review, 'status': 'issues', 'note': 'R$ 1,00 levado ao cofre sem registro; orientado'}).status_code == 201
    assert client.post('/api/cash-reviews', json={**review, 'day': '2099-01-01'}).status_code == 422
    day = client.get('/api/cash-reviews/days', params={'end': '2026-11-03', 'days': 1}).json()[0]
    assert day['state'] == 'reviewed' and day['review']['status'] == 'issues'
    assert client.post(f'/api/cash-sessions/{second}/reopen', json={'reason': 'Correção da contagem', 'occurred_at': '2026-11-04T09:00:00-03:00'}).status_code == 200
    assert client.get('/api/cash-reviews/days', params={'end': '2026-11-03', 'days': 1}).json()[0]['state'] == 'outdated'


def test_expense_alerts_and_explanations(client):
    for day in ['2026-10-01', '2026-10-08', '2026-10-15']:
        expense(client, 10000, day)
    high = expense(client, 25000, '2026-11-03')
    expense(client, 4000, '2026-11-04', payee='Mercado do bairro', document='CUPOM-1', category='Limpeza')
    expense(client, 4000, '2026-11-05', payee='Mercado do bairro', document='CUPOM-2', category='Limpeza')
    key = item(client)
    first = order(client, key)
    assert client.post(f'/api/purchases/{first}/receive', json={'document': 'NF-A', 'occurred_at': '2026-10-20T12:00:00-03:00', 'paid_by': 'unpaid', 'lines': [{'item_id': key, 'quantity': '5', 'unit_cost_cents': 500}]}).status_code == 201
    assert client.post(f'/api/purchases/{first}/receive', json={'document': 'NF-B', 'occurred_at': '2026-11-03T12:00:00-03:00', 'paid_by': 'unpaid', 'lines': [{'item_id': key, 'quantity': '5', 'unit_cost_cents': 600}]}).status_code == 201
    result = client.get('/api/expense-alerts', params={'start': '2026-11-02', 'end': '2026-11-08'}).json()
    kinds = {a['kind'] for a in result['alerts']}
    assert {'above_usual', 'duplicate', 'unit_cost', 'category_increase'} <= kinds
    above = next(a for a in result['alerts'] if a['kind'] == 'above_usual')
    assert above['expense_id'] == high and above['severity'] == 'high' and above['reference_cents'] == 10000
    assert next(a for a in result['alerts'] if a['kind'] == 'unit_cost')['reference_cents'] == 500
    before = result['open_count']
    note = {'alert_key': above['key'], 'note': 'Botijão extra para o evento da escola'}
    assert client.post('/api/expense-alerts/notes', json=note).status_code == 201
    assert client.post('/api/expense-alerts/notes', json=note).status_code == 409
    assert client.post('/api/expense-alerts/notes', json={**note, 'alert_key': 'unknown:1'}).status_code == 422
    after = client.get('/api/expense-alerts', params={'start': '2026-11-02', 'end': '2026-11-08'}).json()
    assert after['open_count'] == before - 1
    assert next(a for a in after['alerts'] if a['key'] == above['key'])['explanation']['note'] == note['note']


def test_weekly_report_markdown_versions_and_routine(client):
    employee = person(client)
    session = client.post('/api/cash-sessions', json={'employee_id': employee, 'opened_at': '2026-11-02T08:00:00-03:00', 'opening_cents': 1000, 'note': 'Troco contado'}).json()['id']
    client.post(f'/api/cash-sessions/{session}/close', json={'occurred_at': '2026-11-02T18:00:00-03:00', 'counted_cents': 1000, 'reason': 'Fechamento'})
    expense(client, 5000, '2026-11-03')
    event(client, kind='recess', title='Recesso escolar', starts_on='2026-11-12', ends_on='2026-11-13', effect='reduced')
    report = client.get('/api/reports/weekly', params={'week': '2026-11-04'}).json()
    assert report['week_start'] == '2026-11-02' and report['week_end'] == '2026-11-08'
    assert report['markdown'].startswith('# Relatório semanal · 02/11 a 08/11/2026')
    assert '## Caixa: aberturas, fechamentos e conferência diária' in report['markdown'] and 'Recesso escolar' in report['markdown']
    assert '*Vendas:*' in report['text'] and report['cash_pending_days'] >= 1
    assert any('calendário da escola' in action for action in report['actions'])
    assert client.get('/api/reports/weekly', params={'week': '2099-01-05'}).status_code == 422
    download = client.get('/api/reports/weekly.md', params={'week': '2026-11-02'})
    assert download.status_code == 200 and 'relatorio-semanal-2026-11-02.md' in download.headers['content-disposition']
    first = client.post('/api/weekly-reports', json={'week': '2026-11-02', 'note': 'Enviado ao meu pai pelo WhatsApp'})
    second = client.post('/api/weekly-reports', json={'week': '2026-11-06', 'note': 'Reenviado com a conferência do caixa'})
    assert first.status_code == 201 and second.json()['version'] == 2
    saved = client.get(f"/api/weekly-reports/{first.json()['id']}").json()
    assert saved['markdown'].startswith('# Relatório semanal')
    routine = client.get('/api/routine').json()
    assert [r['id'] for r in routine] == ['calendar', 'purchases', 'cash', 'weekly', 'expenses']
    assert routine[0]['status'] == 'pending'


def test_monthly_report_keeps_goal_fields(client):
    report = client.get('/api/reports/monthly', params={'month': '2026-11'}).json()
    assert report['month'] == '2026-11' and report['goal'] is None and 'sales_cents' in report
