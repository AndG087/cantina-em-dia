from sqlalchemy import create_engine, delete

from app import backup, main
from app.database import Base
from test_cash import day
from test_expenses import expense
from test_school import event


def test_weekly_report_versions_and_routine(client):
    day(client, '2026-11-02', 10000, 2000, 10000, withdrawals=2000)
    expense(client, 5000, '2026-11-03')
    event(client, kind='recess', title='Recesso escolar', starts_on='2026-11-12', ends_on='2026-11-13', effect='reduced')
    report = client.get('/api/reports/weekly', params={'week': '2026-11-04'}).json()
    assert report['week_start'] == '2026-11-02' and report['totals']['sales_cents'] == 3000 and report['totals']['expenses_cents'] == 5000
    assert report['markdown'].startswith('# Relatório semanal · 02/11 a 08/11/2026') and 'Recesso escolar' in report['markdown']
    assert '*Vendas:* R$ 30,00' in report['text'] and report['cash_pending_days'] >= 1
    assert any('calendário da escola' in action for action in report['actions'])
    assert client.get('/api/reports/weekly', params={'week': '2099-01-05'}).status_code == 422
    assert 'relatorio-semanal-2026-11-02.md' in client.get('/api/reports/weekly.md', params={'week': '2026-11-02'}).headers['content-disposition']
    first = client.post('/api/weekly-reports', json={'week': '2026-11-02', 'note': 'Enviado ao meu pai pelo WhatsApp'}).json()
    assert client.post('/api/weekly-reports', json={'week': '2026-11-06', 'note': 'Reenviado'}).json()['version'] == 2
    assert client.get(f"/api/weekly-reports/{first['id']}").json()['markdown'].startswith('# Relatório semanal')
    routine = client.get('/api/routine').json()
    assert [r['id'] for r in routine] == ['calendar', 'purchases', 'cash', 'weekly', 'expenses'] and routine[0]['status'] == 'pending'


def test_backup_restores_every_table(client, connection, tmp_path):
    day(client, '2026-11-02', 10000, 2000, 10000)
    expense(client, 5000, '2026-11-03')
    event(client)
    before = backup.export(connection)
    path = tmp_path / 'copia.json.gz'
    path.write_bytes(backup.dump(before))
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(delete(table))
    backup.restore(path, connection)
    after = backup.export(connection)
    assert after['tables'] == before['tables'] and after['tables']['cash_sessions']


def test_health_does_not_expose_database_failure(client, monkeypatch):
    assert client.get('/api/health/database').json()['database'] == 'cantina_em_dia_test'
    unavailable = create_engine('mysql+pymysql://test:private@127.0.0.1:1/unavailable', connect_args={'connect_timeout': 1})
    monkeypatch.setattr(main, 'engine', unavailable)
    try:
        response = client.get('/api/health/database')
        assert response.status_code == 503 and 'private' not in response.text
    finally:
        unavailable.dispose()
