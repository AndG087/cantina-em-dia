from test_finance import product, cash, sell
from test_purchases import order


def test_report_receipts_and_sale_not_double_counted(client):
    key = product(client); session = cash(client)
    sell(client, key, session, [{'method': 'pix', 'amount_cents': 400}])
    payment = client.get('/api/sale-payments').json()[0]['id']
    client.post('/api/settlements', json={'payment_id': payment, 'gross_cents': 400, 'fee_cents': 10, 'occurred_at': '2026-11-03T12:00:00-03:00', 'reference': 'ST-REPORT'})
    report = client.get('/api/reports/monthly', params={'month': '2026-11'})
    assert report.status_code == 200, report.text
    data = report.json()
    assert data['sales_cents'] == 400 and data['receipts_net_cents'] == 390
    assert data['cogs_cents'] == 200 and data['operating_result_cents'] == 190
    assert data['goal'] is None


def test_goal_pending_versioning_and_snapshot(client):
    key = product(client); session = cash(client); sell(client, key, session)
    assert client.post('/api/goal-assessments', json={'month': '2026-11', 'note': 'Simulação sem meta'}).status_code == 409
    goal = {'month': '2026-11', 'basis': 'net_sales', 'target_cents': 300, 'agreement': 'Confirmado pelo responsável: 100% do excedente'}
    assert client.post('/api/goals', json=goal).status_code == 201
    result = client.get('/api/reports/monthly?month=2026-11').json()
    assert result['goal']['variable_cents'] == 100
    snapshot = client.post('/api/goal-assessments', json={'month': '2026-11', 'note': 'Simulação acompanhada'})
    assert snapshot.status_code == 201, snapshot.text
    client.post('/api/goals', json={**goal, 'target_cents': 500})
    assert client.get('/api/reports/monthly?month=2026-11').json()['goal']['variable_cents'] == 0
    assert client.get('/api/goal-assessments').json()[0]['variable_cents'] == 100


def test_inventory_purchase_not_deducted_again_in_result(client):
    key = product(client); purchase = order(client, key, 2)
    received = client.post(f'/api/purchases/{purchase}/receive', json={'document': 'NF-REPORT', 'occurred_at': '2026-11-02T07:00:00-03:00', 'paid_by': 'employee', 'payer_name': 'Dona Gel', 'lines': [{'item_id': key, 'quantity': '2', 'unit_cost_cents': 200}]})
    assert received.status_code == 201
    report = client.get('/api/reports/monthly?month=2026-11').json()
    assert report['purchase_expenses_cents'] == 400 and report['operating_expenses_cents'] == 0
    assert report['operating_result_cents'] == 0


def test_unreconciled_digital_blocks_profit_goal(client):
    key = product(client); sell(client, key, None, [{'method': 'credit', 'amount_cents': 400}])
    client.post('/api/goals', json={'month': '2026-11', 'basis': 'operating_result', 'target_cents': 0, 'agreement': 'Base de resultado a confirmar custos'})
    result = client.get('/api/reports/monthly?month=2026-11').json()
    assert result['operating_result_cents'] is None and result['goal']['variable_cents'] is None
    assert client.post('/api/goal-assessments', json={'month': '2026-11', 'note': 'Tentar sem taxas conhecidas'}).status_code == 409


def test_month_boundaries_use_local_timezone_and_validate_input(client):
    assert client.get('/api/reports/monthly?month=2026-13').status_code == 422
    assert client.get('/api/reports/monthly?month=2026-11').json()['sales_cents'] == 0
    assert client.get('/api/reports/monthly.csv?month=2026-11').status_code == 200
    assert client.get('/api/dashboard').status_code == 200
