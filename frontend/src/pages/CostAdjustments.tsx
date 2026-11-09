import { useState } from 'react';
import { api } from '../api';
import { DataTable, ErrorNote, RecordForm, dateTime, money, useRemote } from '../components/ui';

type Lot = { id: number; item_id: number; code: string; unit_cost_cents: string; original_unit_cost_cents: string; balance: string; produced: boolean; cost_known: boolean };
type Payload = { lot_id: number; unit_cost_cents: string; confirmed: boolean; document: string; reason: string };
type Preview = { lot_id: number; previous_cost_cents: string; unit_cost_cents: string; expected_fingerprint: string; sales: { id: number; before_cents: number; after_cents: number }[]; productions: { id: number; before_cents: number; after_cents: number }[]; earliest_affected_at: string; purchase_linked: boolean };
type Revision = { id: number; lot_id: number; previous_cost_cents: string; unit_cost_cents: string; document: string; reason: string; created_at: string };
const preciseCost = (value: string) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 8 }).format(Number(value) / 100);
export default function CostAdjustments({ names }: { names: { id: number; name: string }[] }) {
  const lots = useRemote<Lot[]>('/stock-lots?include_empty=true'); const revisions = useRemote<Revision[]>('/cost-revisions');
  const [preview, setPreview] = useState<{ request: Payload; result: Preview } | null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [message, setMessage] = useState('');
  const name = (lot: Lot) => names.find(i => i.id === lot.item_id)?.name || `Item #${lot.item_id}`;
  async function refresh() { await Promise.all([lots.refresh(), revisions.refresh()]); }
  async function confirm() {
    if (!preview) return;
    setBusy(true); setError('');
    try {
      await api('/cost-revisions', { method: 'POST', body: JSON.stringify({ ...preview.request, expected_fingerprint: preview.result.expected_fingerprint }) });
      setPreview(null); setMessage('Correção registrada. Confira novamente os relatórios dos períodos afetados.'); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível confirmar.'); }
    finally { setBusy(false); }
  }
  const p = preview?.result;
  return <><h2>Correção do custo gerencial</h2><ErrorNote errors={[lots.error, revisions.error, error]} />
    <div className="notice">Use para corrigir ou confirmar o custo de um lote, inclusive já consumido. Os relatórios recalculam as vendas, perdas e produções relacionadas. Os valores originalmente registrados e as apurações guardadas permanecem preservados. Esta operação não altera notas, despesas, pagamentos nem a quantidade em estoque.</div>
    <RecordForm title="Preparar correção de custo" submit="Conferir impacto sem gravar" successMessage="Prévia preparada. Confira os dados abaixo antes de confirmar." fields={[
      { name: 'lot_id', label: 'Lote de entrada (inclui lotes sem saldo)', options: (lots.data || []).filter(l => !l.produced).map(l => ({ value: l.id, label: `#${l.id} · ${name(l)} · ${l.code} · saldo ${l.balance}` })) },
      { name: 'cost', label: 'Custo correto em R$ por unidade de controle do item', type: 'number', min: 0, step: '0.000001', hint: 'Para kg, informe o custo por kg; para un, o custo de uma unidade. Não informe o valor total da nota.' },
      { name: 'confirmed', label: 'Conferi o custo no documento, inclusive se for zero', type: 'checkbox' },
      { name: 'document', label: 'Documento que confirma o custo' }, { name: 'reason', label: 'Motivo da correção', type: 'textarea' },
    ]} onSubmit={async v => {
      setPreview(null); setMessage(''); setError('');
      const raw = String(v.cost).replace(',', '.'); if (!/^\d+(\.\d{1,6})?$/.test(raw)) throw new Error('Informe um custo válido com até seis casas decimais em reais.');
      const request = { lot_id: Number(v.lot_id), unit_cost_cents: (Number(raw) * 100).toFixed(6), confirmed: Boolean(v.confirmed), document: String(v.document), reason: String(v.reason) };
      const result = await api<Preview>('/cost-revisions/preview', { method: 'POST', body: JSON.stringify(request) }); setPreview({ request, result });
    }} />
    {p && preview && <section className="panel backup-intro"><div><h3>Conferir antes de confirmar</h3><p>Lote #{p.lot_id}: de {preciseCost(p.previous_cost_cents)} para {preciseCost(p.unit_cost_cents)} por unidade de controle.</p><p>{p.sales.length} venda(s) e {p.productions.length} produção(ões) afetadas. Confira os relatórios a partir de {dateTime(p.earliest_affected_at)}.</p><p>Documento: {preview.request.document}. Motivo: {preview.request.reason}.</p>{p.purchase_linked && <p>Este lote veio de uma compra. A despesa e o pagamento originais continuarão iguais; confira separadamente qualquer diferença financeira da nota.</p>}<p>Se uma apuração já foi guardada, registre uma nova conferência e combine o ajuste com seus pais.</p></div><button className="button primary" disabled={busy} onClick={() => void confirm()}>{busy ? 'Confirmando…' : 'Confirmar correção deste lote'}</button></section>}
    {p && <DataTable title="Vendas afetadas pela prévia" rows={p.sales} columns={[{ label: 'Venda', render: r => `#${r.id}` }, { label: 'Custo atual', render: r => money(r.before_cents) }, { label: 'Custo corrigido', render: r => money(r.after_cents) }]} />}
    {message && <div className="notice" role="status">{message}</div>}
    <DataTable title="Histórico de correções (últimas 500)" rows={revisions.data || []} columns={[{ label: 'Correção / lote', render: r => `#${r.id} · lote #${r.lot_id}` }, { label: 'Data', render: r => dateTime(r.created_at) }, { label: 'Antes', render: r => preciseCost(r.previous_cost_cents) }, { label: 'Depois', render: r => preciseCost(r.unit_cost_cents) }, { label: 'Documento / motivo', render: r => `${r.document} · ${r.reason}` }]} />
  </>;
}
