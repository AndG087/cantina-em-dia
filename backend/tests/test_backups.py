import base64
import hashlib
import io
import json
import zipfile
import subprocess
import os
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app import backups, storage
from app.attachments import AttachmentIn, upload
from app.database import engine, SessionLocal, Base
from app.config import ROOT
from app.models import Attachment, AuditLog, BackupRecord, Employee, Shift, StockItem, StockLot, StockMovement


@pytest.fixture(autouse=True)
def backup_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DATA_ROOT', tmp_path)


@pytest.fixture
def committed_records(backup_storage):
    """Dados confirmados no banco de testes, visíveis ao retrato independente."""
    assert engine.url.database == 'cantina_em_dia_test'
    token = uuid4().hex
    with SessionLocal() as db:
        employee = Employee(name='Responsável do teste de backup', role='Teste', active=True); db.add(employee); db.flush()
        item = StockItem(sku='BKP-' + token, name='Insumo de teste', category='Teste', kind='ingredient', unit='kg', minimum=Decimal('0.250'), balance=Decimal('1.234'), unit_cost_cents=123, cost_known=True)
        db.add(item); db.flush()
        lot = StockLot(item_id=item.id, code='Lote de teste', expiry=date(2027, 1, 1), balance=Decimal('1.234'), unit_cost_cents=Decimal('123.123456'), received_at=datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc), cost_known=True)
        db.add(lot); db.flush()
        movement = StockMovement(item_id=item.id, lot_id=lot.id, quantity=Decimal('1.234'), kind='opening', reason='Conferência de backup', unit_cost_cents=Decimal('123.123456'), occurred_at=lot.received_at, cost_known=True)
        db.add(movement)
        shift = Shift(employee_id=employee.id, weekday=0, start_time=time(8, 30), end_time=time(12, 45), valid_from=date(2026, 1, 1))
        db.add(shift); db.flush()
        log = AuditLog(entity='backup_test', entity_id=token, action='test', details={'texto': 'Ação em português', 'valor_decimal_texto': '123.123456', 'flag': False})
        db.add(log); db.commit()
        employee_id, item_id, lot_id, movement_id, shift_id = employee.id, item.id, lot.id, movement.id, shift.id
    with engine.begin() as connection:
        for _ in range(3): connection.execute(text("SELECT nextval(pg_get_serial_sequence('employees', 'id'))"))
    content = 'Comprovante de teste, com acentuação e valores a conferir.'.encode('utf-8')
    with SessionLocal() as db:
        attachment = upload(AttachmentIn(filename='mensagem.txt', content_base64=base64.b64encode(content).decode(), entity='employee', entity_id=employee_id, note='Treinamento de teste'), db)
    attachment_id = attachment['id']
    with SessionLocal() as db:
        path = storage.attachment_path(db.get(Attachment, attachment_id).storage_name)
    try:
        yield {'employee': employee_id, 'item': item_id, 'lot': lot_id, 'movement': movement_id, 'shift': shift_id, 'attachment': attachment_id, 'file': path, 'content': content}
    finally:
        # Exclusão estritamente dos registros criados por este teste, no banco isolado.
        with engine.begin() as connection:
            connection.execute(Attachment.__table__.delete().where(Attachment.id == attachment_id))
            connection.execute(AuditLog.__table__.delete().where(AuditLog.entity == 'attachment', AuditLog.entity_id == str(attachment_id)))
            connection.execute(AuditLog.__table__.delete().where(AuditLog.entity == 'backup_test', AuditLog.entity_id == token))
            connection.execute(Shift.__table__.delete().where(Shift.id == shift_id))
            connection.execute(StockMovement.__table__.delete().where(StockMovement.id == movement_id))
            connection.execute(StockLot.__table__.delete().where(StockLot.id == lot_id))
            connection.execute(StockItem.__table__.delete().where(StockItem.id == item_id))
            connection.execute(Employee.__table__.delete().where(Employee.id == employee_id))


