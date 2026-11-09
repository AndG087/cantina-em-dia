from decimal import Decimal
from sqlalchemy import select

from app.models import StockLot, StockMovement, Sale, CostRevision
from test_finance import product, cash, sell
from test_inventory import movement
from test_production import recipe, produce
from test_inventory import item
from test_purchases import order


def correction(client, lot, cost, **extra):
    payload = {'lot_id': lot, 'unit_cost_cents': str(cost), 'confirmed': True, 'document': 'Nota conferida TESTE', 'reason': 'Correção após conferência da nota', **extra}
    response = client.post('/api/cost-revisions/preview', json=payload)
    assert response.status_code == 200, response.text
    return payload, response.json()


def confirm(client, payload, preview):
    return client.post('/api/cost-revisions', json={**payload, 'expected_fingerprint': preview['expected_fingerprint']})


def test_corrects_sale_cost_without_rewriting_original_or_assessment(client, isolated_test_database):
    key = product(client); session = cash(client); sale = sell(client, key, session).json()['id']
    client.post('/api/goals', json={'month': '2026-11', 'basis': 'net_sales', 'target_cents': 0, 'agreement': 'Acordo de teste documentado'})
    saved = client.post('/api/goal-assessments', json={'month': '2026-11', 'owner_approved': False, 'note': 'Apuração antes da correção'}).json()
    lot = client.get('/api/stock-lots').json()[0]['id']
    payload, preview = correction(client, lot, 300)
    assert preview['sales'] == [{'id': sale, 'before_cents': 200, 'after_cents': 300, 'voided': False}]
    assert client.get('/api/cost-revisions').json() == []
    assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/reports/monthly?month=2026-11').json()['cogs_cents'] == 300
    assert client.get('/api/sales').json()[0]['original_cost_cents'] == 200
    assert client.get('/api/sales').json()[0]['cost_cents'] == 300
    assert isolated_test_database.scalar(select(Sale.cost_cents).where(Sale.id == sale)) == 200
    assert isolated_test_database.scalar(select(StockLot.unit_cost_cents).where(StockLot.id == lot)) == Decimal(200)
    after = client.get('/api/goal-assessments').json()[0]
    assert after['report'] == saved['report'] and after['has_later_cost_revision'] is True
    assert float(client.get('/api/items').json()[0]['balance']) == 9


def test_propagates_raw_cost_to_production_and_existing_and_future_sales(client):
    raw, ready, key = recipe(client)
    run = produce(client, key, input_source='measured', inputs=[{'item_id': raw, 'quantity': '2'}]).json()['id']
    def sell_ready():
        return client.post('/api/sales', json={'occurred_at': '2026-11-03T09:00:00-03:00', 'lines': [{'item_id': ready, 'quantity': '1', 'unit_price_cents': 2000}], 'payments': [{'method': 'pix', 'amount_cents': 2000}]})
    assert sell_ready().json()['cost_cents'] == 125
    lots = client.get('/api/stock-lots?include_empty=true').json()
    raw_lot = next(l['id'] for l in lots if l['item_id'] == raw)
    finished = next(l['id'] for l in lots if l['item_id'] == ready)
    payload, preview = correction(client, raw_lot, 1000)
    assert preview['productions'][0]['id'] == run
    assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/production-runs').json()[0]['total_cost_cents'] == 2000
    assert client.get('/api/sales').json()[0]['cost_cents'] == 250
    assert sell_ready().json()['cost_cents'] == 250
    assert client.post('/api/cost-revisions/preview', json={**payload, 'lot_id': finished}).status_code == 409


def test_unknown_zero_cost_can_be_confirmed_and_previous_values_preserved(client):
    response = client.post('/api/items', json={'sku': 'ZERO', 'name': 'Doação teste', 'category': 'Teste', 'kind': 'product', 'unit': 'un', 'sale_price_cents': 400})
    key = response.json()['id']; movement(client, key, 2)
    session = cash(client); sell(client, key, session)
    assert client.get('/api/reports/monthly?month=2026-11').json()['result_complete'] is False
    lot = client.get('/api/stock-lots').json()[0]['id']
    payload, preview = correction(client, lot, 0)
    assert client.post('/api/cost-revisions/preview', json={**payload, 'confirmed': False}).status_code == 422
    assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/reports/monthly?month=2026-11').json()['result_complete'] is True
    assert client.get('/api/cost-revisions').json()[0]['previous_known'] is False


