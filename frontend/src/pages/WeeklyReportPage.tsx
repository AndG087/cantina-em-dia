import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronLeft, ChevronRight, Copy, Download, Printer } from 'lucide-react';
import { api } from '../api';
import { DataTable, RecordForm, ModuleHeading, ErrorNote, useRemote, save, localNow, dateTime, money } from '../components/ui';

type Weekly = { week_start: string; week_end: string; label: string; complete_week: boolean; markdown: string; text: string; sales: { current: number; previous: number; variation_pct: number | null };
  current: { sales_count: number; all_expenses_cents: number }; cash_pending_days: number; cash_reviewed_days: number; open_alerts: number; actions: string[] };
type Saved = { id: number; week_start: string; version: number; note: string; created_at: string; complete_week: boolean; sales_cents: number | null; actions: number };

function shift(iso: string, days: number) { const d = new Date(`${iso}T12:00:00`); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); }
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

export default function WeeklyReportPage() {
  const [week, setWeek] = useState(() => shift(localNow().slice(0, 10), -7));
  const report = useRemote<Weekly>(`/reports/weekly?week=${week}`); const saved = useRemote<Saved[]>('/weekly-reports');
  const [archived, setArchived] = useState<{ id: number; title: string; markdown: string; text: string } | null>(null);
  const [message, setMessage] = useState('');
  async function refresh() { await Promise.all([report.refresh(), saved.refresh()]); }
  const r = report.data; const shown = archived?.markdown ?? r?.markdown ?? '';
  const text = archived?.text ?? r?.text ?? '';
  async function copy() {
    try { await navigator.clipboard.writeText(text); setMessage('Texto copiado. Cole no WhatsApp ou no e-mail.'); }
    catch { setMessage('Não foi possível copiar automaticamente. Selecione o texto do relatório e copie.'); }
  }
  async function open(row: Saved) {
    try { const data = await api<{ markdown: string; text: string }>(`/weekly-reports/${row.id}`); setArchived({ id: row.id, title: `Versão ${row.version} entregue em ${dateTime(row.created_at)}`, ...data }); window.scrollTo({ top: 0 }); }
    catch (e) { setMessage(e instanceof Error ? e.message : 'Não foi possível abrir a versão salva.'); }
  }
  const variation = r?.sales.variation_pct;
  return <><ModuleHeading title="Relatório semanal" description="Resumo da semana para a gestão: vendas, caixa, compras, estoque, gastos e calendário da escola." onRefresh={() => void refresh()} /><ErrorNote errors={[report.error, saved.error]} />
    <div className="toolbar no-print"><button className="button secondary" onClick={() => { setArchived(null); setWeek(shift(week, -7)); }} aria-label="Semana anterior"><ChevronLeft size={15} /></button><label>Qualquer dia da semana<input className="toolbar-input" type="date" value={week} max={localNow().slice(0, 10)} onChange={e => { if (e.target.value) { setArchived(null); setWeek(e.target.value); } }} /></label><button className="button secondary" disabled={shift(week, 7) > localNow().slice(0, 10)} onClick={() => { setArchived(null); setWeek(shift(week, 7)); }} aria-label="Próxima semana"><ChevronRight size={15} /></button>
      <button className="button secondary" onClick={() => window.print()} disabled={!shown}><Printer size={15} />Imprimir ou salvar PDF</button><button className="button secondary" onClick={() => void copy()} disabled={!text}><Copy size={15} />Copiar texto para WhatsApp</button><a className="button secondary" href={`/api/reports/weekly.md?week=${week}`}><Download size={15} />Baixar .md</a></div>
    {message && <p className="success-message no-print" role="status">{message}</p>}
    {r && !archived && <div className="responsibility-grid no-print"><div className="panel stat-box"><span>Vendas da semana</span><strong>{money(r.sales.current)}</strong><small>{r.current.sales_count} pedido(s) · {variation == null ? 'sem base na semana anterior' : `${variation > 0 ? '+' : ''}${variation.toLocaleString('pt-BR')}% vs. semana anterior`}</small></div><div className="panel stat-box"><span>Caixa conferido</span><strong className={r.cash_pending_days ? 'warning-text' : ''}>{r.cash_reviewed_days} dia(s)</strong><small>{r.cash_pending_days ? `${r.cash_pending_days} dia(s) aguardando conferência` : 'Nenhum dia pendente'}</small></div><div className="panel stat-box"><span>Pendências listadas</span><strong className={r.actions.length ? 'warning-text' : ''}>{r.actions.length}</strong><small>{r.open_alerts} gasto(s) fora do padrão sem explicação</small></div></div>}
    {r && !r.complete_week && !archived && <div className="notice no-print">Semana em andamento: os números ainda vão mudar. Para entregar, use a semana encerrada ou registre como prévia.</div>}
    {archived && <div className="notice no-print">Mostrando a {archived.title}. <button className="text-button" onClick={() => setArchived(null)}>Voltar ao relatório atual</button></div>}
    <section className="panel document-view" id="print-document">{shown ? <article className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{shown}</ReactMarkdown></article> : <p className="empty-cell">Carregando relatório…</p>}</section>
    <div className="forms-grid no-print"><RecordForm title="Registrar entrega do relatório" submit="Guardar esta versão" successMessage="Versão guardada no histórico." fields={[{ name: 'note', label: 'Para quem enviou, como e observações', type: 'textarea', hint: 'Ex.: enviado ao meu pai pelo WhatsApp em 10/11. O retrato atual dos números fica guardado.' }]} onSubmit={v => save('/weekly-reports', { week, note: v.note }, refresh)} /></div>
    <div className="no-print"><DataTable title="Relatórios entregues" rows={saved.data || []} columns={[{ label: 'Semana', render: x => `${short(x.week_start)} · v${x.version}${x.complete_week === false ? ' (prévia)' : ''}` }, { label: 'Guardado em', render: x => dateTime(x.created_at) }, { label: 'Vendas', render: x => x.sales_cents == null ? '—' : money(x.sales_cents) }, { label: 'Pendências', render: x => x.actions }, { label: 'Observações', render: x => x.note }, { label: 'Abrir', render: x => <button className="mini-action" onClick={() => void open(x)}>Ver versão</button> }]} /></div>
  </>;
}
