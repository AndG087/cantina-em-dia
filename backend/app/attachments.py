import base64
import binascii
import hashlib
import os
from pathlib import PurePosixPath
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import storage
from .database import get_session
from .domain import audit, get_or_404, lock, now
from .inventory import ReasonIn
from .models import Attachment, Expense, ExpensePayment, Sale, Purchase, StockMovement, InventoryCount, ProductionRun, CashSession, Employee
from .team import Input

router = APIRouter(prefix='/api', tags=['Comprovantes e anexos'])
DB = Annotated[Session, Depends(get_session)]
Entity = Literal['inbox', 'expense', 'expense_payment', 'sale', 'purchase', 'stock', 'inventory', 'production', 'cash', 'employee']
MAX_BYTES = 8 * 1024 * 1024
ENTITY_MODELS = {'expense': Expense, 'expense_payment': ExpensePayment, 'sale': Sale, 'purchase': Purchase, 'stock': StockMovement,
                 'inventory': InventoryCount, 'production': ProductionRun, 'cash': CashSession, 'employee': Employee}
ENTITY_LABELS = {'inbox': 'Recebidos / ainda não vinculados', 'expense': 'Despesa', 'expense_payment': 'Pagamento / reembolso', 'sale': 'Venda',
                 'purchase': 'Pedido de compra', 'stock': 'Movimento de estoque', 'inventory': 'Contagem física', 'production': 'Produção', 'cash': 'Caixa', 'employee': 'Funcionário / treinamento'}
MEDIA = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.txt': 'text/plain',
         '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.ogg': 'audio/ogg', '.opus': 'audio/ogg', '.wav': 'audio/wav'}


class AttachmentIn(Input):
    filename: str = Field(min_length=1, max_length=180)
    content_base64: str = Field(min_length=1, max_length=11_184_812)
    entity: Entity = 'inbox'
    entity_id: int = Field(default=0, ge=0)
    note: str = Field(default='', max_length=300)


class LinkIn(Input):
    entity: Entity
    entity_id: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=500)


def target(db, entity, key):
    if entity == 'inbox':
        if key != 0: raise HTTPException(422, 'Na caixa de recebidos, use identificação zero.')
    else:
        get_or_404(db, ENTITY_MODELS[entity], key)


