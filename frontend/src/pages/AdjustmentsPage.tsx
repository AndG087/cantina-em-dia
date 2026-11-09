import { useState } from 'react';
import { DataTable, ErrorNote, ModuleHeading, RecordForm, cents, dateTime, instant, localNow, money, save, useRemote } from '../components/ui';

type Item = { id: number; name: string; kind: string; active: boolean; sale_price_cents: number | null; price_locked: boolean };
type Rule = { id: number; item_id: number; effective_from: string; price_cents: number | null; locked: boolean; source: string; reason: string; cancelled_at: string | null };
export default function AdjustmentsPage() {
  const items = useRemote<Item[]>('/items'); const rules = useRemote<Rule[]>('/price-rules');
  const [error] = useState('');
  async function refresh() { await Promise.all([items.refresh(), rules.refresh()]); }
  const products = (items.data || []).filter(i => i.kind === 'product' && i.active);
  const name = (id: number) => items.data?.find(i => i.id === id)?.name || `#${id}`;
  return <><ModuleHeading title="Preços e custos" description="Registre as mudanças com documento de origem e preserve o histórico." onRefresh={() => void refresh()} /><ErrorNote errors={[items.error, rules.error, error]} />
    <div className="notice">O preço usado na venda é conferido pela data e hora em que ela ocorreu. Uma nova regra não muda vendas antigas. Para preços fixados pela licitação, informe a autorização correspondente, inclusive para liberar o preço.</div>
    <div className="forms-grid"><RecordForm title="Nova vigência de preço" submit="Registrar vigência" fields={[
      { name: 'item_id', label: 'Produto', options: products.map(i => ({ value: i.id, label: i.name })) },
      { name: 'effective_from', label: 'Passa a valer a partir de', type: 'datetime-local', value: localNow(), hint: 'Pode ser uma data futura. Não pode alcançar vendas já registradas desse produto.' },
      { name: 'price', label: 'Preço unitário de venda (R$)', type: 'number', min: 0 },
      { name: 'locked', label: 'Preço fixado pela licitação', type: 'checkbox' },
      { name: 'source', label: 'Documento ou autorização de origem', hint: 'Exemplo: aditivo da licitação, data e identificação da tabela. Guarde o arquivo em Comprovantes e anexos.' },
      { name: 'reason', label: 'Motivo da mudança', type: 'textarea' },
    ]} onSubmit={v => save('/price-rules', { item_id: Number(v.item_id), effective_from: instant(v.effective_from), price_cents: cents(v.price), locked: v.locked, source: v.source, reason: v.reason }, refresh)} />
    <RecordForm title="Cancelar vigência sem vendas posteriores" fields={[
      { name: 'id', label: 'Regra a cancelar', options: (rules.data || []).filter(r => !r.cancelled_at && new Date(r.effective_from).getFullYear() > 1900).map(r => ({ value: r.id, label: `#${r.id} · ${name(r.item_id)} · ${dateTime(r.effective_from)}` })) },
      { name: 'reason', label: 'Justificativa do cancelamento' },
    ]} onSubmit={v => save(`/price-rules/${v.id}/cancel`, { reason: v.reason }, refresh)} /></div>
    <DataTable title="Preços vigentes agora" rows={products} columns={[{ label: 'Produto', render: r => name(r.id) }, { label: 'Preço', render: r => r.sale_price_cents === null ? 'Não informado' : money(r.sale_price_cents) }, { label: 'Regra', render: r => r.price_locked ? 'Fixo pela licitação' : 'Livre' }]} />
    <DataTable title="Histórico de vigências (últimas 2000)" rows={rules.data || []} columns={[
      { label: 'Regra / produto', render: r => `#${r.id} · ${name(r.item_id)}` }, { label: 'Válida a partir de', render: r => new Date(r.effective_from).getFullYear() <= 1900 ? 'Cadastro inicial' : dateTime(r.effective_from) },
      { label: 'Preço', render: r => r.price_cents === null ? 'Não informado' : money(r.price_cents) }, { label: 'Tipo', render: r => r.locked ? 'Fixo' : 'Livre' },
      { label: 'Origem e motivo', render: r => `${r.source} · ${r.reason}` }, { label: 'Situação', render: r => r.cancelled_at ? 'Cancelada' : 'Registrada' },
    ]} />
  </>;
}
