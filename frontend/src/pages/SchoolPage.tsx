import { useState } from 'react';
import { api } from '../api';
import { Badge, DataTable, ErrorNote, FormShell, PageHeading, RecordForm, dateTime, localNow, send, shortDate, useRemote } from '../components/ui';

type Course = { id: number; name: string; shift: string; shift_label: string; starts_on: string; ends_on: string; weekdays: number[]; students: number | null; source: string; cancelled_at: string | null; cancel_reason: string };
type SchoolEvent = { id: number; kind_label: string; title: string; starts_on: string; ends_on: string; effect: string; effect_label: string; source: string; cancelled_at: string | null; cancel_reason: string };
type Day = { day: string; weekday: string; status: 'open' | 'closed' | 'reduced' | 'increased'; reasons: string[]; courses_by_shift: Record<string, string[]>; courses_count: number; students_estimate: number | null };
type Check = { checked_at: string; source: string; note: string; age_days?: number; overdue?: boolean };
type Calendar = { days: Day[]; active_courses: Course[]; starting_soon: Course[]; ending_soon: Course[]; business_days: number; altered_days: number; last_check: Check | null };

const shifts: Record<string, string> = { morning: 'Manhã', afternoon: 'Tarde', evening: 'Noite', full_day: 'Integral' };
const kinds: Record<string, string> = { holiday: 'Feriado', recess: 'Recesso', vacation: 'Férias escolares', strike: 'Paralisação / greve', school_event: 'Evento da escola', other: 'Outro' };
const effects: Record<string, string> = { closed: 'Cantina fechada', reduced: 'Movimento reduzido', normal: 'Sem alteração prevista', increased: 'Movimento maior' };
const statusLook = { open: ['Normal', 'ok'], closed: ['Fechada', 'danger'], reduced: ['Reduzido', 'warn'], increased: ['Maior movimento', 'info'] } as const;
const weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
const options = (map: Record<string, string>) => Object.entries(map).map(([value, label]) => ({ value, label }));

function courseBody(form: HTMLFormElement) {
  const data = new FormData(form);
  const days = data.getAll('weekday').map(Number);
  if (!days.length) throw new Error('Marque ao menos um dia de aula.');
  const students = String(data.get('students') || '').trim();
  return { name: data.get('name'), shift: data.get('shift'), starts_on: data.get('starts_on'), ends_on: data.get('ends_on'), weekdays: days, students: students ? Number(students) : null, source: data.get('source') };
}

