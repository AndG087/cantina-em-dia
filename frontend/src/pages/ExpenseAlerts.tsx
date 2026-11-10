import { useEffect, useState } from 'react';
import { RecordForm, useRemote, save, localNow, dateTime, money } from '../components/ui';

type Alert = { key: string; kind: string; kind_label: string; severity: 'high' | 'medium' | 'info'; title: string; detail: string; occurred_at: string; amount_cents: number; reference_cents: number | null; expense_id: number | null; explanation: { note: string; created_at: string } | null };
type Result = { start: string; end: string; alerts: Alert[]; open_count: number; insufficient_history: string[];
  thresholds: { lookback_days: number; min_samples: number; above_usual_pct: number; category_pct: number; category_min_diff_cents: number; unit_cost_pct: number; duplicate_days: number } };
const severityNames = { high: 'Alta', medium: 'Média', info: 'Informativo' };
function shift(iso: string, days: number) { const d = new Date(`${iso}T12:00:00`); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); }

/** Gastos fora do padrão, com explicação registrada pelo gerente. */
export default function ExpenseAlerts({ refreshKey = 0 }: { refreshKey?: number }) {
  const today = localNow().slice(0, 10);
  const [start, setStart] = useState(shift(today, -29)); const [end, setEnd] = useState(today);
  const result = useRemote<Result>(`/expense-alerts?start=${start}&end=${end}`);
  const { refresh } = result;
  useEffect(() => { if (refreshKey) void refresh(); }, [refreshKey, refresh]);
  const data = result.data; const t = data?.thresholds;
  const open = (data?.alerts || []).filter(a => !a.explanation);
  return <section className="panel data-panel expense-alerts"><h2>Gastos fora do padrão<span className={data?.open_count ? 'warning-text' : ''}>{data ? (data.open_count ? `${data.open_count} sem explicação` : 'Nenhum alerta pendente') : 'Carregando…'}</span></h2>
    <div className="toolbar alert-toolbar"><label>De<input className="toolbar-input" type="date" value={start} max={end} onChange={e => { if (e.target.value) setStart(e.target.value); }} /></label><label>Até<input className="toolbar-input" type="date" value={end} min={start} max={today} onChange={e => { if (e.target.value) setEnd(e.target.value); }} /></label></div>
    {result.error && <div className="error-banner" role="alert">{result.error}</div>}
    <div className="alert-cards">{data?.alerts.length ? data.alerts.map(a => <article key={a.key} className={`alert-card ${a.severity} ${a.explanation ? 'explained' : ''}`}><header><span className={`severity ${a.severity}`}>{severityNames[a.severity]}</span><span>{a.kind_label}</span><time>{dateTime(a.occurred_at)}</time></header><strong>{a.title}</strong><p>{a.detail}</p>{a.explanation ? <p className="explanation">Explicação: {a.explanation.note} <small>({dateTime(a.explanation.created_at)})</small></p> : a.severity !== 'info' && <p className="warning-text">Sem explicação registrada.</p>}</article>) : <p className="empty-cell">{data ? 'Nenhum gasto fora do padrão no período, considerando o histórico registrado.' : 'Carregando…'}</p>}</div>
    {open.length > 0 && <div className="forms-grid alert-form"><RecordForm title="Registrar explicação de um alerta" submit="Registrar explicação" fields={[{ name: 'alert_key', label: 'Alerta', options: open.map(a => ({ value: a.key, label: `${a.kind_label} · ${a.title}`.slice(0, 120) })) }, { name: 'note', label: 'Explicação conferida', type: 'textarea', hint: 'Ex.: compra maior para o evento da escola; preço do fornecedor subiu (nota anexada); lançamento duplicado corrigido.' }]} onSubmit={v => save('/expense-alerts/notes', v, result.refresh)} /></div>}
    {t && <div className="notice">Critérios: despesa {t.above_usual_pct}% ou mais acima da mediana da categoria (mínimo de {t.min_samples} lançamentos nos últimos {t.lookback_days} dias); mesmo favorecido e valor em até {t.duplicate_days} dias; despesas manuais de uma categoria {t.category_pct}% acima da média dos períodos anteriores (e ao menos {money(t.category_min_diff_cents)} a mais); custo de compra {t.unit_cost_pct}% acima das últimas compras do item. Um alerta pede conferência; não é prova de erro.{data?.insufficient_history.length ? ` Ainda sem histórico suficiente: ${data.insufficient_history.join(', ')}.` : ''}</div>}
  </section>;
}
