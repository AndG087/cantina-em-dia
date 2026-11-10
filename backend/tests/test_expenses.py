from conftest import at
from test_purchases_stock import item, order, receive


def expense(client, amount, date, payee='Distribuidora de gás', document=None, category='Gás'):
    response = client.post('/api/expenses', json={'description': f'{category} {date}', 'category': category, 'amount_cents': amount, 'occurred_at': at(date),
                                                   'payee': payee, 'document': document or f'DOC-{date}-{amount}'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_expense_alerts_and_explanations(client):
    for date in ['2026-10-01', '2026-10-08', '2026-10-15']:
        expense(client, 10000, date)
    high = expense(client, 25000, '2026-11-03')
    expense(client, 4000, '2026-11-04', payee='Mercado do bairro', document='CUPOM-1', category='Limpeza')
    expense(client, 4000, '2026-11-05', payee='Mercado do bairro', document='CUPOM-2', category='Limpeza')
    key = item(client); purchase = order(client, key)
    assert receive(client, purchase, key, 'NF-A', 5, 500, 2500, day='2026-10-20').status_code == 201
    assert receive(client, purchase, key, 'NF-B', 5, 600, 3000, day='2026-11-03').status_code == 201
    result = client.get('/api/expense-alerts', params={'start': '2026-11-02', 'end': '2026-11-08'}).json()
    assert {a['kind'] for a in result['alerts']} == {'above_usual', 'duplicate', 'unit_cost', 'category_increase'}
    above = next(a for a in result['alerts'] if a['kind'] == 'above_usual')
    assert above['severity'] == 'high' and above['reference_cents'] == 10000 and above['key'] == f'above_usual:{high}'
    assert next(a for a in result['alerts'] if a['kind'] == 'unit_cost')['reference_cents'] == 500
    note = {'alert_key': above['key'], 'note': 'Botijão extra para o evento da escola'}
    assert client.post('/api/expense-alerts/notes', json=note).status_code == 201
    assert client.post('/api/expense-alerts/notes', json=note).status_code == 409
    assert client.post('/api/expense-alerts/notes', json={**note, 'alert_key': 'unknown:1'}).status_code == 422
    after = client.get('/api/expense-alerts', params={'start': '2026-11-02', 'end': '2026-11-08'}).json()
    assert after['open_count'] == result['open_count'] - 1


def test_manual_expense_can_be_deleted_but_purchase_expense_cannot(client):
    manual = expense(client, 1000, '2026-11-02')
    assert client.post('/api/expenses', json={'description': 'Repetida', 'category': 'Gás', 'amount_cents': 1000, 'occurred_at': at('2026-11-02'),
                                              'payee': 'Distribuidora de gás', 'document': 'DOC-2026-11-02-1000'}).status_code == 409
    assert client.delete(f'/api/expenses/{manual}').status_code == 204
    key = item(client); purchase = order(client, key)
    receive(client, purchase, key, 'NF-1', 1, 500, 500)
    purchase_expense = client.get('/api/expenses').json()[0]['id']
    assert client.delete(f'/api/expenses/{purchase_expense}').status_code == 409
