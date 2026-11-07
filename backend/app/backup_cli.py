"""Acesso ao backup e à recuperação mesmo quando a interface não está aberta."""
import argparse
import json
from pathlib import Path
import zipfile

from fastapi import HTTPException
from sqlalchemy import select

from . import storage
from .backups import create_backup, restore_archive
from .database import SessionLocal
from .domain import TZ, now
from .models import BackupRecord


def main():
    parser = argparse.ArgumentParser(description='Backup e recuperação do Cantina em Dia')
    parser.add_argument('action', choices=['create', 'verify', 'restore'])
    parser.add_argument('--file', type=Path, help='Arquivo .zip gerado pelo aplicativo')
    parser.add_argument('--if-due', action='store_true', help='Criar somente se não há cópia local íntegra de hoje')
    args = parser.parse_args()
    try:
        if args.action == 'create':
            with SessionLocal() as db:
                last = db.scalar(select(BackupRecord).order_by(BackupRecord.created_at.desc(), BackupRecord.id.desc()).limit(1))
                if args.if_due and last:
                    from .backups import digest_file, head_revision
                    path = storage.backup_path(last.filename)
                    if last.snapshot_at and last.snapshot_at.astimezone(TZ).date() == now().astimezone(TZ).date() and path.is_file() and digest_file(path) == last.sha256:
                        with zipfile.ZipFile(path) as archive:
                            if json.loads(archive.read('manifest.json')).get('revision') == head_revision():
                                print('Backup local de hoje já disponível.'); return
                record = create_backup(db, 'Backup diário na inicialização' if args.if_due else 'Backup pela linha de comando')
                print(f'Backup criado: {storage.backup_path(record.filename)}')
        else:
            if args.file is None: parser.error('--file é obrigatório para verificar ou restaurar.')
            result = restore_archive(args.file.resolve(), verify_only=args.action == 'verify')
            print(json.dumps(result, ensure_ascii=False))
            if args.action == 'restore':
                print('Para usar a cópia, encerre o aplicativo e altere somente o nome do banco em DATABASE_URL no .env. O banco anterior foi preservado.')
    except HTTPException as error:
        print(f'Falha: {error.detail}'); raise SystemExit(1)


if __name__ == '__main__': main()
