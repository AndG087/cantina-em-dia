from datetime import datetime, timezone, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.orm import Session

TZ = ZoneInfo("America/Sao_Paulo")


def now():
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(422, "Informe data e horário com fuso horário.")
    if value > now().replace(microsecond=0) + timedelta(minutes=1):
        raise HTTPException(422, "A ocorrência não pode estar no futuro.")
    return value


def get_or_404(session, model, key):
    row = session.get(model, key)
    if row is None:
        raise HTTPException(404, "Registro não encontrado.")
    return row


def lock(session: Session, key: int):
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def audit(session: Session, entity: str, key, action: str, details: dict):
    from .models import AuditLog
    session.add(AuditLog(entity=entity, entity_id=str(key), action=action, details=jsonable_encoder(details)))


def rows(session, model, limit=500):
    return session.scalars(select(model).order_by(model.id.desc()).limit(limit)).all()


def quantity(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"))


def brl(cents) -> str:
    """Formata centavos como moeda brasileira, para mensagens e relatórios."""
    value = Decimal(int(cents)) / 100
    text = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if value < 0 else ''}R$ {text}"
