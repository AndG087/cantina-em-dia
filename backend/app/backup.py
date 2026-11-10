"""Cópia de segurança: todas as tabelas em um arquivo JSON compactado.

    python -m app.backup create [--if-due]   cria a cópia (--if-due: só se ainda não houver uma hoje)
    python -m app.backup restore ARQUIVO     restaura em um banco vazio, já migrado

O inicializador (npm start) cria uma cópia por dia em %LOCALAPPDATA%\\CantinaEmDia\\backups.
"""
import gzip
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Date, DateTime, Numeric, func, select, text

from .config import settings
from .database import Base, engine
from .domain import TZ, now


def revision(connection) -> str:
    return connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()


def export(connection) -> dict:
    tables = {t.name: [dict(row) for row in connection.execute(select(t).order_by(*t.primary_key.columns)).mappings()] for t in Base.metadata.sorted_tables}
    return {'revision': revision(connection), 'created_at': now().isoformat(), 'tables': tables}


def dump(data) -> bytes:
    encode = lambda value: value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    return gzip.compress(json.dumps(data, default=encode, ensure_ascii=False).encode())


def create(if_due=False) -> Path | None:
    folder = settings.backup_dir
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now().astimezone(TZ)
    if if_due and any(folder.glob(f'cantina-{stamp:%Y%m%d}-*.json.gz')):
        return None
    with engine.connect() as connection, connection.begin():
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'))
        data = export(connection)
    path = folder / f'cantina-{stamp:%Y%m%d-%H%M%S}.json.gz'
    path.write_bytes(dump(data))
    return path


def convert(column, value):
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    if isinstance(column.type, Numeric):
        return Decimal(value)
    return value


def restore(path, connection):
    data = json.loads(gzip.decompress(Path(path).read_bytes()))
    if data['revision'] != revision(connection):
        raise ValueError(f"A cópia é da estrutura {data['revision']}; o banco está em {revision(connection)}.")
    if any(connection.execute(select(func.count()).select_from(t)).scalar() for t in Base.metadata.sorted_tables):
        raise ValueError('O banco de destino precisa estar vazio.')
    for table in Base.metadata.sorted_tables:
        rows = [{key: convert(table.c[key], value) for key, value in row.items()} for row in data['tables'].get(table.name, [])]
        if rows:
            connection.execute(table.insert(), rows)
        connection.execute(text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {table.name}"))


def main(args):
    if args[:1] == ['create']:
        path = create('--if-due' in args)
        print(f'Cópia criada: {path}' if path else 'Já existe uma cópia de hoje.')
    elif args[:1] == ['restore'] and len(args) == 2:
        with engine.begin() as connection:
            restore(args[1], connection)
        print('Cópia restaurada.')
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
