import { useEffect, useState } from 'react';
import type { DemoState, Receipt, Scenario } from './data';
import { cents, decimal, TODAY } from './data';
import { Field, focusError, Heading, money, Notice } from './components';
import type { Errors } from './components';

type Line = { id: number; item_id: string; quantity: string; price: string };
type PurchaseDraft = { supplier: string; document: string; date: string; by: string; invoice: string; explanation: string; lines: Line[] };
const blank = (): PurchaseDraft => ({ supplier: '', document: '', date: '', by: '', invoice: '', explanation: '', lines: [{ id: 1, item_id: '', quantity: '', price: '' }] });
const key = (scenario: Scenario) => `cantina.proposta.v4.compra.${scenario}`;
const load = (scenario: Scenario): PurchaseDraft => {
  try { const d = JSON.parse(localStorage.getItem(key(scenario)) || 'null'); if (d && Array.isArray(d.lines) && typeof d.supplier === 'string') return d; } catch { /* Sem armazenamento, usar memória. */ }
  return blank();
};
export default function PurchaseFlow({ state, scenario, update }: { state: DemoState; scenario: Scenario; update: (state: DemoState) => void }) {
  const [draft, setDraft] = useState(() => load(scenario));
  const [errors, setErrors] = useState<Errors>({});
  const [storageFailed, setStorageFailed] = useState(false);
  useEffect(() => { try { localStorage.setItem(key(scenario), JSON.stringify(draft)); } catch { setStorageFailed(true); } }, [draft, scenario]);
  const change = (field: keyof Omit<PurchaseDraft, 'lines'>, value: string) => { setDraft(d => ({ ...d, [field]: value })); setErrors(e => { const next = { ...e }; delete next[field]; return next; }); };
  const changeLine = (id: number, field: keyof Omit<Line, 'id'>, value: string) => { setDraft(d => ({ ...d, lines: d.lines.map(l => l.id === id ? { ...l, [field]: value } : l) })); setErrors(e => { const next = { ...e }; delete next[`line-${id}-${field}`]; return next; }); };
  const lineTotal = (line: Line) => { const q = decimal(line.quantity, 3), c = cents(line.price); return q !== null && q > 0 && c !== null ? Math.round(q * c) : null; };
  const sums = draft.lines.map(lineTotal);
  const total = sums.every(n => n !== null) ? sums.reduce<number>((n, x) => n + x!, 0) : null;
  const invoice = cents(draft.invoice);
  const mismatch = invoice !== null && total !== null && invoice !== total;
  function save() {
    const e: Errors = {};
    if (draft.supplier.trim().length < 2) e.supplier = 'Informe onde comprou.';
    if (!draft.document.trim()) e.document = 'Informe o número ou referência da nota.';
    if (!draft.date || draft.date > TODAY) e.date = 'Informe a data em que recebeu, até 10/11/2026.';
    if (draft.by.trim().length < 2) e.by = 'Informe quem fez a compra.';
    const used = new Set<string>();
    for (const line of draft.lines) {
      const item = state.items.find(i => String(i.id) === line.item_id);
      const q = decimal(line.quantity, 3);
      if (!item) e[`line-${line.id}-item_id`] = 'Escolha um produto cadastrado.';
      else if (used.has(line.item_id)) e[`line-${line.id}-item_id`] = 'Este produto já está na compra. Ajuste a quantidade na primeira linha.';
      used.add(line.item_id);
      if (q === null || q <= 0) e[`line-${line.id}-quantity`] = 'Informe uma quantidade maior que zero, com até três casas decimais.';
      else if (item?.unit === 'un' && !Number.isInteger(q)) e[`line-${line.id}-quantity`] = 'Este produto é contado em unidades inteiras.';
      if (cents(line.price) === null) e[`line-${line.id}-price`] = 'Informe o custo de uma unidade, em reais.';
    }
    if (invoice === null) e.invoice = 'Informe o total impresso na nota.';
    if (mismatch && draft.explanation.trim().length < 3) e.explanation = 'Confira os valores ou explique a diferença da nota.';
    if (state.purchase_receipts.receipts.some(r => r.supplier.toLocaleLowerCase() === draft.supplier.trim().toLocaleLowerCase() && r.document === draft.document.trim())) e.document = 'Essa nota já foi registrada para esse fornecedor. Abra a compra existente.';
    setErrors(e); if (Object.keys(e).length) { focusError(e); return; }
    const id = Date.now();
    const receipt: Receipt = { id, purchase_id: id, supplier: draft.supplier.trim(), document: draft.document.trim(), occurred_at: `${draft.date}T12:00:00-03:00`, total_cents: total!, invoice_total_cents: invoice!, invoice_difference_cents: invoice! - total!, issues: mismatch ? [`Diferença da nota: ${draft.explanation.trim()}`] : [], ok: !mismatch,
      lines: draft.lines.map(l => { const item = state.items.find(i => String(i.id) === l.item_id)!; return { name: item.name, unit: item.unit, quantity: String(decimal(l.quantity, 3)), unit_cost_cents: cents(l.price)!, cost_variation_pct: null }; }) };
    update({ ...state, purchase_receipts: { ...state.purchase_receipts, receipts: [receipt, ...state.purchase_receipts.receipts] },
      items: state.items.map(item => { const line = draft.lines.find(l => l.item_id === String(item.id)); return line ? { ...item, balance: String(Math.round((Number(item.balance) + decimal(line.quantity, 3)!) * 1000) / 1000) } : item; }),
      expenses: [{ id, description: `Compra · ${receipt.supplier}`, category: 'Mercadorias', amount_cents: receipt.total_cents, occurred_at: receipt.occurred_at, payee: receipt.supplier, document: receipt.document, receipt_id: id }, ...state.expenses] });
    try { localStorage.removeItem(key(scenario)); } catch { /* Nada foi enviado ao servidor. */ }
    location.hash = `receipt/${id}/saved`;
  }
  return <><Heading title="Registrar uma compra" description="Informe a nota e os produtos que chegaram. Tudo fica no mesmo registro." back="purchases" />
    {storageFailed && <Notice danger>O rascunho da compra não pôde ser guardado neste navegador. Mantenha esta tela aberta.</Notice>}
    <form className="p-card p-form" noValidate onSubmit={e => { e.preventDefault(); save(); }}>
      {Object.keys(errors).length > 0 && <p role="alert" className="p-error-summary">Revise os campos indicados. Seus produtos continuam preenchidos.</p>}
      <h2>Onde você comprou?</h2><div className="p-fields"><Field id="supplier" label="Fornecedor" list="p-suppliers" value={draft.supplier} error={errors.supplier} onChange={e => change('supplier', e.target.value)} /><datalist id="p-suppliers">{[...new Set(state.purchase_receipts.receipts.map(r => r.supplier))].map(s => <option key={s}>{s}</option>)}</datalist><Field id="document" label="Número ou referência da nota" value={draft.document} error={errors.document} onChange={e => change('document', e.target.value)} /><Field id="date" type="date" max={TODAY} label="Dia em que recebeu" value={draft.date} error={errors.date} onChange={e => change('date', e.target.value)} /><Field id="by" label="Quem fez a compra" value={draft.by} error={errors.by} onChange={e => change('by', e.target.value)} /></div>
      <h2>Produtos recebidos</h2><p className="p-small">O custo deve corresponder à unidade indicada em cada produto.</p>
      {draft.lines.map((line, index) => { const item = state.items.find(i => String(i.id) === line.item_id); const itemId = `line-${line.id}-item_id`; return <fieldset className="p-purchase-line" key={line.id}><legend>Produto {index + 1}</legend><div className="p-field"><label htmlFor={itemId}>Buscar e escolher produto</label><input id={itemId} list="p-products" value={item?.name || line.item_id} placeholder="Digite o nome do produto" aria-invalid={!!errors[itemId]} aria-describedby={errors[itemId] ? `${itemId}-error` : undefined} onChange={e => { const found = state.items.find(i => i.name.toLocaleLowerCase() === e.target.value.toLocaleLowerCase()); changeLine(line.id, 'item_id', found ? String(found.id) : e.target.value); }} />{errors[itemId] && <p id={`${itemId}-error`} className="p-error">{errors[itemId]}</p>}</div><div className="p-fields"><Field id={`line-${line.id}-quantity`} label={`Quantidade (${item?.unit || 'unidade do produto'})`} inputMode={item?.unit === 'un' ? 'numeric' : 'decimal'} value={line.quantity} error={errors[`line-${line.id}-quantity`]} onChange={e => changeLine(line.id, 'quantity', e.target.value)} /><Field id={`line-${line.id}-price`} label={`Custo por ${item?.unit || 'unidade'} (R$)`} inputMode="decimal" value={line.price} error={errors[`line-${line.id}-price`]} onChange={e => changeLine(line.id, 'price', e.target.value)} /></div><div className="p-line-footer"><span>{lineTotal(line) === null ? 'Preencha quantidade e custo' : `Subtotal: ${money(lineTotal(line)!)}`}</span><button type="button" className="p-link" disabled={draft.lines.length === 1} onClick={() => { setDraft(d => ({ ...d, lines: d.lines.filter(l => l.id !== line.id) })); setErrors({}); }}>Remover produto {index + 1}</button></div></fieldset>; })}
      <datalist id="p-products">{state.items.filter(i => i.active).map(i => <option key={i.id} value={i.name}>{i.unit}</option>)}</datalist>
      <button type="button" className="p-button p-secondary" onClick={() => { const id = Math.max(...draft.lines.map(l => l.id)) + 1; setDraft(d => ({ ...d, lines: [...d.lines, { id, item_id: '', quantity: '', price: '' }] })); requestAnimationFrame(() => document.getElementById(`line-${id}-item_id`)?.focus()); }}>+ Adicionar produto</button>
      <div className={`p-total${total === null ? " p-empty-total" : ""}`}><span>Soma dos produtos</span><strong>{total === null ? 'Falta preencher' : money(total)}</strong></div>
      <Field id="invoice" label="Total impresso na nota (R$)" inputMode="decimal" value={draft.invoice} error={errors.invoice} onChange={e => change('invoice', e.target.value)} />
      {mismatch && <><Notice>A nota e os produtos têm valores diferentes. Confira a nota ou explique o motivo.</Notice><Field id="explanation" label="Motivo da diferença" value={draft.explanation} error={errors.explanation} onChange={e => change('explanation', e.target.value)} /></>}
      <p className="p-small">A compra atualiza os produtos e registra o gasto uma vez, apenas nos dados deste exemplo.</p><div className="p-form-footer"><span className="p-small">Rascunho de exemplo neste navegador</span><button className="p-button p-primary">Salvar compra no exemplo</button></div>
    </form></>;
}