function CourseFields({ courses }: { courses?: Course[] }) {
  return <div className="fields">
    {courses && <label>Curso a atualizar<select name="id" required><option value="">Selecione…</option>{courses.map(c => <option key={c.id} value={c.id}>{c.name} · {c.shift_label}</option>)}</select><small>Preencha os demais campos com os dados atualizados.</small></label>}
    <label>Curso / turma<input name="name" required minLength={2} maxLength={150} placeholder="Ex.: Técnico em Mecânica – T2" /></label>
    <label>Turno<select name="shift" required><option value="">Selecione…</option>{options(shifts).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
    <label>Início<input name="starts_on" type="date" required /></label>
    <label>Término previsto<input name="ends_on" type="date" required /></label>
    <label>Alunos (aproximado)<input name="students" type="number" min={0} max={5000} step={1} /><small>Opcional. Ajuda a prever o movimento.</small></label>
    <label>Fonte da informação<input name="source" required minLength={3} maxLength={300} placeholder="Ex.: secretaria" /></label>
    <fieldset className="weekday-checks"><legend>Dias de aula</legend>{weekdays.slice(0, 6).map((name, i) => <label key={name}><input type="checkbox" name="weekday" value={i} defaultChecked={i < 5} />{name}</label>)}</fieldset>
  </div>;
}

export default function SchoolPage() {
  const [start, setStart] = useState(localNow().slice(0, 10)); const [span, setSpan] = useState(28);
  const calendar = useRemote<Calendar>(`/school/calendar?start=${start}&days=${span}`);
  const courses = useRemote<Course[]>('/school/courses'); const events = useRemote<SchoolEvent[]>('/school/events'); const checks = useRemote<Check[]>('/school/checks');
  const refresh = () => Promise.all([calendar.refresh(), courses.refresh(), events.refresh(), checks.refresh()]);
  const c = calendar.data; const check = c?.last_check;
  const activeCourses = (courses.data || []).filter(x => !x.cancelled_at); const activeEvents = (events.data || []).filter(x => !x.cancelled_at);
  const students = c?.active_courses.reduce((sum, x) => sum + (x.students || 0), 0) || 0;
  // Dias úteis agrupados por semana, em colunas de segunda a sexta.
  const weeks = new Map<string, (Day | null)[]>();
  for (const d of c?.days || []) {
    const date = new Date(`${d.day}T12:00:00`); const weekday = (date.getDay() + 6) % 7;
    if (weekday > 4) continue;
    const key = new Date(date.getTime() - weekday * 86400000).toISOString().slice(0, 10);
    if (!weeks.has(key)) weeks.set(key, [null, null, null, null, null]);
    weeks.get(key)![weekday] = d;
  }
  return <>
    <PageHeading title="Calendário da escola" description="Cursos em andamento, feriados e paralisações que mudam o movimento da cantina." onRefresh={() => void refresh()} />
    <ErrorNote errors={[calendar.error, courses.error, events.error, checks.error]} />
    <div className="stat-grid">
      <div className="panel stat"><span>Última averiguação com a escola</span><strong className={!check || check.overdue ? 'warn-text' : ''}>{!check ? 'Ainda não averiguado' : check.age_days === 0 ? 'Hoje' : check.age_days === 1 ? 'Ontem' : `Há ${check.age_days} dias`}</strong><small>{check ? check.source : 'Confirme a cada 7 dias'}</small></div>
      <div className="panel stat"><span>Cursos em andamento</span><strong>{c?.active_courses.length ?? '—'}</strong><small>{students ? `Cerca de ${students} alunos` : 'Informe os alunos para prever o movimento'}</small></div>
      <div className="panel stat"><span>Dias úteis com alteração</span><strong>{c?.altered_days ?? '—'}</strong><small>{c ? `${c.business_days} dia(s) de funcionamento no período` : ''}</small></div>
    </div>
    <div className="notice">O sistema não consulta o Senai: averigue com a secretaria ou coordenação, registre o que mudou e marque a averiguação. Dias com <strong>cantina fechada</strong> não exigem abertura de caixa.</div>
    <div className="forms-grid">
      <RecordForm title="Registrar averiguação do calendário" fields={[{ name: 'source', label: 'Com quem / onde conferiu', hint: 'Ex.: secretaria, coordenação, mural' }, { name: 'note', label: 'O que foi confirmado ou mudou', type: 'textarea', required: false }]} onSubmit={v => send('/school/checks', v, refresh)} />
      <RecordForm title="Registrar feriado, recesso ou paralisação" fields={[{ name: 'kind', label: 'Tipo', options: options(kinds) }, { name: 'title', label: 'Descrição' }, { name: 'starts_on', label: 'De', type: 'date' }, { name: 'ends_on', label: 'Até', type: 'date' }, { name: 'effect', label: 'Efeito na cantina', options: options(effects) }, { name: 'source', label: 'Fonte da informação' }]} onSubmit={v => send('/school/events', v, refresh)} />
      <FormShell title="Cadastrar curso ou turma" onSubmit={async form => { await api('/school/courses', { method: 'POST', body: JSON.stringify(courseBody(form)) }); form.reset(); await refresh(); }}><CourseFields /></FormShell>
      <FormShell title="Atualizar curso" onSubmit={async form => { await api(`/school/courses/${new FormData(form).get('id')}`, { method: 'PUT', body: JSON.stringify(courseBody(form)) }); form.reset(); await refresh(); }}><CourseFields courses={activeCourses} /></FormShell>
      <RecordForm title="Cancelar curso" fields={[{ name: 'id', label: 'Curso', options: activeCourses.map(x => ({ value: x.id, label: `${x.name} · ${x.shift_label}` })) }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => send(`/school/courses/${v.id}/cancel`, { reason: v.reason }, refresh)} />
      <RecordForm title="Cancelar feriado ou paralisação" fields={[{ name: 'id', label: 'Evento', options: activeEvents.map(x => ({ value: x.id, label: `${x.title} · ${shortDate(x.starts_on)}` })) }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => send(`/school/events/${v.id}/cancel`, { reason: v.reason }, refresh)} />
    </div>
    <div className="toolbar"><label>A partir de<input type="date" value={start} onChange={e => e.target.value && setStart(e.target.value)} /></label><label>Período<select value={span} onChange={e => setSpan(Number(e.target.value))}><option value={14}>2 semanas</option><option value={28}>4 semanas</option><option value={56}>8 semanas</option></select></label></div>
    <section className="panel calendar"><h2>Dias úteis previstos</h2>
      {[...weeks].map(([key, week]) => <div className="calendar-week" key={key}>{week.map((d, i) => !d ? <div key={i} className="calendar-day empty" aria-hidden="true" /> : <article key={d.day} className={`calendar-day ${statusLook[d.status][1]}`}>
        <header><strong>{d.weekday.slice(0, 3)} {shortDate(d.day)}</strong><Badge tone={statusLook[d.status][1]}>{statusLook[d.status][0]}</Badge></header>
        <p>{d.courses_count ? `${d.courses_count} turma(s)${d.students_estimate ? ` · ~${d.students_estimate} alunos` : ''}` : 'Sem turmas cadastradas'}</p>
        {Object.entries(d.courses_by_shift).filter(([, names]) => names.length).map(([shift, names]) => <small key={shift}>{shifts[shift]}: {names.length}</small>)}
        {d.reasons.map(r => <em key={r}>{r}</em>)}</article>)}</div>)}
    </section>
    {c && (c.ending_soon.length > 0 || c.starting_soon.length > 0) && <div className="notice">{c.ending_soon.map(x => <div key={`e${x.id}`}>Termina em {shortDate(x.ends_on)}: <strong>{x.name}</strong>.</div>)}{c.starting_soon.map(x => <div key={`s${x.id}`}>Começa em {shortDate(x.starts_on)}: <strong>{x.name}</strong>.</div>)}</div>}
    <DataTable title="Cursos e turmas" rows={courses.data || []} columns={[{ label: 'Curso', render: x => x.name }, { label: 'Turno', render: x => x.shift_label }, { label: 'Período', render: x => `${shortDate(x.starts_on)} a ${shortDate(x.ends_on)}/${x.ends_on.slice(2, 4)}` }, { label: 'Dias', render: x => x.weekdays.map(d => weekdays[d]).join(', ') }, { label: 'Alunos', render: x => x.students ?? '—' }, { label: 'Situação', render: x => x.cancelled_at ? `Cancelado: ${x.cancel_reason}` : x.ends_on < start ? 'Encerrado' : x.starts_on > start ? 'Previsto' : 'Em andamento' }]} />
    <DataTable title="Feriados, recessos e paralisações" rows={events.data || []} columns={[{ label: 'Período', render: x => x.starts_on === x.ends_on ? shortDate(x.starts_on) : `${shortDate(x.starts_on)} a ${shortDate(x.ends_on)}` }, { label: 'Tipo', render: x => x.kind_label }, { label: 'Descrição', render: x => x.title }, { label: 'Efeito', render: x => x.effect_label }, { label: 'Fonte', render: x => x.source }, { label: 'Situação', render: x => x.cancelled_at ? `Cancelado: ${x.cancel_reason}` : 'Vigente' }]} />
    <DataTable title="Averiguações" rows={checks.data || []} columns={[{ label: 'Quando', render: x => dateTime(x.checked_at) }, { label: 'Fonte', render: x => x.source }, { label: 'Observações', render: x => x.note || '—' }]} />
  </>;
}
