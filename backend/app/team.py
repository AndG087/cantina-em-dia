from datetime import date, time, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, audit, aware, get_or_404, lock, now, rows
from .models import Employee, Shift, ShiftOverride, Closure, Assignment, AuditLog

router = APIRouter(prefix="/api", tags=["Equipe e escala"])
DB = Annotated[Session, Depends(get_session)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EmployeeIn(Input):
    name: str = Field(min_length=2, max_length=100)
    role: str = Field(min_length=2, max_length=100)
    active: bool = True


class ShiftIn(Input):
    employee_id: int
    weekday: int = Field(ge=0, le=4)
    start_time: time
    end_time: time
    valid_from: date
    valid_until: date | None = None

    @model_validator(mode="after")
    def interval(self):
        if self.end_time <= self.start_time or (self.valid_until and self.valid_until < self.valid_from):
            raise ValueError("Revise os horários e a vigência da escala.")
        return self


class OverrideIn(Input):
    employee_id: int
    day: date
    start_time: time
    end_time: time
    reason: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def interval(self):
        if self.end_time <= self.start_time:
            raise ValueError("Horário final deve ser posterior ao inicial.")
        return self


class ClosureIn(Input):
    day: date
    reason: str = Field(min_length=3, max_length=300)


class AssignmentIn(Input):
    employee_id: int
    started_at: datetime
    reason: str = Field(min_length=3, max_length=300)


def active_employee(db, key):
    employee = get_or_404(db, Employee, key)
    if not employee.active:
        raise HTTPException(409, "O funcionário está inativo.")
    return employee


@router.get("/employees")
def employees(db: DB):
    return rows(db, Employee)


@router.post("/employees", status_code=201)
def create_employee(data: EmployeeIn, db: DB):
    employee = Employee(**data.model_dump())
    db.add(employee); db.flush()
    audit(db, "employee", employee.id, "created", data.model_dump())
    db.commit(); db.refresh(employee)
    return employee


@router.put("/employees/{key}")
def update_employee(key: int, data: EmployeeIn, db: DB):
    employee = get_or_404(db, Employee, key)
    before = {"name": employee.name, "role": employee.role, "active": employee.active}
    for field, value in data.model_dump().items():
        setattr(employee, field, value)
    audit(db, "employee", key, "updated", {"before": before, "after": data.model_dump()})
    db.commit(); db.refresh(employee)
    return employee


@router.get("/shifts")
def shifts(db: DB):
    return {"weekly": rows(db, Shift), "overrides": rows(db, ShiftOverride), "closures": rows(db, Closure)}


@router.post("/shifts", status_code=201)
def create_shift(data: ShiftIn, db: DB):
    lock(db, 101); active_employee(db, data.employee_id)
    candidates = db.scalars(select(Shift).where(Shift.weekday == data.weekday)).all()
    for existing in candidates:
        periods_overlap = data.valid_from <= (existing.valid_until or date.max) and existing.valid_from <= (data.valid_until or date.max)
        if periods_overlap and data.start_time < existing.end_time and existing.start_time < data.end_time:
            raise HTTPException(409, "Já existe uma escala nesse intervalo. Use uma substituição para exceções pontuais.")
    row = Shift(**data.model_dump()); db.add(row); db.flush()
    audit(db, "shift", row.id, "created", data.model_dump()); db.commit(); db.refresh(row)
    return row


@router.post("/shift-overrides", status_code=201)
def override(data: OverrideIn, db: DB):
    lock(db, 101); active_employee(db, data.employee_id)
    if db.scalar(select(ShiftOverride.id).where(ShiftOverride.day == data.day, ShiftOverride.start_time < data.end_time, ShiftOverride.end_time > data.start_time)):
        raise HTTPException(409, "Existe outra substituição nesse horário.")
    row = ShiftOverride(**data.model_dump()); db.add(row); db.flush()
    audit(db, "override", row.id, "created", data.model_dump()); db.commit(); db.refresh(row)
    return row


@router.post("/closures", status_code=201)
def closure(data: ClosureIn, db: DB):
    lock(db, 101)
    if db.scalar(select(Closure.id).where(Closure.day == data.day)):
        raise HTTPException(409, "Esse dia já está marcado como fechado.")
    row = Closure(**data.model_dump()); db.add(row); db.flush()
    audit(db, "closure", row.id, "created", data.model_dump()); db.commit(); db.refresh(row)
    return row


def assign(db, employee_id, instant, reason):
    lock(db, 102); active_employee(db, employee_id); aware(instant)
    last = db.scalar(select(Assignment).order_by(Assignment.started_at.desc()).limit(1))
    if last:
        if instant <= last.started_at:
            raise HTTPException(409, "A confirmação precisa ser posterior à última troca registrada.")
        if last.ended_at is None:
            last.ended_at = instant
    row = Assignment(employee_id=employee_id, started_at=instant, reason=reason)
    db.add(row); db.flush()
    audit(db, "assignment", row.id, "confirmed", {"employee_id": employee_id, "started_at": instant, "reason": reason})
    return row


@router.post("/assignments", status_code=201)
def confirm(data: AssignmentIn, db: DB):
    from .models import CashSession
    lock(db, 501)
    if db.scalar(select(CashSession.id).where(CashSession.closed_at.is_(None))):
        raise HTTPException(409, 'Há um caixa aberto. Use a passagem com contagem na tela Caixa.')
    row = assign(db, data.employee_id, data.started_at, data.reason)
    db.commit(); db.refresh(row)
    return row


@router.get("/assignments")
def assignments(db: DB):
    return rows(db, Assignment)


@router.get("/cash-responsibility")
def responsibility(db: DB, at: datetime | None = None):
    instant = at or now()
    if instant.tzinfo is None:
        raise HTTPException(422, "Informe o fuso horário.")
    local = instant.astimezone(TZ)
    from .school import closed_by_calendar
    closed = local.weekday() >= 5 or db.scalar(select(Closure.id).where(Closure.day == local.date())) is not None or closed_by_calendar(db, local.date()) is not None
    expected = None
    source = None
    if not closed:
        replacement = db.scalar(select(ShiftOverride).where(ShiftOverride.day == local.date(), ShiftOverride.start_time <= local.time(), ShiftOverride.end_time > local.time()))
        weekly = db.scalars(select(Shift).where(Shift.weekday == local.weekday(), Shift.start_time <= local.time(), Shift.end_time > local.time(), Shift.valid_from <= local.date(), or_(Shift.valid_until.is_(None), Shift.valid_until >= local.date()))).all()
        selected = replacement or (weekly[0] if len(weekly) == 1 else None)
        if selected:
            expected = db.get(Employee, selected.employee_id)
            source = "substituição" if replacement else "escala semanal"
    confirmed = db.scalar(select(Assignment).where(Assignment.started_at <= instant, or_(Assignment.ended_at.is_(None), Assignment.ended_at > instant)).order_by(Assignment.started_at.desc()).limit(1))
    same_day = confirmed and confirmed.started_at.astimezone(TZ).date() == local.date()
    person = db.get(Employee, confirmed.employee_id) if same_day else None
    return {"at": instant, "closed": bool(closed), "expected": expected, "source": source, "confirmed": person, "confirmed_at": confirmed.started_at if same_day else None,
            "pending": not closed and (person is None or (expected and expected.id != person.id)), "previous_assignment_pending": bool(confirmed and not same_day and confirmed.ended_at is None)}


@router.get("/audit")
def history(db: DB):
    return rows(db, AuditLog, 300)
