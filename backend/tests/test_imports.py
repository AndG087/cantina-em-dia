import hashlib
from test_finance import product


def commit_payload(kind, content, **extra):
    return {'kind': kind, 'content': content, 'expected_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(), **extra}


def test_preview_does_not_write_and_commit_is_idempotent(client):
    content = 'sku;name;category;kind;unit;unit_cost;sale_price\nIMP1;Produto importado;Bebidas;product;un;2,50;4,00\n'
    payload = commit_payload('items', content)
    preview = {k: v for k, v in payload.items() if k != 'expected_hash'}
    response = client.post('/api/imports/preview', json=preview)
    assert response.status_code == 200, response.text
    assert response.json()['row_count'] == 1
    assert client.get('/api/items').json() == [] and client.get('/api/imports').json() == []
    saved = client.post('/api/imports/commit', json=payload)
    assert saved.status_code == 201, saved.text
    assert client.get('/api/items').json()[0]['sale_price_cents'] == 400
    assert client.post('/api/imports/commit', json=payload).status_code == 409
    assert client.get(f"/api/imports/{saved.json()['id']}/source").text == content


def test_import_batch_is_atomic_and_hash_changes_require_new_preview(client):
    content = 'sku;name;category;kind;unit\nNOVO;Produto novo;Bebidas;product;un\nINVALIDO;Item ruim;Bebidas;errado;un\n'
    response = client.post('/api/imports/commit', json=commit_payload('items', content))
    assert response.status_code == 422 and 'Linha 3' in response.json()['detail']
    assert client.get('/api/items').json() == [] and client.get('/api/imports').json() == []
    assert client.post('/api/imports/commit', json={**commit_payload('items', content), 'expected_hash': 'a' * 64}).status_code == 409


def test_summary_and_settlement_import_not_double_revenue(client):
    content = 'external_id;occurred_at;method;amount\nSTONE-123;02/11/2026 10:00;Crédito;25,00\n'
    response = client.post('/api/imports/commit', json=commit_payload('sales_summary', content))
    assert response.status_code == 201, response.text
    settlement = 'external_id;method;gross;fee;occurred_at;reference\nSTONE-123;Crédito;25,00;0,75;03/11/2026 12:00;CREDITO-123\n'
    response = client.post('/api/imports/commit', json=commit_payload('settlements', settlement))
    assert response.status_code == 201, response.text
    report = client.get('/api/reports/monthly?month=2026-11').json()
    assert report['sales_cents'] == 2500 and report['receipts_net_cents'] == 2425
    assert report['operating_result_cents'] is None  # Sem itens/custo: não inventar lucro.


def test_item_sale_import_decrements_stock_once(client):
    key = product(client)
    content = 'external_id;occurred_at;method;sku;quantity;unit_price\nSKU-SALE-1;02/11/2026 10:00;Pix;LATA;2;4,00\n'
    response = client.post('/api/imports/commit', json=commit_payload('sales_items', content))
    assert response.status_code == 201, response.text
    assert float(client.get('/api/items').json()[0]['balance']) == 8
    assert client.post('/api/imports/commit', json=commit_payload('sales_items', content)).status_code == 409
    assert float(client.get('/api/items').json()[0]['balance']) == 8


def test_initial_stock_future_expiry_and_quantity_precision(client):
    client.post('/api/items', json={'sku': 'IMP-LOTE', 'name': 'Ingrediente', 'category': 'Insumos', 'kind': 'ingredient', 'unit': 'kg'})
    content = 'external_id;sku;quantity;occurred_at;unit_cost;expiry\nLOTE-1;IMP-LOTE;2,5;02/11/2026 10:00;5,00;2027-12-31\n'
    response = client.post('/api/imports/commit', json=commit_payload('initial_stock', content))
    assert response.status_code == 201, response.text
    assert float(client.get('/api/items').json()[0]['balance']) == 2.5
    wrong = content.replace('LOTE-1', 'LOTE-2').replace('2,5;', '0,0001;')
    assert client.post('/api/imports/commit', json=commit_payload('initial_stock', wrong)).status_code == 422
