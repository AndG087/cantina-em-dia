import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronLeft, ChevronRight, Copy, Download, Printer } from 'lucide-react';
import { api } from '../api';
import { DataTable, ErrorNote, PageHeading, RecordForm, dateTime, localNow, money, send, shiftDate, shortDate, useRemote } from '../components/ui';

type Weekly = { week_start: string; complete_week: boolean; markdown: string; text: string; totals: { sales_cents: number }; previous: { sales_cents: number }; cash_pending_days: number; open_alerts: number; actions: string[] };
type Saved = { id: number; week_start: string; version: number; note: string; created_at: string };

export default function WeeklyReportPage() {
  const today = localNow().slice(0, 10);
  const [week, setWeek] = useState(() => shiftDate(today, -7));
  const report = useRemote<Weekly>(`/reports/weekly?week=${week}`); const saved = useRemote<Saved[]>('/weekly-reports');
  const [archived, setArchived] = useState<{ title: string; markdown: string; text: string } | null>(null);
  const [message, setMessage] = useState('');
  const r = report.data; const markdown = archived?.markdown ?? r?.markdown ?? ''; const text = archived?.text ?? r?.text ?? '';
  const go = (day: string) => { setArchived(null); setWeek(day); };
  async function copy() {
    try { await navigator.clipboard.writeText(text); setMessage('Texto copiado. Cole no WhatsApp.'); }
    catch { setMessage('Não foi possível copiar. Selecione o texto do relatório e copie.'); }
  }
  async function open(row: Saved) {
    const data = await api<{ markdown: string; text: string }>(`/weekly-reports/${row.id}`);
    setArchived({ title: `versão ${row.version} da semana de ${shortDate(row.week_start)}, guardada em ${dateTime(row.created_at)}`, ...data }); window.scrollTo({ top: 0 });
  }
  return <>
    <PageHeading title="Relatório semanal" description="Resumo da semana para enviar aos seus pais: vendas, caixa, compras, estoque, gastos e calendário." onRefresh={() => { void report.refresh(); void saved.refresh(); }} />
    <ErrorNote errors={[report.error, saved.error]} />
    <div className="toolbar no-print">
      <button className="button secondary" aria-label="Semana anterior" onClick={() => go(shiftDate(week, -7))}><ChevronLeft size={16} /></button>
      <label>Qualquer dia da semana<input type="date" value={week} max={today} onChange={e => e.target.value && go(e.target.value)} /></label>
      <button className="button secondary" aria-label="Próxima semana" disabled={shiftDate(week, 7) > today} onClick={() => go(shiftDate(week, 7))}><ChevronRight size={16} /></button>
      <button className="button secondary" onClick={() => window.print()}><Printer size={15} />Imprimir ou PDF</button>
      <button className="button secondary" onClick={() => void copy()}><Copy size={15} />Copiar para WhatsApp</button>
      <a className="button secondary" href={`/api/reports/weekly.md?week=${week}`}><Download size={15} />Baixar .md</a>
    </div>
    {message && <p className="success-text no-print" role="status">{message}</p>}
    {r && !archived && <div className="stat-grid no-print">
      <div className="panel stat"><span>Vendas da semana</span><strong>{money(r.totals.sales_cents)}</strong><small>Semana anterior: {money(r.previous.sales_cents)}</small></div>
      <div className="panel stat"><span>Dias de caixa a conferir</span><strong className={r.cash_pending_days ? 'warn-text' : ''}>{r.cash_pending_days}</strong><small>{r.open_alerts} gasto(s) fora do padrão sem explicação</small></div>
      <div className="panel stat"><span>Pendências</span><strong className={r.actions.length ? 'warn-text' : ''}>{r.actions.length}</strong><small>{r.complete_week ? 'Semana encerrada' : 'Semana em andamento: os números ainda mudam'}</small></div>
    </div>}
    {archived && <div className="notice no-print">Mostrando a {archived.title}. <button className="link-button" onClick={() => setArchived(null)}>Voltar ao relatório atual</button></div>}
    <section className="panel document"><article className="markdown">{markdown ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown> : <p className="muted">Carregando…</p>}</article></section>
    <div className="forms-grid no-print"><RecordForm title="Registrar entrega do relatório" submit="Guardar esta versão" fields={[{ name: 'note', label: 'Para quem enviou, como e quando', type: 'textarea', hint: 'Os números atuais ficam guardados nesta versão.' }]} onSubmit={v => send('/weekly-reports', { week, note: v.note }, saved.refresh)} /></div>
    <div className="no-print"><DataTable title="Relatórios entregues" rows={saved.data || []} columns={[{ label: 'Semana', render: x => `${shortDate(x.week_start)} · v${x.version}` }, { label: 'Guardado em', render: x => dateTime(x.created_at) }, { label: 'Observações', render: x => x.note }, { label: 'Abrir', render: x => <button className="mini-button" onClick={() => void open(x)}>Ver</button> }]} /></div>
  </>;
}
