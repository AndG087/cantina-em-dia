from test_team import person
from test_inventory import movement


def cash(client, opening=1000):
    employee = person(client)
    response = client.post('/api/cash-sessions', json={'employee_id': employee, 'opened_at': '2026-11-02T08:00:00-03:00', 'opening_cents': opening, 'note': 'Troco acompanhado'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def product(client, balance=10):
    response = client.post('/api/items', json={'sku': 'LATA', 'name': 'Refrigerante', 'category': 'Bebidas', 'kind': 'product', 'unit': 'un', 'unit_cost_cents': 200, 'sale_price_cents': 400, 'price_locked': True})
    key = response.json()['id']
    movement(client, key, balance)
    return key


def sell(client, key, session, payments=None):
    return client.post('/api/sales', json={'occurred_at': '2026-11-02T09:00:00-03:00', 'cash_session_id': session, 'lines': [{'item_id': key, 'quantity': '1', 'unit_price_cents': 400}], 'payments': payments or [{'method': 'cash', 'amount_cents': 400}]})


def test_split_sale_and_digital_receipt_no_double_sale(client):
    key = product(client); session = cash(client)
    response = sell(client, key, session, [{'method': 'cash', 'amount_cents': 200}, {'method': 'pix', 'amount_cents': 200}])
    assert response.status_code == 201, response.text
    assert client.get('/api/cash-sessions').json()[0]['expected_cents'] == 1200
    assert float(client.get('/api/items').json()[0]['balance']) == 9
    payment = next(p for p in client.get('/api/sale-payments').json() if p['method'] == 'pix')
    settlement = {'payment_id': payment['id'], 'gross_cents': 200, 'fee_cents': 5, 'occurred_at': '2026-11-03T10:00:00-03:00', 'reference': 'EXTRATO-1'}
    assert client.post('/api/settlements', json=settlement).status_code == 201
    assert client.post('/api/settlements', json=settlement).status_code == 409
    assert len(client.get('/api/sales').json()) == 1
    assert next(p for p in client.get('/api/sale-payments').json() if p['id'] == payment['id'])['pending_cents'] == 0


def test_handover_count_difference_not_counted_twice(client):
    key = product(client); session = cash(client); sell(client, key, session)
    other = person(client, 'Segundo operador')
    response = client.post(f'/api/cash-sessions/{session}/handover', json={'employee_id': other, 'occurred_at': '2026-11-02T10:00:00-03:00', 'counted_cents': 1350, 'reason': 'Diferença a conferir'})
    assert response.status_code == 201, response.text
    assert response.json()['difference_cents'] == -50
    assert client.get('/api/cash-sessions').json()[0]['expected_cents'] == 1350
    closed = client.post(f'/api/cash-sessions/{session}/close', json={'occurred_at': '2026-11-02T11:00:00-03:00', 'counted_cents': 1350, 'reason': 'Contagem final acompanhada'})
    assert closed.status_code == 200 and closed.json()['difference_cents'] == 0
    assert sell(client, key, session).status_code == 409


def test_invalid_sale_rolls_back_everything(client):
    key = product(client); session = cash(client)
    assert sell(client, key, session, [{'method': 'cash', 'amount_cents': 399}]).status_code == 422
    assert client.get('/api/sales').json() == []
    assert float(client.get('/api/items').json()[0]['balance']) == 10


def test_cash_expense_is_linked_and_not_double_counted(client):
    session = cash(client)
    expense = client.post('/api/expenses', json={'description': 'Conta de teste', 'category': 'Manutenção', 'amount_cents': 150, 'occurred_at': '2026-11-02T09:00:00-03:00', 'paid_by': 'unpaid', 'payee': 'Fornecedor', 'document': 'DOC-1'}).json()['id']
    payment = client.post(f'/api/expenses/{expense}/payments', json={'amount_cents': 150, 'method': 'cash', 'source': 'cantina', 'cash_session_id': session, 'occurred_at': '2026-11-02T10:00:00-03:00', 'reference': 'DINHEIRO-1'})
    assert payment.status_code == 201, payment.text
    assert client.get('/api/cash-sessions').json()[0]['expected_cents'] == 850
    assert len(client.get('/api/expenses').json()) == 1
    assert client.get('/api/expenses').json()[0]['pending_cents'] == 0


def test_cancel_sale_and_record_actual_cash_refund(client):
    key = product(client); session = cash(client, 0); sale = sell(client, key, session).json()['id']
    cancelled = client.post(f'/api/sales/{sale}/cancel', json={'reason': 'Cliente devolveu produto', 'stock_returned': True, 'occurred_at': '2026-11-02T10:00:00-03:00'})
    assert cancelled.status_code == 200, cancelled.text
    assert float(client.get('/api/items').json()[0]['balance']) == 10
    payment = client.get('/api/sale-payments').json()[0]
    assert payment['refund_pending_cents'] == 400
    response = client.post('/api/sale-refunds', json={'payment_id': payment['id'], 'amount_cents': 400, 'cash_session_id': session, 'occurred_at': '2026-11-02T10:30:00-03:00', 'reference': 'DEV-1'})
    assert response.status_code == 201, response.text
    assert client.get('/api/cash-sessions').json()[0]['expected_cents'] == 0


def test_cash_control_protects_open_and_transfer(client):
    session = cash(client)
    employee = person(client, 'Outro gerente')
    assert client.post('/api/cash-sessions', json={'employee_id': employee, 'opened_at': '2026-11-02T09:00:00-03:00', 'opening_cents': 0, 'note': 'Outra abertura'}).status_code == 409
    assert client.post('/api/assignments', json={'employee_id': employee, 'started_at': '2026-11-02T10:00:00-03:00', 'reason': 'Troca sem contagem'}).status_code == 409
    assert client.post(f'/api/cash-sessions/{session}/entries', json={'kind': 'withdrawal', 'amount_cents': 2000, 'occurred_at': '2026-11-02T10:00:00-03:00', 'note': 'Retirada maior que saldo'}).status_code == 409
    assert client.get('/api/cash-sessions').json()[0]['expected_cents'] == 1000
