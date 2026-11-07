def item(client, sku='ARROZ', unit='kg'):
    response = client.post('/api/items', json={'sku': sku, 'name': 'Arroz teste', 'category': 'Insumos', 'kind': 'ingredient', 'unit': unit, 'unit_cost_cents': 500})
    assert response.status_code == 201
    return response.json()['id']


def movement(client, key, qty, kind='incoming', **extra):
    return client.post('/api/stock-movements', json={'item_id': key, 'quantity': str(qty), 'kind': kind, 'occurred_at': '2026-11-01T09:00:00-03:00', 'reason': 'Documento de teste', **extra})


def test_stock_no_negative_reversal_and_duplicate_sku(client):
    key = item(client)
    assert movement(client, key, 10).status_code == 201
    outgoing = movement(client, key, 3, 'consumption', occurred_at='2026-11-02T10:00:00-03:00')
    assert outgoing.status_code == 201
    assert movement(client, key, 20, 'consumption').status_code == 409
    assert float(client.get('/api/items').json()[0]['balance']) == 7
    original = outgoing.json()[0]['id']
    assert client.post(f'/api/stock-movements/{original}/reverse', json={'reason': 'Correção do lançamento'}).status_code == 201
    assert client.post(f'/api/stock-movements/{original}/reverse', json={'reason': 'Correção duplicada'}).status_code == 409
    assert float(client.get('/api/items').json()[0]['balance']) == 10


def test_expired_lot_blocked_but_can_be_recorded_as_loss(client):
    key = item(client)
    assert movement(client, key, 5, expiry='2026-11-01').status_code == 201
    assert movement(client, key, 1, 'consumption', occurred_at='2026-11-02T10:00:00-03:00').status_code == 409
    assert movement(client, key, 5, 'loss', occurred_at='2026-11-02T10:00:00-03:00').status_code == 201
    assert float(client.get('/api/items').json()[0]['balance']) == 0


def test_count_stale_guard_and_late_date(client):
    key = item(client)
    movement(client, key, 10)
    request = {'item_id': key, 'counted_at': '2026-11-02T12:00:00-03:00', 'counted': '8', 'expected': '9', 'reason': 'Contagem acompanhada'}
    assert client.post('/api/inventory-counts', json=request).status_code == 409
    assert client.post('/api/inventory-counts', json={**request, 'expected': '10'}).status_code == 201
    assert float(client.get('/api/items').json()[0]['balance']) == 8


def test_units_and_fixed_prices(client):
    key = item(client, unit='un')
    assert movement(client, key, '1.5').status_code == 422
    response = client.post('/api/items', json={'sku': 'LATA', 'name': 'Refrigerante lata', 'category': 'Bebidas', 'kind': 'product', 'unit': 'un', 'sale_price_cents': 400, 'price_locked': True})
    record = response.json(); record.pop('id'); record.pop('balance')
    assert client.put(f"/api/items/{response.json()['id']}", json={**record, 'sale_price_cents': 450}).status_code == 409