def test_stale_preview_is_rejected_and_revisions_are_append_only(client):
    key = product(client); lot = client.get('/api/stock-lots').json()[0]['id']
    payload, preview = correction(client, lot, 300)
    movement(client, key, 1)
    assert confirm(client, payload, preview).status_code == 409
    assert client.get('/api/cost-revisions').json() == []
    payload, preview = correction(client, lot, 300); assert confirm(client, payload, preview).status_code == 201
    payload, preview = correction(client, lot, 200); assert confirm(client, payload, preview).status_code == 201
    assert len(client.get('/api/cost-revisions').json()) == 2
    assert float(next(l for l in client.get('/api/stock-lots').json() if l['id'] == lot)['unit_cost_cents']) == 200


def test_decimal_cost_and_losses_and_depleted_lots(client, isolated_test_database):
    key = product(client, balance=3); lot = client.get('/api/stock-lots').json()[0]['id']
    movement(client, key, 1, 'loss', occurred_at='2026-11-02T10:00:00-03:00')
    payload, preview = correction(client, lot, '123.456789')
    assert confirm(client, payload, preview).status_code == 201
    assert isolated_test_database.scalar(select(CostRevision.unit_cost_cents)) == Decimal('123.456789')
    report = client.get('/api/reports/monthly?month=2026-11').json()
    assert report['losses_and_staff_cents'] == 123 and report['closing_stock_value_cents'] == 247
    movement(client, key, 2, 'loss', occurred_at='2026-11-03T10:00:00-03:00')
    assert client.get('/api/stock-lots').json() == []
    payload, preview = correction(client, lot, 200)
    assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/reports/monthly?month=2026-11').json()['losses_and_staff_cents'] == 600
    assert client.get('/api/reports/monthly?month=2026-11').json()['closing_stock_value_cents'] == 0


def test_purchase_cost_correction_does_not_change_document_or_reimbursement(client):
    key = item(client); purchase = order(client, key, 1)
    received = client.post(f'/api/purchases/{purchase}/receive', json={'document': 'NF-CUSTO', 'occurred_at': '2026-11-02T12:00:00-03:00',
        'paid_by': 'owner', 'lines': [{'item_id': key, 'quantity': '1', 'unit_cost_cents': 500}]}).json()
    before = client.get('/api/expenses').json()
    payments = client.get('/api/expense-payments').json()
    lot = client.get('/api/stock-lots').json()[0]['id']
    payload, preview = correction(client, lot, 550)
    assert preview['purchase_linked'] is True
    assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/expenses').json() == before
    assert client.get('/api/expense-payments').json() == payments
    assert before[0]['id'] == received['expense_id'] and before[0]['amount_cents'] == 500


def test_reversed_manual_loss_uses_revised_cost_and_does_not_remain_as_loss(client):
    key = product(client, balance=3); lot = client.get('/api/stock-lots').json()[0]['id']
    loss = movement(client, key, 1, 'loss', occurred_at='2026-11-02T10:00:00-03:00').json()[0]['id']
    payload, preview = correction(client, lot, 300); confirm(client, payload, preview)
    assert client.post(f'/api/stock-movements/{loss}/reverse', json={'reason': 'Perda lançada em duplicidade'}).status_code == 201
    assert client.get('/api/reports/monthly?month=2026-11').json()['losses_and_staff_cents'] == 0
    assert client.get('/api/reports/monthly?month=2026-11').json()['closing_stock_value_cents'] == 900


def test_cancelled_total_production_loss_is_excluded_after_cost_revision(client):
    raw, ready, key = recipe(client)
    run = produce(client, key, actual_output='0').json()['id']
    lot = next(l['id'] for l in client.get('/api/stock-lots').json() if l['item_id'] == raw)
    payload, preview = correction(client, lot, 1000); assert confirm(client, payload, preview).status_code == 201
    assert client.get('/api/reports/monthly?month=2026-11').json()['losses_and_staff_cents'] == 2000
    assert client.post(f'/api/production-runs/{run}/cancel', json={'reason': 'Produção registrada por engano'}).status_code == 200
    assert client.get('/api/reports/monthly?month=2026-11').json()['losses_and_staff_cents'] == 0
