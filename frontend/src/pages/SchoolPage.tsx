import { useState } from 'react';
import { api } from '../api';
import { DataTable, RecordForm, ModuleHeading, ErrorNote, useRemote, save, localNow, dateTime, Composer } from '../components/ui';

type Course = { id: number; name: string; shift: string; shift_label: string; starts_on: string; ends_on: string; weekdays: number[]; students: number | null; source: string; note: string; cancelled_at: string | null; cancel_reason: string };
type SchoolEvent = { id: number; kind: string; kind_label: string; title: string; starts_on: string; ends_on: string; effect: string; effect_label: string; source: string; note: string; cancelled_at: string | null; cancel_reason: string };
type Day = { day: string; weekday: string; status: 'open' | 'closed' | 'reduced' | 'increased'; reasons: string[]; courses_by_shift: Record<string, string[]>; courses_count: number; students_estimate: number | null; students_complete: boolean };
type Check = { id: number; checked_at: string; source: string; note: string; age_days?: number; overdue?: boolean };
type Calendar = { start: string; end: string; days: Day[]; events: SchoolEvent[]; active_courses: Course[]; starting_soon: Course[]; ending_soon: Course[]; business_days: number; altered_days: number; last_check: Check | null; check_interval_days: number };

export const shiftNames: Record<string, string> = { morning: 'Manhã', afternoon: 'Tarde', evening: 'Noite', full_day: 'Integral' };
const kindNames: Record<string, string> = { holiday: 'Feriado', recess: 'Recesso', vacation: 'Férias escolares', strike: 'Paralisação / greve', school_event: 'Evento da escola', other: 'Outro' };
const effectNames: Record<string, string> = { closed: 'Cantina fechada', reduced: 'Movimento reduzido', normal: 'Sem alteração prevista', increased: 'Movimento maior' };
const statusNames: Record<Day['status'], string> = { open: 'Normal', closed: 'Fechada', reduced: 'Reduzido', increased: 'Maior movimento' };
const weekdayNames = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

function WeekdayChecks({ selected = [0, 1, 2, 3, 4] }: { selected?: number[] }) {
  return <fieldset className="weekday-checks"><legend>Dias de aula</legend>{weekdayNames.slice(0, 6).map((name, i) => <label key={name}><input type="checkbox" name="weekday" value={i} defaultChecked={selected.includes(i)} />{name}</label>)}</fieldset>;
}

function courseBody(form: FormData) {
  const weekdays = form.getAll('weekday').map(Number);
  if (!weekdays.length) throw new Error('Marque ao menos um dia de aula.');
  const students = String(form.get('students') || '').trim();
  return { name: form.get('name'), shift: form.get('shift'), starts_on: form.get('starts_on'), ends_on: form.get('ends_on'), weekdays, students: students ? Number(students) : null, source: form.get('source'), note: form.get('note') || '' };
}

