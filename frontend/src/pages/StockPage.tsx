import { useState } from 'react';
import { api } from '../api';
import { DataTable, ErrorNote, PageHeading, RecordForm, count, dateTime, instant, localNow, send, useRemote } from '../components/ui';
import type { Field } from '../components/ui';

export type Item = { id: number; name: string; category: string; unit: string; minimum: string; balance: string; active: boolean };
type Movement = { id: number; item_id: number; quantity: string; kind: string; reason: string; occurred_at: string };
type Count = { id: number; item_id: number; counted_at: string; expected: string; counted: string; difference: string; note: string };
const kinds: Record<string, string> = { entry: 'Entrada avulsa', output: 'Saída / consumo', loss: 'Perda', purchase: 'Compra recebida', count: 'Ajuste de inventário' };

/** Folha de contagem: carrega o saldo esperado de cada item e grava todos os preenchidos de uma vez. */
function CountSheet({ onSaved }: { onSaved: () => Promise<unknown> }) {
  const [at, setAt] = useState(localNow());
  const [sheet, setSheet] = useState<Item[] | null>(null);
  const [counted, setCounted] = useState<Record<number, string>>({});
  const [note, setNote] = useState(''); const [message, setMessage] = useState(''); const [failed, setFailed] = useState(false);
  async function attempt(action: () => Promise<string>) {
    try { setMessage(await action()); setFailed(false); } catch (e) { setMessage(e instanceof Error ? e.message : 'Não foi possível concluir.'); setFailed(true); }
  }
  const load = () => attempt(async () => {
    const result = await api<{ items: (Item & { expected: string })[] }>(`/inventory-sheet?at=${encodeURIComponent(instant(at))}`);
    setSheet(result.items.map(i => ({ ...i, balance: i.expected }))); setCounted({}); return '';
  });
  const filled = (sheet || []).filter(i => (counted[i.id] || '').trim());
  const save = () => attempt(async () => {
    if (!filled.length) throw new Error('Preencha a quantidade contada de ao menos um item.');
    const lines = filled.map(i => ({ item_id: i.id, expected: String(i.balance), counted: counted[i.id].trim().replace(',', '.') }));
    const result = await api<{ counted: number; with_difference: number }>('/inventory-counts', { method: 'POST', body: JSON.stringify({ counted_at: instant(at), note, lines }) });
    setSheet(null); setNote(''); await onSaved();
    return `${result.counted} item(ns) registrado(s), ${result.with_difference} com diferença ajustada.`;
  });
  return <details className="panel record-form wide"><summary>Folha de inventário (contagem do estoque)</summary>
    <div className="fields"><label>Horário da contagem<input type="datetime-local" value={at} onChange={e => { setAt(e.target.value); setSheet(null); }} /><small>O esperado considera compras e lançamentos até esse horário. Diferença negativa = o que saiu sem lançamento (vendas, consumo ou perdas).</small></label></div>
    <div className="form-foot"><span className={failed ? 'danger-text' : 'success-text'} role="status">{message}</span><button type="button" className="button secondary" onClick={() => void load()}>Carregar folha</button></div>
    {sheet && <><div className="table-scroll"><table><thead><tr><th>Item</th><th>Esperado</th><th>Contado</th><th>Diferença</th></tr></thead><tbody>{sheet.map(i => {
      const text = (counted[i.id] || '').trim().replace(',', '.'); const diff = text && !Number.isNaN(Number(text)) ? Math.round((Number(text) - Number(i.balance)) * 1000) / 1000 : null;
      return <tr key={i.id}><td>{i.name}<div className="muted">{i.category}</div></td><td>{count(i.balance)} {i.unit}</td>
        <td><input className="count-input" inputMode="decimal" aria-label={`Contado de ${i.name}`} placeholder="não contado" value={counted[i.id] || ''} onChange={e => setCounted({ ...counted, [i.id]: e.target.value })} /></td>
        <td className={diff ? (diff < 0 ? 'danger-text' : 'warn-text') : ''}>{diff === null ? '—' : `${diff > 0 ? '+' : ''}${count(diff)} ${i.unit}`}</td></tr>;
    })}</tbody></table></div>
      <div className="fields"><label>Quem contou e observações<input value={note} maxLength={500} onChange={e => setNote(e.target.value)} placeholder="Ex.: contagem semanal com a Dona Gel" /></label></div>
      <div className="form-foot"><span className="muted">{filled.length} de {sheet.length} preenchido(s). Itens em branco não mudam.</span><button type="button" className="button primary" onClick={() => void save()}>Registrar contagem</button></div></>}
  </details>;
}

