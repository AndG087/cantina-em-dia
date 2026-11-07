import { useEffect } from 'react';
import { DataTable, RecordForm, ModuleHeading, ErrorNote, useRemote, save, localNow, instant, dateTime } from '../components/ui';

export type Employee = { id: number; name: string; role: string; active: boolean };
type Shift = { id: number; employee_id: number; weekday: number; start_time: string; end_time: string; valid_from: string; valid_until: string | null };
type Override = { id: number; employee_id: number; day: string; start_time: string; end_time: string; reason: string };
type Assignment = { id: number; employee_id: number; started_at: string; ended_at: string | null; reason: string };
export type Responsibility = { at: string; closed: boolean; expected: Employee | null; confirmed: Employee | null; confirmed_at: string | null; source: string | null; pending: boolean; previous_assignment_pending: boolean };
const days = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'];
export default function TeamPage() {
  const employees = useRemote<Employee[]>('/employees');
  const shifts = useRemote<{ weekly: Shift[]; overrides: Override[]; closures: { day: string; reason: string }[] }>('/shifts');
  const assignments = useRemote<Assignment[]>('/assignments');
  const responsibility = useRemote<Responsibility>('/cash-responsibility');
  const audit = useRemote<{ id: number; entity: string; action: string; created_at: string; actor: string }[]>('/audit');
  async function refresh() { await Promise.all([employees.refresh(), shifts.refresh(), assignments.refresh(), responsibility.refresh(), audit.refresh()]); }
  useEffect(() => { const timer = setInterval(() => void responsibility.refresh(), 30000); return () => clearInterval(timer); }, [responsibility.refresh]);
  const people = employees.data || [];
  const options = people.filter(p => p.active).map(p => ({ value: p.id, label: p.name }));
  const person = (id: number) => people.find(p => p.id === id)?.name || `Funcionário #${id}`;
  const current = responsibility.data;
  return <><ModuleHeading title="Equipe e caixa" description="Escala automática, confirmação de presença e histórico de responsabilidade." onRefresh={() => void refresh()} /><ErrorNote errors={[employees.error, shifts.error, responsibility.error, assignments.error, audit.error]} />
    <section className="responsibility-grid"><div className="panel stat-box"><span>Responsável previsto agora</span><strong>{current?.closed ? 'Cantina fechada' : current?.expected?.name || 'Sem escala definida'}</strong><small>{current?.source || 'Segunda a sexta, conforme a escala'}</small></div><div className="panel stat-box"><span>Responsável confirmado</span><strong>{current?.confirmed?.name || 'Sem confirmação hoje'}</strong><small>{current?.confirmed_at ? dateTime(current.confirmed_at) : 'A escala não comprova presença'}</small></div><div className="panel stat-box"><span>Situação</span><strong>{current?.previous_assignment_pending ? 'Turno anterior pendente' : current?.pending ? 'Confirmar responsável' : current?.closed ? 'Dia fechado' : current?.confirmed ? 'Confirmado' : 'Aguardando registros'}</strong><small>Atualiza a cada 30 segundos</small></div></section>
    <div className="forms-grid"><RecordForm title="Cadastrar funcionário" fields={[{ name: 'name', label: 'Nome' }, { name: 'role', label: 'Função' }]} onSubmit={v => save('/employees', v, refresh)} />
    <RecordForm title="Alterar funcionário" fields={[{ name: 'id', label: 'Funcionário', options: people.map(p => ({ value: p.id, label: p.name })) }, { name: 'name', label: 'Nome atualizado' }, { name: 'role', label: 'Função' }, { name: 'active', label: 'Funcionário ativo', type: 'checkbox' }]} onSubmit={v => { const { id, ...data } = v; return save(`/employees/${id}`, data, refresh, 'PUT'); }} />
    <RecordForm title="Adicionar escala semanal" fields={[{ name: 'employee_id', label: 'Responsável', options }, { name: 'weekday', label: 'Dia', options: days.map((d, i) => ({ value: i, label: d })) }, { name: 'start_time', label: 'Início', type: 'time' }, { name: 'end_time', label: 'Fim', type: 'time' }, { name: 'valid_from', label: 'Válida a partir de', type: 'date', value: localNow().slice(0, 10) }, { name: 'valid_until', label: 'Válida até (opcional)', type: 'date', required: false }]} onSubmit={v => save('/shifts', { ...v, employee_id: Number(v.employee_id), weekday: Number(v.weekday), valid_until: v.valid_until || null }, refresh)} />
    <RecordForm title="Substituição pontual" fields={[{ name: 'employee_id', label: 'Substituto', options }, { name: 'day', label: 'Data', type: 'date' }, { name: 'start_time', label: 'Início', type: 'time' }, { name: 'end_time', label: 'Fim', type: 'time' }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => save('/shift-overrides', { ...v, employee_id: Number(v.employee_id) }, refresh)} />
    <RecordForm title="Confirmar quem assumiu o caixa" fields={[{ name: 'employee_id', label: 'Funcionário', options }, { name: 'started_at', label: 'Data e hora efetiva', type: 'datetime-local', value: localNow() }, { name: 'reason', label: 'Motivo / informação recebida' }]} onSubmit={v => save('/assignments', { ...v, employee_id: Number(v.employee_id), started_at: instant(v.started_at) }, refresh)} />
    <RecordForm title="Marcar feriado ou dia fechado" fields={[{ name: 'day', label: 'Data', type: 'date' }, { name: 'reason', label: 'Motivo' }]} onSubmit={v => save('/closures', v, refresh)} /></div>
    <DataTable title="Funcionários" rows={people} columns={[{ label: 'Nome', render: r => r.name }, { label: 'Função', render: r => r.role }, { label: 'Situação', render: r => r.active ? 'Ativo' : 'Inativo' }]} />
    <DataTable title="Escala semanal" rows={shifts.data?.weekly || []} columns={[{ label: 'Responsável', render: r => person(r.employee_id) }, { label: 'Dia', render: r => days[r.weekday] }, { label: 'Horário', render: r => `${r.start_time.slice(0, 5)}–${r.end_time.slice(0, 5)}` }, { label: 'Vigência', render: r => `${r.valid_from} até ${r.valid_until || 'indefinido'}` }]} />
    <DataTable title="Substituições" rows={shifts.data?.overrides || []} columns={[{ label: 'Responsável', render: r => person(r.employee_id) }, { label: 'Data', render: r => r.day }, { label: 'Horário', render: r => `${r.start_time.slice(0, 5)}–${r.end_time.slice(0, 5)}` }, { label: 'Motivo', render: r => r.reason }]} />
    <DataTable title="Dias fechados" rows={shifts.data?.closures || []} columns={[{ label: 'Data', render: r => r.day }, { label: 'Motivo', render: r => r.reason }]} />
    <DataTable title="Confirmações e trocas" rows={assignments.data || []} columns={[{ label: 'Responsável', render: r => person(r.employee_id) }, { label: 'Assumiu em', render: r => dateTime(r.started_at) }, { label: 'Passou em', render: r => dateTime(r.ended_at) }, { label: 'Motivo', render: r => r.reason }]} />
    <DataTable title="Histórico de alterações (últimos 300)" rows={audit.data || []} columns={[{ label: 'Quando', render: r => dateTime(r.created_at) }, { label: 'Registro', render: r => r.entity }, { label: 'Ação', render: r => r.action }, { label: 'Autor', render: r => r.actor }]} />
  </>;
}