function CourseFields() {
  return <div className="operation-fields"><label>Curso / turma<input name="name" required minLength={2} maxLength={150} placeholder="Ex.: Técnico em Mecânica – T2" /></label><label>Turno<select name="shift" required><option value="">Selecione…</option>{Object.entries(shiftNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Início<input name="starts_on" type="date" required /></label><label>Término previsto<input name="ends_on" type="date" required /></label><label>Alunos (aproximado)<input name="students" type="number" min={0} max={5000} step={1} /><small>Opcional. Ajuda a prever o movimento.</small></label><label>Fonte da informação<input name="source" required minLength={3} maxLength={300} placeholder="Ex.: quadro de turmas da secretaria" /></label><label>Observações<input name="note" maxLength={500} /></label><WeekdayChecks /></div>;
}

export default function SchoolPage() {
  const [start, setStart] = useState(localNow().slice(0, 10)); const [span, setSpan] = useState(28);
  const calendar = useRemote<Calendar>(`/school/calendar?start=${start}&days=${span}`);
  const courses = useRemote<Course[]>('/school/courses'); const events = useRemote<SchoolEvent[]>('/school/events'); const checks = useRemote<Check[]>('/school/checks');
  async function refresh() { await Promise.all([calendar.refresh(), courses.refresh(), events.refresh(), checks.refresh()]); }
  const c = calendar.data; const check = c?.last_check;
  const activeCourses = (courses.data || []).filter(x => !x.cancelled_at); const activeEvents = (events.data || []).filter(x => !x.cancelled_at);
  const students = c?.active_courses.reduce((sum, x) => sum + (x.students || 0), 0) || 0;
  // Agrupa os dias úteis por semana, em colunas de segunda a sexta.
  const weeks = new Map<string, (Day | null)[]>();
  for (const d of c?.days || []) {
    const date = new Date(`${d.day}T12:00:00`); const weekday = (date.getDay() + 6) % 7;
    if (weekday > 4) continue;
    const monday = new Date(date); monday.setDate(date.getDate() - weekday);
    const key = monday.toISOString().slice(0, 10);
    if (!weeks.has(key)) weeks.set(key, [null, null, null, null, null]);
    weeks.get(key)![weekday] = d;
  }
  return <><ModuleHeading title="Calendário da escola" description="Cursos em andamento, feriados, recessos e paralisações que mudam o movimento da cantina." onRefresh={() => void refresh()} /><ErrorNote errors={[calendar.error, courses.error, events.error, checks.error]} />
    <div className="responsibility-grid"><div className="panel stat-box"><span>Última averiguação com a escola</span><strong className={!check || check.overdue ? 'warning-text' : ''}>{check ? (check.age_days === 0 ? 'Hoje' : check.age_days === 1 ? 'Ontem' : `Há ${check.age_days} dias`) : 'Ainda não averiguado'}</strong><small>{check ? `${dateTime(check.checked_at)} · ${check.source}` : `Confirme a cada ${c?.check_interval_days || 7} dias`}</small></div><div className="panel stat-box"><span>Cursos em andamento</span><strong>{c?.active_courses.length ?? '—'}</strong><small>{students ? `Cerca de ${students} alunos informados` : 'Informe os alunos para prever o movimento'}</small></div><div className="panel stat-box"><span>Dias úteis com alteração no período</span><strong>{c ? c.altered_days : '—'}</strong><small>{c ? `${c.business_days} dia(s) de funcionamento previsto` : ''}</small></div></div>
    <div className="notice">O sistema não consulta o Senai. Averigue com a secretaria ou coordenação, registre o que mudou e marque a averiguação. Eventos com efeito <strong>cantina fechada</strong> dispensam abertura de caixa e responsável naquele dia.</div>
    <div className="forms-grid"><RecordForm title="Registrar averiguação do calendário" submit="Registrar averiguação" fields={[{ name: 'source', label: 'Com quem / onde conferiu', hint: 'Ex.: secretaria, coordenação, mural, site do Senai' }, { name: 'note', label: 'O que foi confirmado ou mudou', type: 'textarea', required: false }]} onSubmit={v => save('/school/checks', v, refresh)} />
      <RecordForm title="Registrar feriado, recesso ou paralisação" fields={[{ name: 'kind', label: 'Tipo', options: Object.entries(kindNames).map(([value, label]) => ({ value, label })) }, { name: 'title', label: 'Descrição', hint: 'Ex.: Proclamação da República; greve dos docentes' }, { name: 'starts_on', label: 'De', type: 'date' }, { name: 'ends_on', label: 'Até', type: 'date' }, { name: 'effect', label: 'Efeito na cantina', options: Object.entries(effectNames).map(([value, label]) => ({ value, label })) }, { name: 'source', label: 'Fonte da informação' }, { name: 'note', label: 'Observações', required: false }]} onSubmit={v => save('/school/events', v, refresh)} />
      <Composer title="Cadastrar curso ou turma em andamento" onSubmit={async form => { await api('/school/courses', { method: 'POST', body: JSON.stringify(courseBody(form)) }); await refresh(); }}><CourseFields /></Composer>
      <Composer title="Atualizar curso (datas, turno, alunos)" onSubmit={async form => { await api(`/school/courses/${form.get('id')}`, { method: 'PUT', body: JSON.stringify({ ...courseBody(form), reason: form.get('reason') }) }); await refresh(); }}><div className="operation-fields"><label>Curso<select name="id" required><option value="">Selecione…</option>{activeCourses.map(x => <option key={x.id} value={x.id}>{x.name} · {x.shift_label}</option>)}</select><small>Preencha todos os campos com os dados atualizados.</small></label><label>Motivo da alteração<input name="reason" required minLength={3} maxLength={500} /></label></div><CourseFields /></Composer>
      <RecordForm title="Cancelar curso cadastrado" fields={[{ name: 'id', label: 'Curso', options: activeCourses.map(x => ({ value: x.id, label: `${x.name} · ${x.shift_label}` })) }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => save(`/school/courses/${v.id}/cancel`, { reason: v.reason }, refresh)} />
      <RecordForm title="Cancelar feriado ou paralisação" fields={[{ name: 'id', label: 'Evento', options: activeEvents.map(x => ({ value: x.id, label: `${x.title} · ${short(x.starts_on)}` })) }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => save(`/school/events/${v.id}/cancel`, { reason: v.reason }, refresh)} /></div>
    <div className="toolbar"><label>A partir de<input className="toolbar-input" type="date" value={start} onChange={e => { if (e.target.value) setStart(e.target.value); }} /></label><label>Período<select className="toolbar-input" value={span} onChange={e => setSpan(Number(e.target.value))}><option value={14}>2 semanas</option><option value={28}>4 semanas</option><option value={56}>8 semanas</option></select></label></div>
    <section className="panel school-calendar"><h2>Dias úteis previstos</h2><div className="calendar-legend">{Object.entries(statusNames).map(([key, label]) => <span key={key} className={`day-status ${key}`}>{label}</span>)}</div>
      {[...weeks].map(([key, week]) => <div className="calendar-week" key={key}>{week.map((d, i) => !d ? <div key={i} className="calendar-day empty" aria-hidden="true" /> : <article key={d.day} className={`calendar-day ${d.status}`}><header><strong>{d.weekday.slice(0, 3)} {short(d.day)}</strong><span>{statusNames[d.status]}</span></header><p>{d.courses_count ? `${d.courses_count} turma(s)${d.students_estimate ? ` · ~${d.students_estimate} alunos` : ''}` : 'Sem turmas cadastradas'}</p>{Object.entries(d.courses_by_shift).filter(([, names]) => names.length).map(([key, names]) => <small key={key}>{shiftNames[key]}: {names.length}</small>)}{d.reasons.filter(r => !r.startsWith('Fim de semana')).map(r => <em key={r}>{r}</em>)}</article>)}</div>)}
      {!c?.days.length && <p className="empty-cell">Carregando calendário…</p>}</section>
    {c && (c.ending_soon.length > 0 || c.starting_soon.length > 0) && <div className="notice">{c.ending_soon.map(x => <div key={`e${x.id}`}>Termina em {short(x.ends_on)}: <strong>{x.name}</strong> ({x.shift_label.toLowerCase()}).</div>)}{c.starting_soon.map(x => <div key={`s${x.id}`}>Começa em {short(x.starts_on)}: <strong>{x.name}</strong> ({x.shift_label.toLowerCase()}).</div>)}</div>}
    <DataTable title="Cursos e turmas" rows={courses.data || []} columns={[{ label: 'Curso', render: x => x.name }, { label: 'Turno', render: x => x.shift_label }, { label: 'Período', render: x => `${short(x.starts_on)}/${x.starts_on.slice(2, 4)} a ${short(x.ends_on)}/${x.ends_on.slice(2, 4)}` }, { label: 'Dias', render: x => x.weekdays.map(d => weekdayNames[d]).join(', ') }, { label: 'Alunos', render: x => x.students ?? 'Não informado' }, { label: 'Fonte', render: x => x.source }, { label: 'Situação', render: x => x.cancelled_at ? `Cancelado: ${x.cancel_reason}` : x.ends_on < localNow().slice(0, 10) ? 'Encerrado' : x.starts_on > localNow().slice(0, 10) ? 'Previsto' : 'Em andamento' }]} />
    <DataTable title="Feriados, recessos e paralisações" rows={events.data || []} columns={[{ label: 'Período', render: x => x.starts_on === x.ends_on ? short(x.starts_on) : `${short(x.starts_on)} a ${short(x.ends_on)}` }, { label: 'Tipo', render: x => x.kind_label }, { label: 'Descrição', render: x => x.title }, { label: 'Efeito', render: x => <span className={`day-status ${x.effect === 'normal' ? 'open' : x.effect}`}>{x.effect_label}</span> }, { label: 'Fonte', render: x => x.source }, { label: 'Situação', render: x => x.cancelled_at ? `Cancelado: ${x.cancel_reason}` : 'Vigente' }]} />
    <DataTable title="Histórico de averiguações" rows={checks.data || []} columns={[{ label: 'Quando', render: x => dateTime(x.checked_at) }, { label: 'Fonte', render: x => x.source }, { label: 'Observações', render: x => x.note || '—' }]} />
  </>;
}