export default function StockPage() {
  const items = useRemote<Item[]>('/items'); const movements = useRemote<Movement[]>('/stock-movements'); const counts = useRemote<Count[]>('/inventory-counts');
  const refresh = () => Promise.all([items.refresh(), movements.refresh(), counts.refresh()]);
  const all = items.data || []; const name = (id: number) => all.find(i => i.id === id)?.name || `#${id}`;
  const active = all.filter(i => i.active).map(i => ({ value: i.id, label: `${i.name} (${count(i.balance)} ${i.unit})` }));
  const itemFields: Field[] = [{ name: 'name', label: 'Nome' }, { name: 'category', label: 'Categoria', hint: 'Ex.: Bebidas, Salgados, Insumos, Embalagens' }, { name: 'unit', label: 'Unidade', options: ['un', 'kg', 'L'].map(v => ({ value: v, label: v })) }, { name: 'minimum', label: 'Estoque mínimo', type: 'number', min: 0, step: '0.001', value: '0' }];
  return <>
    <PageHeading title="Estoque e inventário" description="Saldo de cada item a partir das compras, saídas e contagens." onRefresh={() => void refresh()} />
    <ErrorNote errors={[items.error, movements.error, counts.error]} />
    <div className="forms-grid">
      <CountSheet onSaved={refresh} />
      <RecordForm title="Cadastrar item" fields={itemFields} onSubmit={v => send('/items', { ...v, active: true }, refresh)} />
      <RecordForm title="Alterar item" fields={[{ name: 'id', label: 'Item', options: all.map(i => ({ value: i.id, label: i.name })) }, ...itemFields, { name: 'active', label: 'Item em uso', type: 'checkbox' }]} onSubmit={({ id, ...v }) => send(`/items/${id}`, v, refresh, 'PUT')} />
      <RecordForm title="Registrar entrada, saída ou perda" fields={[{ name: 'item_id', label: 'Item', options: active }, { name: 'kind', label: 'Tipo', options: ['entry', 'output', 'loss'].map(k => ({ value: k, label: kinds[k] })) }, { name: 'quantity', label: 'Quantidade', type: 'number', step: '0.001', min: '0.001' }, { name: 'occurred_at', label: 'Quando', type: 'datetime-local', value: localNow() }, { name: 'reason', label: 'Motivo', hint: 'Compras com nota entram pela tela Compras.' }]}
        onSubmit={v => send('/stock-movements', { ...v, item_id: Number(v.item_id), occurred_at: instant(v.occurred_at) }, refresh)} />
    </div>
    <DataTable title="Itens" rows={all} columns={[{ label: 'Item', render: i => i.name }, { label: 'Categoria', render: i => i.category }, { label: 'Saldo', render: i => <span className={i.active && Number(i.balance) <= Number(i.minimum) ? 'warn-text' : ''}>{count(i.balance)} {i.unit}</span> }, { label: 'Mínimo', render: i => `${count(i.minimum)} ${i.unit}` }, { label: 'Situação', render: i => !i.active ? 'Fora de uso' : Number(i.balance) <= Number(i.minimum) ? 'Repor' : 'Ok' }]} />
    <DataTable title="Contagens e diferenças" rows={counts.data || []} columns={[{ label: 'Quando', render: c => dateTime(c.counted_at) }, { label: 'Item', render: c => name(c.item_id) }, { label: 'Esperado', render: c => count(c.expected) }, { label: 'Contado', render: c => count(c.counted) }, { label: 'Diferença', render: c => <span className={Number(c.difference) ? 'danger-text' : ''}>{count(c.difference)}</span> }, { label: 'Observações', render: c => c.note }]} />
    <DataTable title="Movimentos (últimos 300)" rows={movements.data || []} columns={[{ label: 'Quando', render: m => dateTime(m.occurred_at) }, { label: 'Item', render: m => name(m.item_id) }, { label: 'Tipo', render: m => kinds[m.kind] || m.kind }, { label: 'Quantidade', render: m => count(m.quantity) }, { label: 'Motivo', render: m => m.reason }]} />
  </>;
}
