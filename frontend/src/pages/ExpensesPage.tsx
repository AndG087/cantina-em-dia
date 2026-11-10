import { useState } from 'react';
import { Badge, DataTable, ErrorNote, PageHeading, RecordForm, cents, dateTime, instant, localNow, money, send, shiftDate, useRemote } from '../components/ui';

type Expense = { id: number; description: string; category: string; amount_cents: number; occurred_at: string; payee: string; document: string; receipt_id: number | null };
type Alert = { key: string; kind_label: string; severity: 'high' | 'medium'; title: string; detail: string; occurred_at: string; explanation: { note: string; created_at: string } | null };
type Alerts = { alerts: Alert[]; open_count: number; criteria: string };

export default function ExpensesPage() {
  const today = localNow().slice(0, 10);
  const [start, setStart] = useState(shiftDate(today, -29)); const [end, setEnd] = useState(today);
  const expenses = useRemote<Expense[]>('/expenses'); const alerts = useRemote<Alerts>(`/expense-alerts?start=${start}&end=${end}`);
  const refresh = () => Promise.all([expenses.refresh(), alerts.refresh()]);
  const unexplained = (alerts.data?.alerts || []).filter(a => !a.explanation);
  return <>
    <PageHeading title="Despesas" description="Lançamento das despesas e identificação de gastos fora do padrão." onRefresh={() => void refresh()} />
    <ErrorNote errors={[expenses.error, alerts.error]} />
    <section className="panel">
      <div className="panel-heading"><h2>Gastos fora do padrão</h2><span className={alerts.data?.open_count ? 'warn-text' : 'muted'}>{alerts.data ? (alerts.data.open_count ? `${alerts.data.open_count} sem explicação` : 'Nenhum pendente') : 'Carregando…'}</span></div>
      <div className="toolbar inset"><label>De<input type="date" value={start} max={end} onChange={e => e.target.value && setStart(e.target.value)} /></label><label>Até<input type="date" value={end} min={start} max={today} onChange={e => e.target.value && setEnd(e.target.value)} /></label></div>
      <div className="alert-cards">{alerts.data?.alerts.length ? alerts.data.alerts.map(a => <article key={a.key} className={`alert-card ${a.explanation ? 'ok' : a.severity === 'high' ? 'danger' : 'warn'}`}>
        <header><Badge tone={a.severity === 'high' ? 'danger' : 'warn'}>{a.kind_label}</Badge><time>{dateTime(a.occurred_at)}</time></header>
        <strong>{a.title}</strong><p>{a.detail}</p>
        {a.explanation ? <p className="success-text">Explicação: {a.explanation.note}</p> : <p className="warn-text">Sem explicação registrada.</p>}
      </article>) : <p className="muted">Nenhum gasto fora do padrão no período, considerando o histórico registrado.</p>}</div>
      <p className="criteria">{alerts.data?.criteria} Um alerta pede conferência; não é prova de erro.</p>
    </section>
    <div className="forms-grid">
      <RecordForm title="Lançar despesa" fields={[{ name: 'description', label: 'Descrição' }, { name: 'category', label: 'Categoria', hint: 'Use sempre os mesmos nomes: Gás, Energia, Limpeza, Manutenção…' }, { name: 'amount', label: 'Valor (R$)', type: 'number', min: '0.01' },
        { name: 'occurred_at', label: 'Data', type: 'datetime-local', value: localNow() }, { name: 'payee', label: 'Pago a' }, { name: 'document', label: 'Nota / comprovante' }]}
        onSubmit={({ amount, ...v }) => send('/expenses', { ...v, amount_cents: cents(amount), occurred_at: instant(v.occurred_at) }, refresh)} />
      <RecordForm title="Explicar um gasto fora do padrão" fields={[{ name: 'alert_key', label: 'Alerta', options: unexplained.map(a => ({ value: a.key, label: `${a.kind_label} · ${a.title}` })) }, { name: 'note', label: 'Explicação conferida', type: 'textarea', hint: 'Ex.: compra maior para evento da escola; preço do fornecedor subiu.' }]} onSubmit={v => send('/expense-alerts/notes', v, refresh)} />
      <RecordForm title="Apagar despesa lançada por engano" fields={[{ name: 'id', label: 'Despesa', options: (expenses.data || []).filter(e => !e.receipt_id).map(e => ({ value: e.id, label: `${e.description} · ${money(e.amount_cents)} · ${dateTime(e.occurred_at)}` })) }]} submit="Apagar" onSubmit={v => send(`/expenses/${v.id}`, undefined, refresh, 'DELETE')} />
    </div>
    <DataTable title="Despesas (últimas 300)" rows={expenses.data || []} columns={[{ label: 'Data', render: e => dateTime(e.occurred_at) }, { label: 'Descrição', render: e => e.description }, { label: 'Categoria', render: e => e.category }, { label: 'Pago a', render: e => e.payee }, { label: 'Documento', render: e => e.document }, { label: 'Valor', render: e => money(e.amount_cents) }]} />
  </>;
}
