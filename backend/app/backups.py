"""Backup lógico dos dados da aplicação e arquivos imutáveis.

O retrato usa REPEATABLE READ. Restauração sempre cria outro banco e compara
todos os registros; não executa SQL vindo do arquivo nem sobrescreve o banco atual.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
import zlib
import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Annotated
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, select, text, DateTime, Date, Time, Numeric
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from . import storage
from .attachments import MAX_BYTES as MAX_ATTACHMENT_BYTES, file_type
from .config import ROOT, APP_VERSION, settings
from .database import Base, engine, get_session
from .domain import TZ, audit, get_or_404, lock, now, rows
from .models import BackupRecord
from .team import Input

router = APIRouter(prefix='/api', tags=['Backup e restauração'])
DB = Annotated[Session, Depends(get_session)]
MAX_ZIP_BYTES = 512 * 1024 * 1024
MAX_DATABASE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024


def head_revision():
    return ScriptDirectory.from_config(Config(str(ROOT / 'backend/alembic.ini'))).get_current_head()


def encode_value(value):
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError('Data sem fuso no backup.')
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (date, time)): return value.isoformat()
    raise TypeError('Tipo de dado não suportado pelo formato de backup.')


def json_bytes(value):
    return json.dumps(value, default=encode_value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def sequence_name(connection, table):
    return connection.scalar(text('SELECT pg_get_serial_sequence(:table, :column)'), {'table': table.name, 'column': 'id'})


def read_tables(connection):
    return {table.name: [dict(row) for row in connection.execute(select(table).order_by(*table.primary_key.columns)).mappings()] for table in Base.metadata.sorted_tables}


def snapshot():
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            connection.execute(text('SET TRANSACTION READ ONLY'))
            revision = connection.scalar(text('SELECT version_num FROM alembic_version'))
            if revision != head_revision():
                raise HTTPException(409, 'Aplique as migrações antes de gerar o backup.')
            tables = read_tables(connection)
            sequences = {}
            quote = connection.dialect.identifier_preparer.quote
            for table in Base.metadata.sorted_tables:
                seq = sequence_name(connection, table)
                if seq:
                    # O nome vem do PostgreSQL para uma tabela fixa da aplicação.
                    parts = seq.split('.')
                    sql_name = '.'.join(quote(part.strip('"')) for part in parts)
                    state = connection.execute(text(f'SELECT last_value, is_called FROM {sql_name}')).mappings().one()
                    sequences[table.name] = dict(state)
    return revision, {'tables': tables, 'sequences': sequences}


def public(record):
    file = storage.backup_path(record.filename)
    return {'id': record.id, 'filename': record.filename, 'label': record.label, 'size_bytes': record.size_bytes, 'sha256': record.sha256,
            'created_at': record.created_at, 'snapshot_at': record.snapshot_at, 'verified_at': record.verified_at,
            'last_restore_database': record.last_restore_database, 'last_restored_at': record.last_restored_at,
            'file_available': file.is_file() and file.stat().st_size == record.size_bytes}


def create_backup(db: Session, label='Backup manual'):
    lock(db, 903)
    revision, data = snapshot(); database = json_bytes(data)
    if len(database) > MAX_DATABASE_BYTES:
        raise HTTPException(413, 'Os registros excedem o limite de 64 MB deste formato. Use uma exportação PostgreSQL completa para esse volume.')
    captured = now()
    filename = f'cantina-{captured.astimezone(TZ):%Y%m%dT%H%M%S}-{uuid4().hex[:12]}.zip'
    path = storage.backup_path(filename)
    manifest = {'format': 'cantina-em-dia', 'format_version': 1, 'application_version': APP_VERSION, 'revision': revision, 'created_at': captured.isoformat(),
                'source_database': engine.url.database, 'files': {'database.json': hashlib.sha256(database).hexdigest()}}
    created = False; committed = False
    try:
        with path.open('xb') as raw:
            created = True
            with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('database.json', database)
                total = len(database)
                if len(data['tables']['attachments']) > 20000:
                    raise HTTPException(413, 'O backup excede o limite de 20.000 anexos deste formato.')
                for attachment in data['tables']['attachments']:
                    source = storage.attachment_path(attachment['storage_name'])
                    if not source.is_file(): raise HTTPException(409, f"Anexo #{attachment['id']} ausente. Recupere o arquivo antes do backup.")
                    if source.stat().st_size != attachment['size_bytes'] or source.stat().st_size > MAX_ATTACHMENT_BYTES:
                        raise HTTPException(409, f"Anexo #{attachment['id']} tem tamanho inconsistente.")
                    content = source.read_bytes()
                    if hashlib.sha256(content).hexdigest() != attachment['sha256']:
                        raise HTTPException(409, f"Anexo #{attachment['id']} está alterado. O backup não foi concluído.")
                    total += len(content)
                    if total > MAX_EXPANDED_BYTES: raise HTTPException(413, 'O conteúdo do backup excede o limite de 1 GB.')
                    name = 'attachments/' + attachment['storage_name']
                    manifest['files'][name] = attachment['sha256']; archive.writestr(name, content)
                archive.writestr('manifest.json', json_bytes(manifest))
            raw.flush(); os.fsync(raw.fileno())
        if path.stat().st_size > MAX_ZIP_BYTES: raise HTTPException(413, 'O arquivo de backup excede o limite de 512 MB.')
        record = BackupRecord(filename=filename, label=label, size_bytes=path.stat().st_size, sha256=digest_file(path), snapshot_at=captured)
        db.add(record); db.flush(); audit(db, 'backup', record.id, 'created', {'filename': filename, 'revision': revision, 'attachments': len(data['tables']['attachments'])})
        db.commit(); committed = True; db.refresh(record)
        return record
    except Exception:
        if created and not committed: path.unlink(missing_ok=True)
        raise


def load_archive(path: Path, expected_sha: str | None = None):
    if not path.is_file(): raise HTTPException(404, 'Arquivo de backup não encontrado.')
    if path.stat().st_size > MAX_ZIP_BYTES: raise HTTPException(413, 'Backup maior que 512 MB.')
    if expected_sha and digest_file(path) != expected_sha: raise HTTPException(409, 'O arquivo de backup foi alterado ou está incompleto.')
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist(); names = [entry.filename for entry in infos]
            if len(names) != len(set(names)) or len(names) > 20002 or 'manifest.json' not in names:
                raise ValueError('Estrutura de arquivo inválida.')
            if any(entry.flag_bits & 1 for entry in infos): raise ValueError('Backups criptografados não são suportados neste formato.')
            if sum(entry.file_size for entry in infos) > MAX_EXPANDED_BYTES + MAX_MANIFEST_BYTES:
                raise ValueError('Conteúdo descompactado acima do limite.')
            if archive.getinfo('manifest.json').file_size > MAX_MANIFEST_BYTES: raise ValueError('Manifesto muito grande.')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('format') != 'cantina-em-dia' or manifest.get('format_version') != 1 or not isinstance(manifest.get('files'), dict):
                raise ValueError('Formato de backup não reconhecido.')
            if set(names) != set(manifest['files']) | {'manifest.json'} or 'database.json' not in names:
                raise ValueError('Lista de arquivos inconsistente.')
            if manifest.get('revision') != head_revision():
                raise HTTPException(409, 'Este backup exige a mesma revisão de estrutura do aplicativo. Use a versão correspondente antes de restaurar.')
            if archive.getinfo('database.json').file_size > MAX_DATABASE_BYTES: raise ValueError('Registros acima do limite de 64 MB.')
            raw = archive.read('database.json')
            if hashlib.sha256(raw).hexdigest() != manifest['files']['database.json']: raise ValueError('Registros alterados.')
            data = json.loads(raw)
            if set(data.get('tables', {})) != set(Base.metadata.tables) or not isinstance(data.get('sequences'), dict):
                raise ValueError('Tabelas ou sequências não correspondem à revisão do aplicativo.')
            for name, table_rows in data['tables'].items():
                if not isinstance(table_rows, list): raise ValueError('Dados de tabela inválidos.')
                columns = set(Base.metadata.tables[name].columns.keys())
                if any(not isinstance(row, dict) or set(row) != columns for row in table_rows): raise ValueError('Colunas inconsistentes.')
            for record in data['tables']['backup_records']:
                storage.backup_path(record['filename'])
            if not set(data['sequences']).issubset(Base.metadata.tables): raise ValueError('Sequência desconhecida.')
            expected_files = {'database.json'}
            for attachment in data['tables']['attachments']:
                storage.attachment_path(attachment['storage_name'])  # valida o nome; não extrai caminhos do ZIP
                name = 'attachments/' + attachment['storage_name']; expected_files.add(name)
                if name not in names or not 0 < attachment['size_bytes'] <= MAX_ATTACHMENT_BYTES or archive.getinfo(name).file_size != attachment['size_bytes']:
                    raise ValueError('Anexo ausente ou com tamanho inconsistente.')
                content = archive.read(name)
                digest = hashlib.sha256(content).hexdigest()
                if digest != attachment['sha256'] or digest != manifest['files'].get(name): raise ValueError('Anexo alterado.')
                _, extension = file_type(attachment['original_name'], content)
                if extension != Path(attachment['storage_name']).suffix: raise ValueError('Formato do anexo inconsistente.')
            if expected_files != set(manifest['files']): raise ValueError('O backup contém arquivos sem vínculo.')
            captured = datetime.fromisoformat(manifest['created_at'])
            if captured.tzinfo is None: raise ValueError('Data do backup sem fuso horário.')
            return manifest, data
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as error:
        raise HTTPException(422, 'Backup inválido, incompleto ou com integridade comprometida.') from error


def decode_rows(table, values):
    result = []
    for row in values:
        decoded = {}
        for column in table.columns:
            value = row[column.name]
            if value is not None:
                if isinstance(column.type, DateTime): value = datetime.fromisoformat(value)
                elif isinstance(column.type, Date): value = date.fromisoformat(value)
                elif isinstance(column.type, Time): value = time.fromisoformat(value)
                elif isinstance(column.type, Numeric): value = Decimal(value)
            decoded[column.name] = value
        result.append(decoded)
    return result


def isolated_name(name):
    if not re.fullmatch(r'cantina_(verify|restore)_[a-f0-9]{12}', name):
        raise ValueError('Somente bancos isolados criados pela restauração podem ser administrados por esta função.')


def database_admin(name, create):
    isolated_name(name)
    admin = create_engine(engine.url.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True, connect_args={'connect_timeout': 5})
    try:
        with admin.connect() as connection:
            quoted = connection.dialect.identifier_preparer.quote(name)
            connection.execute(text(f'CREATE DATABASE {quoted}' if create else f'DROP DATABASE IF EXISTS {quoted} WITH (FORCE)'))
    finally: admin.dispose()


def migrate_copy(url):
    env = {**os.environ, 'DATABASE_URL': url.render_as_string(hide_password=False), 'PYTHONUTF8': '1'}
    command = [sys.executable, '-m', 'alembic', '-c', str(ROOT / 'backend/alembic.ini'), 'upgrade', 'head']
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode:
        raise HTTPException(409, 'Não foi possível preparar o banco isolado. Confira as permissões do PostgreSQL e as migrações.')


def restore_archive(path: Path, *, verify_only=False, expected_sha=None):
    manifest, data = load_archive(path, expected_sha)
    name = ('cantina_verify_' if verify_only else 'cantina_restore_') + uuid4().hex[:12]
    target_url = engine.url.set(database=name); target_engine = None; created = False; success = False; copied_files = []
    try:
        database_admin(name, True); created = True; migrate_copy(target_url)
        target_engine = create_engine(target_url, hide_parameters=True, connect_args={'connect_timeout': 5})
        if target_engine.url.database == engine.url.database: raise ValueError('Banco de destino não isolado.')
        with target_engine.begin() as connection:
            # Somente a configuração inicial sem dados operacionais, no banco recém-criado.
            connection.execute(Base.metadata.tables['app_settings'].delete())
            for table in Base.metadata.sorted_tables:
                values = decode_rows(table, data['tables'][table.name])
                for index in range(0, len(values), 500): connection.execute(table.insert(), values[index:index + 500])
                sequence = sequence_name(connection, table)
                if sequence:
                    maximum = max((row['id'] for row in values), default=0)
                    state = data['sequences'].get(table.name, {'last_value': 1, 'is_called': False})
                    last = state['last_value']
                    if not isinstance(last, int) or isinstance(last, bool) or last < 1 or not isinstance(state['is_called'], bool): raise ValueError('Estado de sequência inválido.')
                    value = max(maximum, last)
                    connection.execute(text('SELECT setval(CAST(:sequence AS regclass), :value, :called)'), {'sequence': sequence, 'value': value, 'called': maximum >= last or state['is_called']})
        with target_engine.connect() as connection:
            restored = read_tables(connection)
        if hashlib.sha256(json_bytes(restored)).hexdigest() != hashlib.sha256(json_bytes(data['tables'])).hexdigest():
            raise HTTPException(409, 'A conferência dos registros restaurados falhou. O banco atual foi preservado.')
        if not verify_only:
            with zipfile.ZipFile(path) as archive:
                # Não sobrescrever um arquivo local diferente que tenha o mesmo identificador.
                for item in data['tables']['attachments']:
                    destination = storage.attachment_path(item['storage_name'])
                    if destination.exists() and digest_file(destination) != item['sha256']:
                        raise HTTPException(409, 'Existe um anexo local diferente com o mesmo identificador. O banco atual foi preservado.')
                for item in data['tables']['attachments']:
                    destination = storage.attachment_path(item['storage_name'])
                    if not destination.exists():
                        with destination.open('xb') as file:
                            copied_files.append(destination)
                            file.write(archive.read('attachments/' + item['storage_name'])); file.flush(); os.fsync(file.fileno())
        success = True
        return {'database': None if verify_only else name, 'verified': True, 'revision': manifest['revision'], 'snapshot_at': manifest['created_at'],
                'rows': sum(len(values) for values in data['tables'].values()), 'tables': len(data['tables']), 'attachments': len(data['tables']['attachments'])}
    except subprocess.TimeoutExpired:
        raise HTTPException(409, 'A preparação do banco isolado excedeu o tempo limite. O banco atual foi preservado.')
    except SQLAlchemyError as error:
        if getattr(getattr(error, 'orig', None), 'sqlstate', None) == '42501':
            raise HTTPException(409, 'O usuário do PostgreSQL precisa de permissão para criar bancos isolados. Nenhuma permissão foi alterada.') from error
        raise HTTPException(409, 'Não foi possível restaurar os registros no banco isolado. O banco atual foi preservado.') from error
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(422, 'O backup contém valores incompatíveis com a estrutura atual. O banco atual foi preservado.') from error
    finally:
        cleanup_failed = False
        if target_engine: target_engine.dispose()
        if created and (verify_only or not success):
            try: database_admin(name, False)
            except SQLAlchemyError:
                logging.getLogger('cantina').error('Não foi possível limpar o banco isolado %s.', name)
                cleanup_failed = True
        if not success:
            for file in copied_files: file.unlink(missing_ok=True)
        if cleanup_failed:
            raise HTTPException(409, f'O banco isolado {name} precisa ser removido manualmente. A verificação não foi marcada como concluída; o banco atual foi preservado.')


def backup_file(db, key):
    record = get_or_404(db, BackupRecord, key); path = storage.backup_path(record.filename)
    if not path.is_file(): raise HTTPException(404, 'O backup não está nesta pasta. Importe a cópia guardada em outro local.')
    return record, path


@router.get('/backups')
def list_backups(db: DB):
    return [public(record) for record in rows(db, BackupRecord)]


@router.get('/backups/config')
def configuration():
    return {'format': 'cantina-em-dia', 'format_version': 1, 'max_bytes': MAX_ZIP_BYTES, 'revision': head_revision(), 'auto_enabled': settings.cantina_auto_backup}


@router.post('/backups', status_code=201)
def backup(payload: Input, db: DB):
    return public(create_backup(db))


@router.get('/backups/{key}/download')
def download(key: int, db: DB):
    record, path = backup_file(db, key)
    if digest_file(path) != record.sha256: raise HTTPException(409, 'O arquivo de backup foi alterado ou está incompleto.')
    return FileResponse(path, filename=record.filename, media_type='application/zip', headers={'X-Content-Type-Options': 'nosniff'})


@router.post('/backups/{key}/verify')
def verify(key: int, payload: Input, db: DB):
    lock(db, 903); record, path = backup_file(db, key)
    result = restore_archive(path, verify_only=True, expected_sha=record.sha256)
    record.verified_at = now(); audit(db, 'backup', key, 'restore_verified', result); db.commit()
    return result


@router.post('/backups/{key}/restore', status_code=201)
def restore(key: int, payload: Input, db: DB):
    lock(db, 903); record, path = backup_file(db, key)
    result = restore_archive(path, expected_sha=record.sha256)
    record.verified_at = now(); record.last_restore_database = result['database']; record.last_restored_at = now()
    audit(db, 'backup', key, 'restored_to_new_database', result); db.commit()
    return result


@router.post('/backups/import', status_code=201)
async def import_backup(request: Request, db: DB, filename: Annotated[str, Query(max_length=180)] = 'backup.zip'):
    temporary = storage.directory('backups') / ('upload-' + uuid4().hex + '.part')
    written = 0; created = False
    try:
        with temporary.open('xb') as file:
            created = True
            async for chunk in request.stream():
                written += len(chunk)
                if written > MAX_ZIP_BYTES: raise HTTPException(413, 'Backup maior que 512 MB.')
                file.write(chunk)
            file.flush(); os.fsync(file.fileno())
        manifest, _ = await run_in_threadpool(load_archive, temporary)
        digest = await run_in_threadpool(digest_file, temporary)
        lock(db, 903)
        if db.scalar(select(BackupRecord.id).where(BackupRecord.sha256 == digest)):
            raise HTTPException(409, 'Essa cópia de backup já está cadastrada.')
        captured = datetime.fromisoformat(manifest['created_at'])
        name = f'cantina-{now().astimezone(TZ):%Y%m%dT%H%M%S}-{uuid4().hex[:12]}.zip'
        destination = storage.backup_path(name)
        # Substituição não é usada: o destino é novo e nunca deve sobrescrever outra cópia.
        committed = False; copied = False
        try:
            with temporary.open('rb') as source, destination.open('xb') as file:
                copied = True
                for chunk in iter(lambda: source.read(1024 * 1024), b''): file.write(chunk)
                file.flush(); os.fsync(file.fileno())
            record = BackupRecord(filename=name, label=PurePosixPath(filename.replace('\\', '/')).name[:180], sha256=digest, size_bytes=written, snapshot_at=captured)
            db.add(record); db.flush(); audit(db, 'backup', record.id, 'imported', {'filename': record.label, 'sha256': digest}); db.commit(); committed = True
            return public(record)
        finally:
            if copied and not committed: destination.unlink(missing_ok=True)
    finally:
        if created: temporary.unlink(missing_ok=True)
