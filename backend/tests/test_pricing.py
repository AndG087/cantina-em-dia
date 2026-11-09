from test_finance import product


def sale(client, item, when, price):
    return client.post('/api/sales', json={'occurred_at': when, 'lines': [{'item_id': item, 'quantity': '1', 'unit_price_cents': price}], 'payments': [{'method': 'pix', 'amount_cents': price}]})


def rule(client, item, **extra):
    return client.post('/api/price-rules', json={'item_id': item, 'effective_from': '2026-11-03T00:00:00-03:00', 'price_cents': 450,
                        'locked': True, 'source': 'Aditivo documentado TESTE', 'reason': 'Nova tabela autorizada', **extra})


def test_price_uses_sale_date_and_keeps_old_sales(client):
    item = product(client)
    first = sale(client, item, '2026-11-02T09:00:00-03:00', 400)
    assert first.status_code == 201
    assert rule(client, item).status_code == 201
    assert sale(client, item, '2026-11-03T09:00:00-03:00', 400).status_code == 409
    assert sale(client, item, '2026-11-03T09:00:00-03:00', 450).status_code == 201
    assert sale(client, item, '2026-11-02T10:00:00-03:00', 400).status_code == 201
    assert client.get('/api/items').json()[0]['sale_price_cents'] == 450
    assert client.get('/api/sales').json()[-1]['total_cents'] == 400
    assert rule(client, item, effective_from='2026-11-02T00:00:00-03:00').status_code == 409


def test_future_rule_cancel_preserves_history_and_current_price(client):
    item = product(client)
    new = rule(client, item, effective_from='2030-01-01T00:00:00-03:00').json()
    assert client.get('/api/items').json()[0]['sale_price_cents'] == 400
    quote = client.get(f'/api/items/{item}/price', params={'at': '2030-01-02T00:00:00-03:00'}).json()
    assert quote['sale_price_cents'] == 450
    assert client.post(f"/api/price-rules/{new['id']}/cancel", json={'reason': 'Documento substituído'}).status_code == 200
    assert len(client.get('/api/price-rules').json()) == 2
    assert client.get(f'/api/items/{item}/price', params={'at': '2030-01-02T00:00:00-03:00'}).json()['sale_price_cents'] == 400


def test_rule_with_sales_cannot_be_cancelled_or_changed_by_item_edit(client):
    item = product(client); new = rule(client, item).json()
    assert sale(client, item, '2026-11-03T10:00:00-03:00', 450).status_code == 201
    assert client.post(f"/api/price-rules/{new['id']}/cancel", json={'reason': 'Não pode alterar passado'}).status_code == 409
    payload = client.get('/api/items').json()[0]; payload.pop('id'); payload.pop('balance')
    payload['sale_price_cents'] = 500
    assert client.put(f'/api/items/{item}', json=payload).status_code == 409


def test_rule_requires_document_and_timezone(client):
    item = product(client)
    assert rule(client, item, source='').status_code == 422
    assert rule(client, item, effective_from='2026-11-03T00:00:00').status_code == 422
