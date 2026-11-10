"""Peças comuns: fuso horário, datas, valores e validação de entrada."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

TZ = ZoneInfo('America/Sao_Paulo')
Money = Annotated[int, Field(ge=0, le=2_000_000_000)]
Qty = Annotated[Decimal, Field(max_digits=14, decimal_places=3)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return now().astimezone(TZ).date()


def day_start(day: date) -> datetime:
    return datetime.combine(day, time(0), TZ)


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(422, 'Informe data e horário com fuso horário.')
    if value > now() + timedelta(minutes=1):
        raise HTTPException(422, 'A data não pode estar no futuro.')
    return value


def get_or_404(db, model, key):
    row = db.get(model, key)
    if row is None:
        raise HTTPException(404, 'Registro não encontrado.')
    return row


def as_dict(row, **extra) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns} | extra


def brl(cents) -> str:
    value = Decimal(int(cents)) / 100
    text = f'{abs(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{'-' if value < 0 else ''}R$ {text}"


def qty(value) -> str:
    return format(Decimal(str(value)).normalize(), 'f').replace('.', ',')


def ddmm(day: date) -> str:
    return day.strftime('%d/%m')