def counts():
    with engine.connect() as connection:
        return {table.name: len(connection.execute(select(table.c.id)).all()) for table in Base.metadata.sorted_tables}


def test_backup_roundtrip_preserves_decimal_dates_json_and_files(client, committed_records):
    data = committed_records; before = counts()
    response = client.post('/api/backups', json={})
    assert response.status_code == 201, response.text
    record = response.json(); path = storage.backup_path(record['filename'])
    assert digest(path) == record['sha256']
    assert client.get(f"/api/backups/{record['id']}/download").content == path.read_bytes()
    verified = client.post(f"/api/backups/{record['id']}/verify", json={})
    assert verified.status_code == 200, verified.text
    assert verified.json()['verified'] and verified.json()['attachments'] >= 1
    assert verified.json()['database'] is None
    assert counts() == before
    data['file'].unlink()  # perda simulada somente na pasta temporária deste teste
    restored = client.post(f"/api/backups/{record['id']}/restore", json={})
    assert restored.status_code == 201, restored.text
    name = restored.json()['database']; copied = create_engine(engine.url.set(database=name))
    try:
        with Session(copied) as db:
            lot = db.get(StockLot, data['lot'])
            assert lot.balance == Decimal('1.234') and lot.unit_cost_cents == Decimal('123.123456')
            assert lot.expiry == date(2027, 1, 1) and lot.received_at.utcoffset().total_seconds() in (0, -10800)
            assert db.get(Shift, data['shift']).start_time == time(8, 30)
            assert db.get(Attachment, data['attachment']).entity_id == data['employee']
            assert db.scalar(select(AuditLog).where(AuditLog.entity == 'backup_test')).details['texto'] == 'Ação em português'
            added = Employee(name='Novo após restauração', role='Teste', active=True); db.add(added); db.commit()
            assert added.id > data['employee'] + 3  # inclui IDs reservados e não usados na origem
        assert data['file'].read_bytes() == data['content']
        assert counts() == before  # banco de origem preservado
        latest = client.get('/api/backups').json()[0]
        assert latest['last_restore_database'] == name and latest['verified_at']
    finally:
        copied.dispose(); backups.database_admin(name, False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_altered_archive_rejected_before_creating_database(client, monkeypatch):
    record = client.post('/api/backups', json={}).json(); path = storage.backup_path(record['filename'])
    path.write_bytes(b'alterado')
    def forbidden(*args, **kwargs): raise AssertionError('Não criar banco para arquivo inválido.')
    monkeypatch.setattr(backups, 'database_admin', forbidden)
    assert client.post(f"/api/backups/{record['id']}/verify", json={}).status_code == 409
    assert client.get(f"/api/backups/{record['id']}/download").status_code == 409


def test_import_recovers_backup_catalog_and_rejects_duplicates(client, isolated_test_database):
    record = client.post('/api/backups', json={}).json(); content = storage.backup_path(record['filename']).read_bytes()
    isolated_test_database.execute(BackupRecord.__table__.delete().where(BackupRecord.id == record['id']))
    assert client.get('/api/backups').json() == []
    response = client.post('/api/backups/import?filename=copia-externa.zip', content=content, headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 201, response.text
    assert response.json()['label'] == 'copia-externa.zip'
    assert client.get(f"/api/backups/{response.json()['id']}/download").content == content
    assert client.post('/api/backups/import', content=content, headers={'Content-Type': 'application/octet-stream'}).status_code == 409
    assert not list(storage.directory('backups').glob('*.part'))


def test_invalid_import_and_size_limit_do_not_leave_files(client, monkeypatch):
    assert client.post('/api/backups/import', content=b'nao e um zip', headers={'Content-Type': 'application/octet-stream'}).status_code == 422
    monkeypatch.setattr(backups, 'MAX_ZIP_BYTES', 3)
    assert client.post('/api/backups/import', content=b'1234', headers={'Content-Type': 'application/octet-stream'}).status_code == 413
    assert not list(storage.directory('backups').iterdir())


def test_zip_extra_paths_are_rejected_without_extraction(client):
    record = client.post('/api/backups', json={}).json(); original = storage.backup_path(record['filename'])
    output = io.BytesIO()
    with zipfile.ZipFile(original) as archive, zipfile.ZipFile(output, 'w') as modified:
        manifest = json.loads(archive.read('manifest.json'))
        manifest['files']['../fora.txt'] = hashlib.sha256(b'fora').hexdigest()
        for name in archive.namelist():
            if name != 'manifest.json': modified.writestr(name, archive.read(name))
        modified.writestr('../fora.txt', b'fora'); modified.writestr('manifest.json', json.dumps(manifest))
    response = client.post('/api/backups/import', content=output.getvalue(), headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 422
    assert not (storage.DATA_ROOT / 'fora.txt').exists()


def test_mutations_reject_other_websites(client):
    assert client.post('/api/backups', json={}, headers={'Origin': 'https://outro-site.example'}).status_code == 403
    assert client.post('/api/employees', json={'name': 'Injeção externa', 'role': 'Teste'}, headers={'Origin': 'https://outro-site.example'}).status_code == 403
    assert client.get('/api/employees').json() == []
    assert client.post('/api/backups', json={}, headers={'Origin': 'http://127.0.0.1:5173'}).status_code == 201


def test_missing_receipt_does_not_generate_false_success(client, committed_records):
    committed_records['file'].unlink()
    response = client.post('/api/backups', json={})
    assert response.status_code == 409 and 'ausente' in response.json()['detail']
    assert client.get('/api/backups').json() == []
    assert not list(storage.directory('backups').iterdir())


def test_schema_revision_guard_and_production_database_protection(client):
    with pytest.raises(ValueError): backups.database_admin('cantina_em_dia', False)
    record = client.post('/api/backups', json={}).json()
    original = storage.backup_path(record['filename']); output = io.BytesIO()
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(output, 'w') as changed:
        manifest = json.loads(source.read('manifest.json')); manifest['revision'] = '0001_foundation'
        for name in source.namelist():
            changed.writestr(name, json.dumps(manifest) if name == 'manifest.json' else source.read(name))
    assert client.post('/api/backups/import', content=output.getvalue(), headers={'Content-Type': 'application/octet-stream'}).status_code == 409


def test_daily_cli_creates_once_and_honors_file_location(backup_storage):
    assert engine.url.database == 'cantina_em_dia_test'
    with engine.connect() as connection:
        before = set(connection.scalars(select(BackupRecord.id)).all())
    env = {**os.environ, 'CANTINA_DATA_DIR': str(storage.DATA_ROOT), 'PYTHONUTF8': '1'}
    try:
        command = [sys.executable, '-m', 'app.backup_cli', 'create', '--if-due']
        first = subprocess.run(command, cwd=ROOT / 'backend', env=env, capture_output=True, encoding='utf-8', timeout=60,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        assert first.returncode == 0, 'A criação de backup pela linha de comando falhou.'
        second = subprocess.run(command, cwd=ROOT / 'backend', env=env, capture_output=True, encoding='utf-8', timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        assert second.returncode == 0 and 'já disponível' in second.stdout
        with engine.connect() as connection:
            created = connection.execute(select(BackupRecord).where(BackupRecord.id.not_in(before or {-1}))).mappings().all()
        assert len(created) == 1
        assert storage.backup_path(created[0]['filename']).is_file()
    finally:
        with engine.begin() as connection:
            connection.execute(BackupRecord.__table__.delete().where(BackupRecord.id.not_in(before or {-1})))
            # O CLI grava auditoria própria; remover somente os eventos deste teste.
            connection.execute(AuditLog.__table__.delete().where(AuditLog.entity == 'backup', AuditLog.entity_id.in_([str(r['id']) for r in locals().get('created', [])])))
