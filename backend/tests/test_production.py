from test_inventory import item, movement
from test_finance import sell


def recipe(client):
    raw = item(client); movement(client, raw, 10)
    ready = client.post('/api/items', json={'sku': 'MARMITA', 'name': 'Marmita teste', 'category': 'Almoço', 'kind': 'product', 'unit': 'un', 'sale_price_cents': 2000}).json()['id']
    recipe = client.post('/api/recipes', json={'product_id': ready, 'name': 'Receita teste', 'yield_quantity': '10', 'instructions': 'Modo de preparo medido', 'lines': [{'item_id': raw, 'quantity': '2'}]})
    assert recipe.status_code == 201, recipe.text
    return raw, ready, recipe.json()['id']


def produce(client, key, **changes):
    return client.post('/api/production-runs', json={'recipe_id': key, 'planned_output': '10', 'actual_output': '8', 'occurred_at': '2026-11-02T08:00:00-03:00', 'input_source': 'recipe_estimate', 'note': 'Estimativa a conferir', **changes})


def test_production_consumes_raw_once_and_creates_finished_goods(client):
    raw, ready, recipe_id = recipe(client)
    result = produce(client, recipe_id)
    assert result.status_code == 201, result.text
    balance = {i['id']: float(i['balance']) for i in client.get('/api/items').json()}
    assert balance[raw] == 8 and balance[ready] == 8
    sale = client.post('/api/sales', json={'occurred_at': '2026-11-02T09:00:00-03:00', 'lines': [{'item_id': ready, 'quantity': '1', 'unit_price_cents': 2000}], 'payments': [{'method': 'pix', 'amount_cents': 2000}]})
    assert sale.status_code == 201, sale.text
    balance = {i['id']: float(i['balance']) for i in client.get('/api/items').json()}
    assert balance[raw] == 8 and balance[ready] == 7
    assert sale.json()['cost_cents'] == 125


def test_measured_inputs_and_sample_component(client):
    raw, ready, recipe_id = recipe(client)
    result = produce(client, recipe_id, input_source='measured', inputs=[{'item_id': raw, 'quantity': '3'}])
    assert result.status_code == 201
    standard = client.post('/api/portion-standards', json={'recipe_id': recipe_id, 'component': 'Proteína pronta', 'target_g': '120', 'tolerance_g': '5'}).json()['id']
    sample = client.post('/api/portion-samples', json={'run_id': result.json()['id'], 'standard_id': standard, 'measured_g': '150', 'occurred_at': '2026-11-02T09:00:00-03:00', 'note': 'Pesagem com tara'})
    assert sample.status_code == 201, sample.text
    assert client.get('/api/portion-samples').json()[0]['outside_tolerance'] is True


def test_cancel_unused_production_restores_inputs(client):
    raw, ready, recipe_id = recipe(client)
    run = produce(client, recipe_id).json()['id']
    response = client.post(f'/api/production-runs/{run}/cancel', json={'reason': 'Lançado em duplicidade'})
    assert response.status_code == 200, response.text
    balance = {i['id']: float(i['balance']) for i in client.get('/api/items').json()}
    assert balance[raw] == 10 and balance[ready] == 0