def file_type(filename, data):
    name = PurePosixPath(filename.replace('\\', '/')).name
    extension = PurePosixPath(name).suffix.lower()
    if extension not in MEDIA or not name or any(ord(c) < 32 for c in name):
        raise HTTPException(422, 'Formato não permitido. Use PDF, imagem, TXT ou áudio compatível.')
    valid = {
        '.pdf': data.startswith(b'%PDF-'), '.png': data.startswith(b'\x89PNG\r\n\x1a\n'),
        '.jpg': data.startswith(b'\xff\xd8\xff'), '.jpeg': data.startswith(b'\xff\xd8\xff'),
        '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP',
        '.mp3': data.startswith(b'ID3') or data[:2] in {b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'},
        '.m4a': len(data) > 12 and data[4:8] == b'ftyp',
        '.ogg': data.startswith(b'OggS'), '.opus': data.startswith(b'OggS'),
        '.wav': data.startswith(b'RIFF') and data[8:12] == b'WAVE', '.txt': True,
    }[extension]
    if extension == '.txt':
        try: data.decode('utf-8-sig')
        except UnicodeDecodeError: valid = False
        if b'\x00' in data: valid = False
    if not valid:
        raise HTTPException(422, 'O conteúdo do arquivo não corresponde ao formato informado.')
    return name, extension


def public(row):
    return {'id': row.id, 'entity': row.entity, 'entity_id': row.entity_id, 'original_name': row.original_name, 'sha256': row.sha256,
            'size_bytes': row.size_bytes, 'note': row.note, 'created_at': row.created_at, 'archived_at': row.archived_at}


@router.get('/attachments/config')
def config():
    return {'entities': ENTITY_LABELS, 'extensions': list(MEDIA), 'max_bytes': MAX_BYTES}


@router.get('/attachments/targets')
def targets(db: DB, entity: Entity):
    if entity == 'inbox': return []
    model = ENTITY_MODELS[entity]
    result = []
    for row in db.scalars(select(model).order_by(model.id.desc()).limit(500)):
        label = getattr(row, 'description', None) or getattr(row, 'name', None) or getattr(row, 'note', None) or f'{ENTITY_LABELS[entity]} #{row.id}'
        result.append({'id': row.id, 'label': f'#{row.id} · {str(label)[:100]}'})
    return result


@router.get('/attachments')
def list_attachments(db: DB, entity: Entity | None = None, entity_id: int | None = None, include_archived: bool = False):
    query = select(Attachment)
    if entity: query = query.where(Attachment.entity == entity)
    if entity_id is not None: query = query.where(Attachment.entity_id == entity_id)
    if not include_archived: query = query.where(Attachment.archived_at.is_(None))
    return [public(row) for row in db.scalars(query.order_by(Attachment.id.desc()).limit(500))]


@router.post('/attachments', status_code=201)
def upload(data: AttachmentIn, db: DB):
    target(db, data.entity, data.entity_id)
    try: content = base64.b64decode(data.content_base64, validate=True)
    except (ValueError, binascii.Error): raise HTTPException(422, 'Conteúdo do arquivo inválido.')
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(422, 'O arquivo precisa ter conteúdo e no máximo 8 MB.')
    name, extension = file_type(data.filename, content); digest = hashlib.sha256(content).hexdigest()
    lock(db, 901)
    if db.scalar(select(Attachment.id).where(Attachment.entity == data.entity, Attachment.entity_id == data.entity_id, Attachment.sha256 == digest, Attachment.archived_at.is_(None))):
        raise HTTPException(409, 'Esse arquivo já está vinculado ao mesmo registro.')
    row = Attachment(entity=data.entity, entity_id=data.entity_id, original_name=name, storage_name=uuid4().hex + extension, sha256=digest, size_bytes=len(content), note=data.note)
    path = storage.attachment_path(row.storage_name)
    created = False; committed = False
    try:
        with path.open('xb') as file:
            created = True
            file.write(content)
            file.flush(); os.fsync(file.fileno())
        db.add(row); db.flush()
        audit(db, 'attachment', row.id, 'stored', {'entity': row.entity, 'entity_id': row.entity_id, 'filename': name, 'sha256': digest})
        db.commit(); committed = True; db.refresh(row)
    except Exception:
        if created and not committed: path.unlink(missing_ok=True)
        raise
    return public(row)


def checked_file(db, key):
    row = get_or_404(db, Attachment, key); path = storage.attachment_path(row.storage_name)
    if not path.is_file():
        raise HTTPException(409, 'Arquivo local indisponível. Recupere-o de um backup que contenha os anexos.')
    content = path.read_bytes()
    if len(content) != row.size_bytes or hashlib.sha256(content).hexdigest() != row.sha256:
        raise HTTPException(409, 'O arquivo local foi alterado ou está incompleto. Use uma cópia íntegra do backup.')
    return row, path


@router.get('/attachments/{key}/download')
def download(key: int, db: DB):
    row, path = checked_file(db, key)
    return FileResponse(path, filename=row.original_name, media_type=MEDIA[path.suffix], headers={'X-Content-Type-Options': 'nosniff'})


@router.get('/attachments/{key}/preview')
def preview(key: int, db: DB):
    row, path = checked_file(db, key)
    if not MEDIA[path.suffix].startswith('image/'):
        raise HTTPException(415, 'Este formato está disponível para download.')
    return FileResponse(path, media_type=MEDIA[path.suffix], headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@router.post('/attachments/{key}/link')
def link(key: int, data: LinkIn, db: DB):
    lock(db, 901); row = get_or_404(db, Attachment, key); target(db, data.entity, data.entity_id)
    if db.scalar(select(Attachment.id).where(Attachment.id != key, Attachment.entity == data.entity, Attachment.entity_id == data.entity_id, Attachment.sha256 == row.sha256, Attachment.archived_at.is_(None))):
        raise HTTPException(409, 'Esse arquivo já está vinculado ao destino informado.')
    audit(db, 'attachment', key, 'linked', {'before': {'entity': row.entity, 'entity_id': row.entity_id}, 'after': data.model_dump()})
    row.entity = data.entity; row.entity_id = data.entity_id; db.commit()
    return public(row)


@router.post('/attachments/{key}/archive')
def archive(key: int, data: ReasonIn, db: DB):
    lock(db, 901)
    row = get_or_404(db, Attachment, key)
    if row.archived_at: raise HTTPException(409, 'Anexo já arquivado.')
    row.archived_at = now(); audit(db, 'attachment', key, 'archived', data.model_dump()); db.commit()
    return public(row)


@router.post('/attachments/{key}/unarchive')
def unarchive(key: int, data: ReasonIn, db: DB):
    lock(db, 901); row = get_or_404(db, Attachment, key)
    if not row.archived_at: raise HTTPException(409, 'Anexo não está arquivado.')
    if db.scalar(select(Attachment.id).where(Attachment.id != key, Attachment.entity == row.entity, Attachment.entity_id == row.entity_id, Attachment.sha256 == row.sha256, Attachment.archived_at.is_(None))):
        raise HTTPException(409, 'Existe outra cópia ativa desse arquivo no mesmo registro.')
    row.archived_at = None; audit(db, 'attachment', key, 'unarchived', data.model_dump()); db.commit()
    return public(row)
