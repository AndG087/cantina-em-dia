from test_inventory import item


def order(client, key, qty=10):
    supplier = client.post('/api/suppliers', json={'name': 'Atacado de teste'}).json()['id']
    purchase = client.post('/api/purchases', json={'supplier_id': supplier, 'requested_by': 'Dona Gel', 'lines': [{'item_id': key, 'quantity': str(qty), 'unit_cost_cents': 500}]}).json()['id']
    client.post(f'/api/purchases/{purchase}/approve')
    return purchase


def test_receipt_partial_stock_and_reimbursement_not_duplicate_expense(client):
    key = item(client); purchase = order(client, key)
    receipt = {'document': 'NF-1', 'occurred_at': '2026-11-02T12:00:00-03:00', 'paid_by': 'employee', 'payer_name': 'Dona Gel', 'lines': [{'item_id': key, 'quantity': '4', 'unit_cost_cents': 500}]}
    response = client.post(f'/api/purchases/{purchase}/receive', json=receipt)
    assert response.status_code == 201
    assert response.json()['status'] == 'partial'
    assert float(client.get('/api/items').json()[0]['balance']) == 4
    assert client.post(f'/api/purchases/{purchase}/receive', json=receipt).status_code == 409
    expense = response.json()['expense_id']
    payment = {'amount_cents': 1000, 'method': 'pix', 'source': 'owner', 'occurred_at': '2026-11-03T12:00:00-03:00', 'reference': 'PIX-1'}
    assert client.post(f'/api/expenses/{expense}/payments', json=payment).status_code == 201
    assert client.post(f'/api/expenses/{expense}/payments', json=payment).status_code == 409
    assert client.post(f'/api/expenses/{expense}/payments', json={**payment, 'reference': 'PIX-2', 'amount_cents': 1001}).status_code == 409
    expenses = client.get('/api/expenses').json()
    assert len(expenses) == 1 and expenses[0]['amount_cents'] == 2000 and expenses[0]['pending_cents'] == 1000


def test_over_receipt_rolls_back_stock_and_expense(client):
    key = item(client); purchase = order(client, key, 1)
    response = client.post(f'/api/purchases/{purchase}/receive', json={'document': 'NF-erro', 'occurred_at': '2026-11-02T12:00:00-03:00', 'paid_by': 'unpaid', 'lines': [{'item_id': key, 'quantity': '2', 'unit_cost_cents': 500}]})
    assert response.status_code == 409
    assert float(client.get('/api/items').json()[0]['balance']) == 0
    assert client.get('/api/expenses').json() == []
