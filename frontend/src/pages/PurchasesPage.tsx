import { useState } from 'react';
import { api } from '../api';
import { Badge, DataTable, ErrorNote, FormShell, LinesInput, PageHeading, RecordForm, cents, count, dateTime, emptyLine, instant, localNow, money, send, useRemote } from '../components/ui';
import type { LineDraft } from '../components/ui';
import type { Item } from './StockPage';

type Supplier = { id: number; name: string };
type Purchase = { id: number; supplier_id: number; requested_by: string; status: string };
type Receipt = { id: number; document: string; supplier: string; purchase_id: number; occurred_at: string; total_cents: number; invoice_total_cents: number; invoice_difference_cents: number; issues: string[]; ok: boolean;
  lines: { name: string; unit: string; quantity: string; unit_cost_cents: number; cost_variation_pct: number | null }[] };
type Checks = { receipts: Receipt[]; pending_orders: { id: number; supplier: string; requested_by: string; created_at: string; missing: { name: string; unit: string; missing: string }[] }[]; cost_tolerance_pct: number };

const toLines = (lines: LineDraft[]) => lines.map(l => ({ item_id: Number(l.item_id), quantity: l.quantity, unit_cost_cents: cents(l.price) }));

export default function PurchasesPage() {
  const suppliers = useRemote<Supplier[]>('/suppliers'); const purchases = useRemote<Purchase[]>('/purchases');
  const items = useRemote<Item[]>('/items'); const checks = useRemote<Checks>('/purchase-receipts');
  const [orderLines, setOrderLines] = useState<LineDraft[]>([emptyLine()]);
  const [receiptLines, setReceiptLines] = useState<LineDraft[]>([emptyLine()]);
  const refresh = () => Promise.all([suppliers.refresh(), purchases.refresh(), items.refresh(), checks.refresh()]);
  const supplierName = (id: number) => suppliers.data?.find(s => s.id === id)?.name || `#${id}`;
  const itemOptions = (items.data || []).filter(i => i.active).map(i => ({ value: i.id, label: `${i.name} (${i.unit})` }));
  const open = (purchases.data || []).filter(p => p.status === 'open' || p.status === 'partial').map(p => ({ value: p.id, label: `#${p.id} · ${supplierName(p.supplier_id)} · ${p.requested_by}` }));
  const itemsTotal = receiptLines.reduce((sum, l) => { try { return sum + Math.round(Number(l.quantity || 0) * cents(l.price)); } catch { return sum; } }, 0);
  const tolerance = checks.data?.cost_tolerance_pct ?? 10;
  return <>
    <PageHeading title="Compras e notas" description="Pedido ao fornecedor, recebimento com a nota e conferência de valores, quantidades e custos." onRefresh={() => void refresh()} />
    <ErrorNote errors={[suppliers.error, purchases.error, items.error, checks.error]} />
    <div className="forms-grid">
      <RecordForm title="Cadastrar fornecedor" fields={[{ name: 'name', label: 'Fornecedor' }]} onSubmit={v => send('/suppliers', v, refresh)} />
      <FormShell title="Fazer pedido de compra" onSubmit={async form => {
        const data = new FormData(form);
        await api('/purchases', { method: 'POST', body: JSON.stringify({ supplier_id: Number(data.get('supplier_id')), requested_by: data.get('requested_by'), note: data.get('note') || '', lines: toLines(orderLines) }) });
        form.reset(); setOrderLines([emptyLine()]); await refresh();
      }}><div className="fields"><label>Fornecedor<select name="supplier_id" required><option value="">Selecione…</option>{(suppliers.data || []).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Pedido por<input name="requested_by" required minLength={2} maxLength={100} /></label><label>Observações<input name="note" maxLength={500} /></label></div>
        <LinesInput value={orderLines} onChange={setOrderLines} options={itemOptions} priceLabel="Custo estimado por unidade (R$)" /></FormShell>
      <FormShell title="Receber mercadorias com a nota" onSubmit={async form => {
        const data = new FormData(form);
        await api(`/purchases/${data.get('purchase_id')}/receive`, { method: 'POST', body: JSON.stringify({ document: data.get('document'), occurred_at: instant(data.get('occurred_at')), invoice_total_cents: cents(data.get('invoice_total')), invoice_note: data.get('invoice_note') || '', lines: toLines(receiptLines) }) });
        form.reset(); setReceiptLines([emptyLine()]); await refresh();
      }}><div className="fields"><label>Pedido<select name="purchase_id" required><option value="">Selecione…</option>{open.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label><label>Número da nota<input name="document" required maxLength={120} /></label>
        <label>Recebido em<input name="occurred_at" type="datetime-local" defaultValue={localNow()} required /></label>
        <label>Valor total impresso na nota (R$)<input name="invoice_total" type="number" min="0" step="0.01" required /><small>Soma dos itens abaixo: {money(itemsTotal)}.</small></label>
        <label>Explicação, se a nota não bater com os itens<input name="invoice_note" maxLength={500} placeholder="Desconto, frete, item faltante…" /></label></div>
        <LinesInput value={receiptLines} onChange={setReceiptLines} options={itemOptions} priceLabel="Custo real por unidade (R$)" /></FormShell>
      <RecordForm title="Encerrar pedido sem receber o restante" fields={[{ name: 'id', label: 'Pedido', options: open }, { name: 'reason', label: 'Motivo', hint: 'Ex.: fornecedor sem o item; comprado em outro lugar' }]} onSubmit={v => send(`/purchases/${v.id}/close`, { reason: v.reason }, refresh)} />
    </div>
    <div className="notice">Na conferência, compare a nota com o que chegou. O sistema exige explicação quando a nota não bate com a soma dos itens e aponta custo {tolerance}% ou mais acima do estimado no pedido.</div>
    <DataTable title="Conferência das notas" rows={checks.data?.receipts || []} columns={[
      { label: 'Nota', render: r => <><strong>{r.document}</strong><div className="muted">{r.supplier} · pedido #{r.purchase_id} · {dateTime(r.occurred_at)}</div></> },
      { label: 'Itens recebidos', render: r => r.lines.map(l => <div key={l.name}>{l.name}: {count(l.quantity)} {l.unit} × {money(l.unit_cost_cents)}{l.cost_variation_pct ? <span className={l.cost_variation_pct >= tolerance ? 'danger-text' : 'muted'}> ({l.cost_variation_pct > 0 ? '+' : ''}{l.cost_variation_pct}%)</span> : null}</div>) },
      { label: 'Soma dos itens', render: r => money(r.total_cents) }, { label: 'Valor da nota', render: r => money(r.invoice_total_cents) },
      { label: 'Situação', render: r => <><Badge tone={r.ok ? 'ok' : 'warn'}>{r.ok ? 'Conferida' : 'Divergência'}</Badge>{r.issues.length > 0 && <ul className="issue-list">{r.issues.map(i => <li key={i}>{i}</li>)}</ul>}</> },
    ]} />
    <DataTable title="Pedidos com itens a receber" rows={checks.data?.pending_orders || []} columns={[{ label: 'Pedido', render: p => `#${p.id} · ${dateTime(p.created_at)}` }, { label: 'Fornecedor', render: p => p.supplier }, { label: 'Pedido por', render: p => p.requested_by }, { label: 'Falta receber', render: p => p.missing.map(m => `${m.name}: ${count(m.missing)} ${m.unit}`).join('; ') }]} />
  </>;
}
