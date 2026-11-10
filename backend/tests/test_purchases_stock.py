from conftest import at


def item(client, name='Refrigerante', unit='un'):
    response = client.post('/api/items', json={'name': name, 'category': 'Bebidas', 'unit': unit, 'minimum': '5'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def order(client, key, qty=10, cost=500):
    supplier = client.post('/api/suppliers', json={'name': f'Atacado {key}'}).json()['id']
    return client.post('/api/purchases', json={'supplier_id': supplier, 'requested_by': 'Dona Gel', 'lines': [{'item_id': key, 'quantity': str(qty), 'unit_cost_cents': cost}]}).json()['id']


def receive(client, purchase, key, document, qty, cost, invoice, note='', day='2026-11-02'):
    return client.post(f'/api/purchases/{purchase}/receive', json={'document': document, 'occurred_at': at(day, '12:00'), 'invoice_total_cents': invoice, 'invoice_note': note,
                                                                   'lines': [{'item_id': key, 'quantity': str(qty), 'unit_cost_cents': cost}]})


def balance(client, key):
    return float(next(i for i in client.get('/api/items').json() if i['id'] == key)['balance'])


def test_receipt_checks_invoice_quantities_and_costs(client):
    key = item(client); purchase = order(client, key)
    refused = receive(client, purchase, key, 'NF-10', 4, 600, 2500)
    assert refused.status_code == 422 and 'R$ 25,00' in refused.json()['detail'] and 'R$ 24,00' in refused.json()['detail']
    assert client.get('/api/expenses').json() == [] and balance(client, key) == 0
    assert receive(client, purchase, key, 'NF-10', 4, 600, 2500, 'Frete de R$ 1,00').json()['status'] == 'partial'
    assert receive(client, purchase, key, 'NF-10', 1, 500, 500).status_code == 409
    assert receive(client, purchase, key, 'NF-11', 7, 500, 3500).status_code == 409
    assert receive(client, purchase, key, 'NF-11', 4, 500, 2000).status_code == 201
    checks = client.get('/api/purchase-receipts').json()
    receipts = {r['document']: r for r in checks['receipts']}
    assert receipts['NF-10']['ok'] is False and receipts['NF-10']['invoice_difference_cents'] == 100
    assert any('20% acima do estimado' in issue for issue in receipts['NF-10']['issues'])
    assert receipts['NF-11']['ok'] is True
    assert float(checks['pending_orders'][0]['missing'][0]['missing']) == 2
    assert balance(client, key) == 8
    assert [e['category'] for e in client.get('/api/expenses').json()] == ['Mercadorias', 'Mercadorias']
    assert client.post(f'/api/purchases/{purchase}/close', json={'reason': 'Fornecedor sem estoque'}).json()['status'] == 'closed'
    assert client.get('/api/purchase-receipts').json()['pending_orders'] == []


def test_stock_movements_never_go_negative(client):
    key = item(client)
    assert client.post('/api/stock-movements', json={'item_id': key, 'kind': 'entry', 'quantity': '10', 'occurred_at': at('2026-11-01'), 'reason': 'Saldo inicial'}).status_code == 201
    assert client.post('/api/stock-movements', json={'item_id': key, 'kind': 'output', 'quantity': '1.5', 'occurred_at': at('2026-11-02'), 'reason': 'Venda'}).status_code == 422
    assert client.post('/api/stock-movements', json={'item_id': key, 'kind': 'loss', 'quantity': '11', 'occurred_at': at('2026-11-02'), 'reason': 'Vencido'}).status_code == 409
    assert client.post('/api/stock-movements', json={'item_id': key, 'kind': 'output', 'quantity': '3', 'occurred_at': at('2026-11-02'), 'reason': 'Venda'}).status_code == 201
    assert balance(client, key) == 7
    assert client.post('/api/items', json={'name': 'refrigerante', 'category': 'Bebidas', 'unit': 'un'}).status_code == 409


def test_inventory_count_is_all_or_nothing(client):
    first, second = item(client), item(client, 'Arroz', 'kg')
    for key, quantity in [(first, 10), (second, 5)]:
        client.post('/api/stock-movements', json={'item_id': key, 'kind': 'entry', 'quantity': str(quantity), 'occurred_at': at('2026-11-01'), 'reason': 'Saldo inicial'})
    sheet = {i['id']: float(i['expected']) for i in client.get('/api/inventory-sheet', params={'at': at('2026-11-02', '18:00')}).json()['items']}
    assert sheet == {first: 10, second: 5}
    count = {'counted_at': at('2026-11-02', '18:00'), 'note': 'Inventário semanal', 'lines': [{'item_id': first, 'expected': '10', 'counted': '9'}, {'item_id': second, 'expected': '4', 'counted': '5'}]}
    assert client.post('/api/inventory-counts', json=count).status_code == 409
    assert client.get('/api/inventory-counts').json() == []
    count['lines'][1]['expected'] = '5'
    assert client.post('/api/inventory-counts', json=count).json() == {'counted': 2, 'with_difference': 1}
    assert balance(client, first) == 9 and balance(client, second) == 5
