"""Calendário da escola: cursos em andamento, feriados, recessos e paralisações.

O sistema não consulta o Senai. O gerente averigua com a escola, registra o que
encontrou e a data da averiguação. Eventos com efeito "fechada" dispensam o caixa no dia.
"""
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import Input, as_dict, get_or_404, now, today, TZ
from .models import SchoolCalendarCheck, SchoolCourse, SchoolEvent

router = APIRouter(prefix='/api', tags=['Calendário da escola'])
DB = Annotated[Session, Depends(get_session)]

SHIFTS = {'morning': 'Manhã', 'afternoon': 'Tarde', 'evening': 'Noite', 'full_day': 'Integral'}
EVENT_KINDS = {'holiday': 'Feriado', 'recess': 'Recesso', 'vacation': 'Férias escolares', 'strike': 'Paralisação / greve', 'school_event': 'Evento da escola', 'other': 'Outro'}
EFFECTS = {'open': 'Funcionamento solicitado (fim de semana)', 'closed': 'Cantina fechada', 'reduced': 'Movimento reduzido', 'normal': 'Sem alteração prevista', 'increased': 'Movimento maior'}
WEEKDAYS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
CHECK_INTERVAL_DAYS = 7


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


class EventIn(Input):
    kind: Literal['holiday', 'recess', 'vacation', 'strike', 'school_event', 'other']
    title: str = Field(min_length=3, max_length=150)
    starts_on: date
    ends_on: date
    effect: Literal['open', 'closed', 'reduced', 'normal', 'increased']
    source: str = Field(min_length=3, max_length=300)
    note: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def check(self):
        if self.ends_on < self.starts_on:
            raise ValueError('A data final deve ser igual ou posterior à inicial.')
        if (self.ends_on - self.starts_on).days > 120:
            raise ValueError('Registre períodos de até 120 dias.')
        return self


class CancelIn(Input):
    reason: str = Field(min_length=3, max_length=500)


class CheckIn(Input):
    source: str = Field(min_length=3, max_length=300)
    note: str = Field(default='', max_length=1000)


def course_dict(course):
    return as_dict(course, shift_label=SHIFTS[course.shift])


def event_dict(event):
    return as_dict(event, kind_label=EVENT_KINDS[event.kind], effect_label=EFFECTS[event.effect])


class CalendarBook:
    """Carrega os cursos e eventos do intervalo uma vez e responde dia a dia."""

    def __init__(self, db, first, last):
        active = SchoolCourse.cancelled_at.is_(None)
        self.courses = db.scalars(select(SchoolCourse).where(active, SchoolCourse.starts_on <= last, SchoolCourse.ends_on >= first).order_by(SchoolCourse.shift, SchoolCourse.name)).all()
        self.events = db.scalars(select(SchoolEvent).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.starts_on <= last, SchoolEvent.ends_on >= first).order_by(SchoolEvent.starts_on)).all()
        self.any_course = db.scalar(select(SchoolCourse.id).where(active).limit(1)) is not None

    def day(self, day):
        weekday = day.weekday()
        events = [e for e in self.events if e.starts_on <= day <= e.ends_on]
        # Sábado e domingo só abrem quando o SENAI solicita (evento com efeito "open").
        weekend_closed = weekday >= 5 and not any(e.effect == 'open' for e in events)
        reasons = ['Fim de semana'] if weekend_closed else []
        status = 'closed' if weekend_closed else 'open'
        for event in events:
            reasons.append(f'{EVENT_KINDS[event.kind]}: {event.title} ({EFFECTS[event.effect].lower()})')
            if event.effect == 'closed':
                status = 'closed'
        if status != 'closed':
            if any(e.effect == 'reduced' for e in events):
                status = 'reduced'
            elif any(e.effect == 'increased' for e in events):
                status = 'increased'
        active = [c for c in self.courses if c.starts_on <= day <= c.ends_on and weekday in c.weekdays]
        known = [c.students for c in active if c.students is not None]
        if status != 'closed' and self.any_course and not active:
            reasons.append('Nenhuma turma cadastrada para este dia: confirme com a escola.')
        return {'day': day, 'weekday': WEEKDAYS[weekday], 'status': status, 'cantina_open': status != 'closed', 'reasons': reasons,
                'courses_by_shift': {key: [c.name for c in active if c.shift == key] for key in SHIFTS}, 'courses_count': len(active),
                'students_estimate': sum(known) if known else None}


