"""Calendário da escola: cursos em andamento, feriados, recessos e paralisações.

O sistema não consulta o Senai automaticamente. O gerente averigua o calendário com a
escola, registra o que encontrou e a data da averiguação. Os dias com efeito "fechado"
também deixam de exigir responsável e abertura de caixa.
"""
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, audit, get_or_404, lock, now, rows
from .models import Closure, SchoolCalendarCheck, SchoolCourse, SchoolEvent
from .team import Input

router = APIRouter(prefix='/api', tags=['Calendário escolar'])
DB = Annotated[Session, Depends(get_session)]

SHIFTS = {'morning': 'Manhã', 'afternoon': 'Tarde', 'evening': 'Noite', 'full_day': 'Integral'}
EVENT_KINDS = {'holiday': 'Feriado', 'recess': 'Recesso', 'vacation': 'Férias escolares', 'strike': 'Paralisação / greve', 'school_event': 'Evento da escola', 'other': 'Outro'}
EFFECTS = {'closed': 'Cantina fechada', 'reduced': 'Movimento reduzido', 'normal': 'Sem alteração prevista', 'increased': 'Movimento maior'}
WEEKDAYS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
CHECK_INTERVAL_DAYS = 7


def today():
    return now().astimezone(TZ).date()


class CourseIn(Input):
    name: str = Field(min_length=2, max_length=150)
    shift: Literal['morning', 'afternoon', 'evening', 'full_day']
    starts_on: date
    ends_on: date
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7)
    students: int | None = Field(default=None, ge=0, le=5000)
    source: str = Field(min_length=3, max_length=300)
    note: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def check(self):
        if self.ends_on < self.starts_on:
            raise ValueError('A data final do curso deve ser igual ou posterior à inicial.')
        if len(set(self.weekdays)) != len(self.weekdays) or any(d < 0 or d > 6 for d in self.weekdays):
            raise ValueError('Informe dias da semana válidos, sem repetição.')
        self.weekdays = sorted(self.weekdays)
        return self


class CourseUpdateIn(CourseIn):
    reason: str = Field(min_length=3, max_length=500)


class EventIn(Input):
    kind: Literal['holiday', 'recess', 'vacation', 'strike', 'school_event', 'other']
    title: str = Field(min_length=3, max_length=150)
    starts_on: date
    ends_on: date
    effect: Literal['closed', 'reduced', 'normal', 'increased']
    source: str = Field(min_length=3, max_length=300)
    note: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def check(self):
        if self.ends_on < self.starts_on:
            raise ValueError('A data final deve ser igual ou posterior à inicial.')
        if (self.ends_on - self.starts_on).days > 120:
            raise ValueError('Registre períodos de até 120 dias. Divida férias longas em partes.')
        return self


class CancelIn(Input):
    reason: str = Field(min_length=3, max_length=500)


class CheckIn(Input):
    source: str = Field(min_length=3, max_length=300)
    note: str = Field(default='', max_length=1000)


def course_dict(course):
    return {c.name: getattr(course, c.name) for c in SchoolCourse.__table__.columns} | {'shift_label': SHIFTS[course.shift]}


def event_dict(event):
    return {c.name: getattr(event, c.name) for c in SchoolEvent.__table__.columns} | {'kind_label': EVENT_KINDS[event.kind], 'effect_label': EFFECTS[event.effect]}


def closed_by_calendar(db, day):
    """Título do evento escolar que fecha a cantina no dia, se houver."""
    return db.scalar(select(SchoolEvent.title).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.effect == 'closed',
                                                     SchoolEvent.starts_on <= day, SchoolEvent.ends_on >= day).order_by(SchoolEvent.id).limit(1))


class CalendarBook:
    """Carrega uma vez os registros do intervalo e responde dia a dia."""

    def __init__(self, db, first, last):
        self.courses = db.scalars(select(SchoolCourse).where(SchoolCourse.cancelled_at.is_(None), SchoolCourse.starts_on <= last, SchoolCourse.ends_on >= first).order_by(SchoolCourse.shift, SchoolCourse.name)).all()
        self.events = db.scalars(select(SchoolEvent).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.starts_on <= last, SchoolEvent.ends_on >= first).order_by(SchoolEvent.starts_on, SchoolEvent.id)).all()
        self.closures = {c.day: c.reason for c in db.scalars(select(Closure).where(Closure.day >= first, Closure.day <= last))}
        self.any_course = db.scalar(select(SchoolCourse.id).where(SchoolCourse.cancelled_at.is_(None)).limit(1)) is not None

    def day(self, day):
        weekday = day.weekday()
        events = [e for e in self.events if e.starts_on <= day <= e.ends_on]
        reasons = []; status = 'open'
        if weekday >= 5:
            status = 'closed'; reasons.append('Fim de semana')
        if day in self.closures:
            status = 'closed'; reasons.append(f'Dia fechado: {self.closures[day]}')
        for event in events:
            if event.effect == 'closed':
                status = 'closed'
            reasons.append(f'{EVENT_KINDS[event.kind]}: {event.title} ({EFFECTS[event.effect].lower()})')
        if status != 'closed':
            if any(e.effect == 'reduced' for e in events):
                status = 'reduced'
            elif any(e.effect == 'increased' for e in events):
                status = 'increased'
        active = [c for c in self.courses if c.starts_on <= day <= c.ends_on and weekday in c.weekdays]
        by_shift = {key: [c.name for c in active if c.shift == key] for key in SHIFTS}
        known = [c.students for c in active if c.students is not None]
        if status in {'open', 'increased'} and self.any_course and not active:
            reasons.append('Nenhuma turma cadastrada para este dia: confirme com a escola.')
        return {'day': day, 'weekday': WEEKDAYS[weekday], 'status': status, 'cantina_open': status != 'closed', 'reasons': reasons,
                'events': [e.id for e in events], 'courses_by_shift': by_shift, 'courses_count': len(active),
                'students_estimate': sum(known) if known else None, 'students_complete': len(known) == len(active)}


