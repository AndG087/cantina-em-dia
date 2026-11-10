import { useState } from 'react';
import type { DemoState, Item } from './data';
import { decimal } from './data';
import { count, Empty, Field, focusError, Heading, Link, Notice } from './components';
import type { Errors } from './components';

export default function StockFlow({ state, update }: { state: DemoState; update: (state: DemoState) => void }) {
  const [search, setSearch] = useState(''); const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [errors, setErrors] = useState<Errors>({}); const [review, setReview] = useState(false);
  const [note, setNote] = useState(''); const [saved, setSaved] = useState(false);
  const normalize = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const visible = state.items.filter(i => normalize(`${i.name} ${i.category}`).includes(normalize(search)));
  const filled = state.items.filter(i => quantities[i.id]?.trim());
  function validate() {
    const e: Errors = {}; if (!filled.length) e.search = 'Preencha a quantidade de pelo menos um produto.';
    for (const i of filled) { const q = decimal(quantities[i.id], 3); if (q === null) e[`qty-${i.id}`] = 'Informe uma quantidade válida, a partir de zero.'; else if (i.unit === 'un' && !Number.isInteger(q)) e[`qty-${i.id}`] = 'Informe unidades inteiras.'; }
    setErrors(e); if (Object.keys(e).length) { setSearch(''); focusError(e); return false; } return true;
  }
  const status = (i: Item) => state.meta.uncounted_item_ids.includes(i.id) ? 'Ainda não contado' : `Quantidade no sistema: ${count(i.balance)} ${i.unit}`;
  return <><Heading title={review ? 'Conferir a contagem' : 'Produtos e contagem'} description={review ? 'Revise o que foi contado antes de mudar os saldos.' : 'Busque um produto. Não precisa contar todos de uma vez.'} back="purchases" />
    {state.meta.uncounted_item_ids.length > 0 && <Notice>Há produtos ainda não contados. Saldo inicial zero não confirma que acabaram.</Notice>}
    {saved && <Notice>Contagem atualizada somente neste exemplo. Os dados reais não foram alterados.</Notice>}
    <form className="p-card p-form" noValidate onSubmit={e => { e.preventDefault(); if (!review) { if (validate()) { setReview(true); requestAnimationFrame(() => document.querySelector<HTMLHeadingElement>('[data-page-title]')?.focus()); } } else {
      if (note.trim().length < 3) { setErrors({ countNote: 'Informe quem contou e uma observação da contagem.' }); focusError({ countNote: '' }); return; }
      update({ ...state, items: state.items.map(i => quantities[i.id]?.trim() ? { ...i, balance: String(decimal(quantities[i.id], 3)) } : i), meta: { ...state.meta, uncounted_item_ids: state.meta.uncounted_item_ids.filter(id => !filled.some(i => i.id === id)) } });
      setQuantities({}); setReview(false); setSaved(true); setNote('');
    } }}>
      {Object.keys(errors).length > 0 && <p className="p-error-summary" role="alert">Revise os campos indicados.</p>}
      {!review ? <><Field id="search" type="search" label="Buscar produto" placeholder="Ex.: café, tomate, bebida…" value={search} error={errors.search} onChange={e => setSearch(e.target.value)} />{!visible.length && <Empty>Nenhum produto encontrado.</Empty>}{visible.map(i => <div className="p-product" key={i.id}><div><strong>{i.name}</strong><p className="p-small" data-product-status>{status(i)}</p></div><Field id={`qty-${i.id}`} label={`Contado (${i.unit})`} inputMode={i.unit === 'un' ? 'numeric' : 'decimal'} placeholder="Não contado" value={quantities[i.id] || ''} error={errors[`qty-${i.id}`]} onChange={e => { setQuantities(q => ({ ...q, [i.id]: e.target.value })); setErrors({}); setSaved(false); }} /></div>)}<p className="p-small">{filled.length} produto(s) preenchido(s). Em branco, nada muda. Zero é uma contagem válida.</p></> : <>
      {filled.map(i => <div className="p-list-row" key={i.id}><div><strong>{i.name}</strong><p className="p-small">No sistema: {count(i.balance)} {i.unit} · Contado: {quantities[i.id]} {i.unit}</p></div><span>Diferença: {count(decimal(quantities[i.id], 3)! - Number(i.balance))} {i.unit}</span></div>)}<Field id="countNote" label="Quem contou e observação" value={note} error={errors.countNote} onChange={e => setNote(e.target.value)} /><Notice>Uma diferença não diz se houve venda, consumo ou perda. Registre o que foi conferido.</Notice><button type="button" className="p-link" onClick={() => setReview(false)}>← Alterar quantidades</button>
      </>}
      <div className="p-form-footer"><Link to="catalog" quiet>Ver cadastros</Link><button className="p-button p-primary">{review ? 'Registrar contagem no exemplo' : 'Conferir contagem'}</button></div>
    </form></>;
}