def calendar_days(db, first, last):
    book = CalendarBook(db, first, last)
    return [book.day(first + timedelta(days=offset)) for offset in range((last - first).days + 1)]


def last_check(db):
    row = db.scalar(select(SchoolCalendarCheck).order_by(SchoolCalendarCheck.checked_at.desc()).limit(1))
    if not row:
        return None
    age = (today() - row.checked_at.astimezone(TZ).date()).days
    return as_dict(row, age_days=age, overdue=age > CHECK_INTERVAL_DAYS)


def calendar_summary(db, first, days=14):
    last = first + timedelta(days=days - 1)
    window = calendar_days(db, first, last)
    soon = first + timedelta(days=14)
    courses = db.scalars(select(SchoolCourse).where(SchoolCourse.cancelled_at.is_(None), SchoolCourse.ends_on >= first, SchoolCourse.starts_on <= soon).order_by(SchoolCourse.starts_on)).all()
    events = db.scalars(select(SchoolEvent).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.starts_on <= last, SchoolEvent.ends_on >= first).order_by(SchoolEvent.starts_on)).all()
    active = [c for c in courses if c.starts_on <= first]
    return {'start': first, 'end': last, 'days': window, 'events': [event_dict(e) for e in events],
            'active_courses': [course_dict(c) for c in active], 'starting_soon': [course_dict(c) for c in courses if c.starts_on > first],
            'ending_soon': [course_dict(c) for c in active if c.ends_on <= soon],
            'business_days': sum(1 for d in window if d['cantina_open']), 'altered_days': sum(1 for d in window if d['status'] != 'open' and d['day'].weekday() < 5),
            'last_check': last_check(db), 'check_interval_days': CHECK_INTERVAL_DAYS}


def save(db, row):
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.get('/school/courses')
def courses(db: DB):
    return [course_dict(c) for c in db.scalars(select(SchoolCourse).order_by(SchoolCourse.id.desc()))]


@router.post('/school/courses', status_code=201)
def create_course(data: CourseIn, db: DB):
    return course_dict(save(db, SchoolCourse(**data.model_dump())))


@router.put('/school/courses/{key}')
def update_course(key: int, data: CourseIn, db: DB):
    row = get_or_404(db, SchoolCourse, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Curso cancelado. Cadastre um novo registro se a turma voltar.')
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    return course_dict(save(db, row))


@router.post('/school/courses/{key}/cancel')
def cancel_course(key: int, data: CancelIn, db: DB):
    row = get_or_404(db, SchoolCourse, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Curso já cancelado.')
    row.cancelled_at, row.cancel_reason = now(), data.reason
    return course_dict(save(db, row))


@router.get('/school/events')
def events(db: DB):
    return [event_dict(e) for e in db.scalars(select(SchoolEvent).order_by(SchoolEvent.starts_on.desc()))]


@router.post('/school/events', status_code=201)
def create_event(data: EventIn, db: DB):
    if db.scalar(select(SchoolEvent.id).where(SchoolEvent.cancelled_at.is_(None), SchoolEvent.title == data.title, SchoolEvent.starts_on == data.starts_on)):
        raise HTTPException(409, 'Esse evento já está registrado nessa data.')
    return event_dict(save(db, SchoolEvent(**data.model_dump())))


@router.post('/school/events/{key}/cancel')
def cancel_event(key: int, data: CancelIn, db: DB):
    row = get_or_404(db, SchoolEvent, key)
    if row.cancelled_at:
        raise HTTPException(409, 'Evento já cancelado.')
    row.cancelled_at, row.cancel_reason = now(), data.reason
    return event_dict(save(db, row))


@router.get('/school/checks')
def checks(db: DB):
    return db.scalars(select(SchoolCalendarCheck).order_by(SchoolCalendarCheck.checked_at.desc()).limit(100)).all()


@router.post('/school/checks', status_code=201)
def create_check(data: CheckIn, db: DB):
    return save(db, SchoolCalendarCheck(**data.model_dump()))


@router.get('/school/calendar')
def calendar(db: DB, start: date | None = None, days: int = 14):
    if not 1 <= days <= 92:
        raise HTTPException(422, 'Consulte de 1 a 92 dias por vez.')
    return calendar_summary(db, start or today(), days)