def calendar_days(db, first, last):
    book = CalendarBook(db, first, last)
    result = []; day = first
    while day <= last:
        result.append(book.day(day)); day += timedelta(days=1)
    return result


def last_check(db):
    row = db.scalar(select(SchoolCalendarCheck).order_by(SchoolCalendarCheck.checked_at.desc(), SchoolCalendarCheck.id.desc()).limit(1))
    if not row:
        return None
    age = (today() - row.checked_at.astimezone(TZ).date()).days
    return {'id': row.id, 'checked_at': row.checked_at, 'source': row.source, 'note': row.note, 'age_days': age, 'overdue': age > CHECK_INTERVAL_DAYS}


def calendar_summary(db, first, days=14):
    last = first + timedelta(days=days - 1)
    window = calendar_days(db, first, last)
    soon = first + timedelta(days=14)
    active = db.scalars(select(SchoolCourse).where(SchoolCourse.cancelled_at.is_(None), SchoolCourse.starts_on <= first, SchoolCourse.ends_on >= first).order_by(SchoolCourse.shift, SchoolCourse.name)).all()
    starting = db.scalars(select(SchoolCourse).where(SchoolCourse.cancelled_at.is_(None), SchoolCourse.starts_on > first, SchoolCourse.starts_on <= soon).order_by(SchoolCourse.starts_on)).all()
    ending = [c for c in active if c.ends_on <= soon]
    events = db.scalars(select(SchoolEvent).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.starts_on <= last, SchoolEvent.ends_on >= first).order_by(SchoolEvent.starts_on, SchoolEvent.id)).all()
    return {'start': first, 'end': last, 'days': window, 'events': [event_dict(e) for e in events],
            'active_courses': [course_dict(c) for c in active], 'starting_soon': [course_dict(c) for c in starting], 'ending_soon': [course_dict(c) for c in ending],
            'business_days': sum(1 for d in window if d['cantina_open']), 'altered_days': sum(1 for d in window if d['status'] != 'open' and d['day'].weekday() < 5),
            'last_check': last_check(db), 'check_interval_days': CHECK_INTERVAL_DAYS}


@router.get('/school/courses')
def courses(db: DB):
    return [course_dict(c) for c in rows(db, SchoolCourse, 1000)]


@router.post('/school/courses', status_code=201)
def create_course(data: CourseIn, db: DB):
    lock(db, 1101)
    row = SchoolCourse(**data.model_dump()); db.add(row); db.flush()
    audit(db, 'school_course', row.id, 'created', data.model_dump()); db.commit(); db.refresh(row)
    return course_dict(row)


@router.put('/school/courses/{key}')
def update_course(key: int, data: CourseUpdateIn, db: DB):
    lock(db, 1101); row = get_or_404(db, SchoolCourse, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Curso cancelado. Cadastre um novo registro se a turma voltar.')
    values = data.model_dump(exclude={'reason'})
    before = {field: getattr(row, field) for field in values}
    for field, value in values.items():
        setattr(row, field, value)
    audit(db, 'school_course', key, 'updated', {'before': before, 'after': values, 'reason': data.reason}); db.commit(); db.refresh(row)
    return course_dict(row)


@router.post('/school/courses/{key}/cancel')
def cancel_course(key: int, data: CancelIn, db: DB):
    lock(db, 1101); row = get_or_404(db, SchoolCourse, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Curso já cancelado.')
    row.cancelled_at = now(); row.cancel_reason = data.reason
    audit(db, 'school_course', key, 'cancelled', data.model_dump()); db.commit(); db.refresh(row)
    return course_dict(row)


@router.get('/school/events')
def events(db: DB):
    return [event_dict(e) for e in rows(db, SchoolEvent, 1000)]


@router.post('/school/events', status_code=201)
def create_event(data: EventIn, db: DB):
    lock(db, 1101)
    duplicate = db.scalar(select(SchoolEvent.id).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.title == data.title, SchoolEvent.starts_on == data.starts_on, SchoolEvent.ends_on == data.ends_on))
    if duplicate:
        raise HTTPException(409, 'Esse evento já está registrado no mesmo período.')
    row = SchoolEvent(**data.model_dump()); db.add(row); db.flush()
    audit(db, 'school_event', row.id, 'created', data.model_dump()); db.commit(); db.refresh(row)
    return event_dict(row)


@router.post('/school/events/{key}/cancel')
def cancel_event(key: int, data: CancelIn, db: DB):
    lock(db, 1101); row = get_or_404(db, SchoolEvent, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Evento já cancelado.')
    row.cancelled_at = now(); row.cancel_reason = data.reason
    audit(db, 'school_event', key, 'cancelled', data.model_dump()); db.commit(); db.refresh(row)
    return event_dict(row)


@router.get('/school/checks')
def checks(db: DB):
    return rows(db, SchoolCalendarCheck, 200)


@router.post('/school/checks', status_code=201)
def create_check(data: CheckIn, db: DB):
    row = SchoolCalendarCheck(**data.model_dump()); db.add(row); db.flush()
    audit(db, 'school_calendar', row.id, 'checked', data.model_dump()); db.commit(); db.refresh(row)
    return row


@router.get('/school/calendar')
def calendar(db: DB, start: date | None = None, days: int = 14):
    if days < 1 or days > 92:
        raise HTTPException(422, 'Consulte de 1 a 92 dias por vez.')
    return calendar_summary(db, start or today(), days)
