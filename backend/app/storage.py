"""Arquivos locais imutáveis, separados do código e do diretório do PostgreSQL."""
import os
import re
from pathlib import Path

from fastapi import HTTPException
from .config import settings

DATA_ROOT = Path(settings.cantina_data_dir or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CantinaEmDia').resolve()


def directory(name: str) -> Path:
    if name not in {'attachments', 'backups'}:
        raise ValueError('Diretório de armazenamento inválido.')
    result = DATA_ROOT / name
    result.mkdir(parents=True, exist_ok=True)
    return result.resolve()


def attachment_path(name: str) -> Path:
    if not re.fullmatch(r'[a-f0-9]{32}\.(pdf|png|jpe?g|webp|txt|mp3|m4a|ogg|opus|wav)', name):
        raise HTTPException(409, 'Identificação do arquivo local inválida.')
    parent = directory('attachments')
    result = (parent / name).resolve()
    if not result.is_relative_to(parent):
        raise HTTPException(409, 'O arquivo não pertence ao armazenamento do aplicativo.')
    return result


def backup_path(name: str) -> Path:
    if not re.fullmatch(r'cantina-[0-9]{8}T[0-9]{6}-[a-f0-9]{12}\.zip', name):
        raise HTTPException(409, 'Identificação do backup inválida.')
    parent = directory('backups')
    result = (parent / name).resolve()
    if not result.is_relative_to(parent):
        raise HTTPException(409, 'O backup não pertence ao armazenamento do aplicativo.')
    return result
