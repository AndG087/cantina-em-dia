from conftest import at
from test_school import event


def day(client, date, opening, cash_sales, counted, withdrawals=0, close=True):
    session = client.post('/api/cash-sessions', json={'opened_at': at(date, '07:00'), 'opened_by': 'Dona Gel', 'opening_cents': opening})
    assert session.status_code == 201, session.text
    key = session.json()['id']
    if close:
        closed = client.post(f'/api/cash-sessions/{key}/close', json={'closed_at': at(date, '22:00'), 'closed_by': 'Dona Gel', 'cash_sales_cents': cash_sales, 'pix_cents': 500, 'voucher_cents': 200,
                                                                     'card_cents': 300, 'withdrawals_cents': withdrawals, 'counted_cents': counted})
        assert closed.status_code == 200, closed.text
    return key


def test_close_computes_expected_and_difference(client):
    key = day(client, '2026-11-02', 10000, 5000, 9900, withdrawals=5000)
    row = client.get('/api/cash-sessions').json()[0]
    assert row['id'] == key and row['expected_cents'] == 10000 and row['difference_cents'] == -100
    assert client.post('/api/cash-sessions', json={'opened_at': at('2026-11-02', '20:00'), 'opened_by': 'Outro', 'opening_cents': 0}).status_code == 409


def test_only_one_open_and_reopen_last(client):
    first = day(client, '2026-11-02', 1000, 0, 1000)
    open_key = day(client, '2026-11-03', 1000, 0, 0, close=False)
    assert client.post('/api/cash-sessions', json={'opened_at': at('2026-11-03', '08:00'), 'opened_by': 'Outro', 'opening_cents': 0}).status_code == 409
    assert client.post(f'/api/cash-sessions/{first}/reopen', json={'reason': 'Correção'}).status_code == 409
    client.post(f'/api/cash-sessions/{open_key}/close', json={'closed_at': at('2026-11-03', '21:00'), 'closed_by': 'Dona Gel', 'cash_sales_cents': 0, 'counted_cents': 1000})
    reopened = client.post(f'/api/cash-sessions/{open_key}/reopen', json={'reason': 'Contagem digitada errada'})
    assert reopened.status_code == 200 and reopened.json()['closed_at'] is None and 'Contagem digitada errada' in reopened.json()['note']


def test_daily_review_points_out_gaps(client):
    day(client, '2026-11-02', 10000, 2000, 9650, withdrawals=2000)
    second = day(client, '2026-11-03', 10000, 0, 10000)
    event(client)
    days = {d['day']: d for d in client.get('/api/cash-reviews/days', params={'end': '2026-11-05', 'days': 4}).json()}
    assert days['2026-11-05']['state'] == 'not_applicable'
    assert any('sem abertura' in issue for issue in days['2026-11-04']['issues'])
    assert any('Troco de abertura R$ 100,00' in issue for issue in days['2026-11-03']['issues'])
    assert any('-R$ 3,50' in issue for issue in days['2026-11-02']['issues'])
    assert days['2026-11-03']['pix_cents'] == 500 and days['2026-11-03']['state'] == 'pending'
    review = {'day': '2026-11-03', 'status': 'ok', 'note': 'Conferido'}
    assert client.post('/api/cash-reviews', json=review).status_code == 409
    assert client.post('/api/cash-reviews', json={**review, 'status': 'issues', 'note': 'R$ 3,50 a mais no troco; orientado'}).status_code == 201
    assert client.post('/api/cash-reviews', json={**review, 'day': '2099-01-01'}).status_code == 422
    assert client.get('/api/cash-reviews/days', params={'end': '2026-11-03', 'days': 1}).json()[0]['state'] == 'reviewed'
    client.post(f'/api/cash-sessions/{second}/reopen', json={'reason': 'Correção da contagem'})
    assert client.get('/api/cash-reviews/days', params={'end': '2026-11-03', 'days': 1}).json()[0]['state'] == 'outdated'


def test_contract_hours_and_voucher_in_daily_review(client):
    key = client.post('/api/cash-sessions', json={'opened_at': at('2026-11-02', '08:10'), 'opened_by': 'Dona Gel', 'opening_cents': 1000}).json()['id']
    client.post(f'/api/cash-sessions/{key}/close', json={'closed_at': at('2026-11-02', '20:30'), 'closed_by': 'Dona Gel', 'cash_sales_cents': 0, 'voucher_cents': 1500, 'counted_cents': 1000})
    day = client.get('/api/cash-reviews/days', params={'end': '2026-11-02', 'days': 1}).json()[0]
    assert day['voucher_cents'] == 1500
    assert any('Abertura às 08:10' in issue for issue in day['issues']) and any('Fechamento às 20:30' in issue for issue in day['issues'])
    report = client.get('/api/reports/weekly', params={'week': '2026-11-02'}).json()
    assert report['totals']['voucher_cents'] == 1500 and report['totals']['sales_cents'] == 1500 and 'Voucher' in report['markdown']
