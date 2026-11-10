import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '../api';
import { localNow, instant, count } from '../components/ui';

type SheetItem = { id: number; sku: string; name: string; category: string; kind: string; unit: string; expected: string | number; minimum: string | number };
const kindNames: Record<string, string> = { product: 'Produtos para venda', ingredient: 'Ingredientes', packaging: 'Embalagens' };

/** Inventário de vários itens no mesmo horário de corte, gravado em uma única operação. */
export default function InventorySheet({ onSaved }: { onSaved: () => Promise<unknown> }) {
  const [kind, setKind] = useState(''); const [at, setAt] = useState(localNow());
  const [sheet, setSheet] = useState<{ at: string; items: SheetItem[] } | null>(null);
  const [counted, setCounted] = useState<Record<number, string>>({});
  const [reason, setReason] = useState(''); const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(''); const [error, setError] = useState(false);
  function fail(text: string) { setError(true); setMessage(text); }
  async function load() {
    setBusy(true); setMessage('');
    try { setSheet(await api(`/inventory-sheet?at=${encodeURIComponent(instant(at))}${kind ? `&kind=${kind}` : ''}`)); setCounted({}); }
    catch (e) { fail(e instanceof Error ? e.message : 'Não foi possível carregar a folha.'); }
    finally { setBusy(false); }
  }
  async function submit() {
    if (!sheet) return;
    const lines = sheet.items.filter(i => (counted[i.id] || '').trim()).map(i => ({ item_id: i.id, expected: String(i.expected), counted: counted[i.id].trim().replace(',', '.') }));
    if (!lines.length) return fail('Preencha a quantidade contada de ao menos um item.');
    if (reason.trim().length < 3) return fail('Informe quem contou e a justificativa dos ajustes.');
    setBusy(true); setMessage('');
    try {
      const result = await api<{ counted: number; with_difference: number }>('/inventory-counts/batch', { method: 'POST', body: JSON.stringify({ counted_at: instant(at), reason: reason.trim(), lines }) });
      setError(false); setMessage(`${result.counted} item(ns) registrado(s), ${result.with_difference} com diferença ajustada.`); setSheet(null); setCounted({}); setReason(''); await onSaved();
    } catch (e) { fail(e instanceof Error ? e.message : 'Não foi possível registrar o inventário.'); }
    finally { setBusy(false); }
  }
  const filled = sheet?.items.filter(i => (counted[i.id] || '').trim()).length || 0;
  return <details className="panel record-form inventory-sheet"><summary>Folha de inventário (vários itens)<span>Contagem completa ou por grupo, no mesmo horário de corte</span></summary>
    <div className="operation-fields"><label>Grupo<select value={kind} onChange={e => { setKind(e.target.value); setSheet(null); }}><option value="">Todos os itens ativos</option>{Object.entries(kindNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Horário de corte da contagem<input type="datetime-local" value={at} onChange={e => { setAt(e.target.value); setSheet(null); }} /><small>Itens movimentados depois desse horário não entram no saldo esperado.</small></label></div>
    <div className="operation-form-foot"><span className={error ? 'form-error' : 'success-message'} role={error ? 'alert' : 'status'}>{message}</span><button className="button secondary" type="button" disabled={busy} onClick={() => void load()}>{busy && !sheet ? <Loader2 className="spin" size={15} /> : null}Carregar folha</button></div>
    {sheet && <><div className="table-scroll"><table><thead><tr><th>Item</th><th>Categoria</th><th>Saldo esperado</th><th>Contado</th><th>Diferença</th></tr></thead><tbody>{sheet.items.length ? sheet.items.map(i => {
      const value = (counted[i.id] || '').trim().replace(',', '.'); const diff = value && !Number.isNaN(Number(value)) ? Number(value) - Number(i.expected) : null;
      return <tr key={i.id}><td>{i.name}<div className="muted">{i.sku}</div></td><td>{i.category}</td><td>{count(i.expected)} {i.unit}</td><td><input className="count-input" inputMode="decimal" aria-label={`Quantidade contada de ${i.name}`} value={counted[i.id] || ''} onChange={e => setCounted({ ...counted, [i.id]: e.target.value })} placeholder="não contado" /></td><td className={diff ? (diff < 0 ? 'danger-text' : 'warning-text') : ''}>{diff === null ? '—' : `${diff > 0 ? '+' : ''}${count(Math.round(diff * 1000) / 1000)} ${i.unit}`}</td></tr>;
    }) : <tr><td colSpan={5} className="empty-cell">Nenhum item ativo neste grupo.</td></tr>}</tbody></table></div>
      <div className="operation-fields"><label>Quem contou e justificativa dos ajustes<input value={reason} maxLength={500} onChange={e => setReason(e.target.value)} placeholder="Ex.: inventário semanal com a Dona Gel; diferenças a apurar" /></label></div>
      <div className="operation-form-foot"><span className="muted">{filled} de {sheet.items.length} item(ns) preenchido(s). Itens em branco não são alterados.</span><button className="button primary" type="button" disabled={busy || !filled} onClick={() => void submit()}>{busy && <Loader2 className="spin" size={15} />}Registrar contagens</button></div></>}
  </details>;
}
