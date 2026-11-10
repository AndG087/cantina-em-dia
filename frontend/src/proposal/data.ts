/** Simulador isolado. Os objetos acompanham as respostas da API; nunca a consultam.
 * As duas extensões propostas estão separadas em DemoMeta: horários não informados
 * e itens ainda não contados. Não são campos já disponíveis na API atual.
 */
export const TODAY = '2026-11-10';
export type Scenario = 'rotina' | 'primeiro-uso';
export type Session = {
  id: number; opened_at: string; opened_by: string; opening_cents: number;
  closed_at: string | null; closed_by: string; cash_sales_cents: number;
  pix_cents: number; card_cents: number; voucher_cents: number; withdrawals_cents: number;
  counted_cents: number; expected_cents: number; difference_cents: number; note: string;
};
export type CashDay = {
  day: string; calendar_status: 'open' | 'closed'; sessions: Session[]; carried: number[];
  cash_sales_cents: number; pix_cents: number; card_cents: number; voucher_cents: number;
  withdrawals_cents: number; difference_cents: number; issues: string[];
  state: 'pending' | 'reviewed'; state_label: string;
  review: { status: 'ok' | 'issues'; note: string; reviewed_at: string } | null;
};
export type Item = { id: number; name: string; category: string; unit: 'un' | 'kg' | 'L'; minimum: string; balance: string; active: boolean };
export type Receipt = {
  id: number; document: string; supplier: string; purchase_id: number; occurred_at: string;
  total_cents: number; invoice_total_cents: number; invoice_difference_cents: number;
  issues: string[]; ok: boolean;
  lines: { name: string; unit: string; quantity: string; unit_cost_cents: number; cost_variation_pct: number | null }[];
};
export type Expense = { id: number; description: string; category: string; amount_cents: number; occurred_at: string; payee: string; document: string; receipt_id: number | null };
export type DemoMeta = { uncounted_item_ids: number[]; reported_times: Record<string, { opening: string; closing: string }> };
export type DemoState = {
  cash_days: CashDay[]; items: Item[];
  purchase_receipts: { receipts: Receipt[]; pending_orders: { id: number; supplier: string }[]; cost_tolerance_pct: number };
  expenses: Expense[];
  school_events: { id: number; title: string; starts_on: string; effect: 'closed' | 'open'; source: string }[];
  meta: DemoMeta;
};
export type Draft = {
  day: string; opened_by: string; closed_by: string; opening: string; opening_time: string; closing_time: string;
  cash: string; pix: string; card: string; voucher: string; withdrawn: string; drawer: string; note: string; confirmed: boolean;
  correction_day: string; correction_reason: string;
};
export const blankDraft = (): Draft => ({ day: '', opened_by: '', closed_by: '', opening: '', opening_time: '', closing_time: '', cash: '', pix: '', card: '', voucher: '', withdrawn: '', drawer: '', note: '', confirmed: false, correction_day: '', correction_reason: '' });
export const draftKey = (scenario: Scenario) => `cantina.proposta.v4.rascunho.${scenario}`;
const stateKey = (scenario: Scenario) => `cantina.proposta.v4.dados.${scenario}`;
export function loadDraft(scenario: Scenario): Draft | null {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(draftKey(scenario)) || 'null');
    if (!raw || typeof raw !== 'object') return null;
    const base = blankDraft();
    for (const key of Object.keys(base) as (keyof Draft)[]) if (typeof (raw as Draft)[key] !== typeof base[key]) return null;
    return raw as Draft;
  } catch { return null; }
}
export function storeDraft(scenario: Scenario, draft: Draft | null) {
  try { if (draft) localStorage.setItem(draftKey(scenario), JSON.stringify(draft)); else localStorage.removeItem(draftKey(scenario)); return true; } catch { return false; }
}
export function loadState(scenario: Scenario): DemoState {
  try {
    const raw = JSON.parse(localStorage.getItem(stateKey(scenario)) || 'null');
    if (raw && Array.isArray(raw.cash_days) && Array.isArray(raw.items) && raw.purchase_receipts && raw.meta) return raw;
  } catch { /* Não impedir a revisão se o armazenamento estiver indisponível. */ }
  return fixtures(scenario);
}
export function storeState(scenario: Scenario, state: DemoState) {
  try { localStorage.setItem(stateKey(scenario), JSON.stringify(state)); return true; } catch { return false; }
}
export function resetState(scenario: Scenario) { try { localStorage.removeItem(stateKey(scenario)); localStorage.removeItem(draftKey(scenario)); } catch { /* Estado em memória ainda pode ser reiniciado. */ } return fixtures(scenario); }

export function decimal(value: string, places = 2): number | null {
  if (!new RegExp(`^\\d+(?:[,.]\\d{1,${places}})?$`).test(value.trim())) return null;
  const n = Number(value.trim().replace(',', '.'));
  return Number.isSafeInteger(Math.round(n * 10 ** places)) ? n : null;
}
export const cents = (text: string) => { const n = decimal(text); return n === null ? null : Math.round(n * 100); };
export const dateLabel = (iso: string) => new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long', weekday: 'long' }).format(new Date(`${iso}T12:00:00-03:00`));
export const sales = (day: CashDay) => day.cash_sales_cents + day.pix_cents + day.card_cents + day.voucher_cents;
export const mondayOf = (iso: string) => { const d = new Date(`${iso}T12:00:00Z`); d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7); return d.toISOString().slice(0, 10); };
export const shift = (iso: string, days: number) => { const d = new Date(`${iso}T12:00:00Z`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); };
export function makeDay(day: string, session: Session, reviewed: boolean): CashDay {
  const difference = session.difference_cents;
  return {
    day, calendar_status: 'open', sessions: [session], carried: [], cash_sales_cents: session.cash_sales_cents,
    pix_cents: session.pix_cents, card_cents: session.card_cents, voucher_cents: session.voucher_cents,
    withdrawals_cents: session.withdrawals_cents, difference_cents: difference,
    issues: difference ? ['Diferença entre o dinheiro esperado e o contado.'] : [],
    state: reviewed ? 'reviewed' : 'pending', state_label: reviewed ? 'Valores conferidos' : 'Aguardando conferência',
    review: reviewed ? { status: difference ? 'issues' : 'ok', note: 'Conferido com o resumo da equipe.', reviewed_at: `${day}T22:30:00-03:00` } : null,
  };
}
function fixtureDay(day: string, index: number, cash: number, pix: number, card: number, voucher: number, difference = 0) {
  const expected = 10000 + cash - 30000;
  return makeDay(day, { id: index, opened_at: `${day}T07:30:00-03:00`, closed_at: `${day}T22:00:00-03:00`, opened_by: 'Ana (exemplo)', closed_by: 'Rosa (exemplo)',
    opening_cents: 10000, cash_sales_cents: cash, pix_cents: pix, card_cents: card, voucher_cents: voucher, withdrawals_cents: 30000,
    counted_cents: expected + difference, expected_cents: expected, difference_cents: difference, note: '' }, !difference);
}
/** Dias úteis de outubro para os gráficos do Início: valores fictícios, determinísticos, já conferidos. */
function octoberDays(): CashDay[] {
  const days: CashDay[] = [];
  for (let date = '2026-10-01', n = 0; date <= '2026-10-30'; date = shift(date, 1)) {
    const weekday = new Date(`${date}T12:00:00Z`).getUTCDay();
    if (weekday === 0 || weekday === 6 || date === '2026-10-12') continue;
    n += 1;
    const friday = weekday === 5 ? 1.12 : 1, wave = (n * 37) % 11, swing = (n * 53) % 7;
    const reais = (base: number, step: number, spread: number) => Math.round((base + step * spread) * friday) * 100;
    const difference = date === '2026-10-16' ? -1500 : date === '2026-10-23' ? 500 : 0;
    const day = fixtureDay(date, 100 + n, reais(290, 9, wave), reais(520, 14, swing), reais(250, 8, (wave + 3) % 9), reais(80, 6, swing));
    const session = { ...day.sessions[0], counted_cents: day.sessions[0].expected_cents + difference, difference_cents: difference };
    days.push({ ...makeDay(date, session, true), review: { status: difference ? 'issues' : 'ok', note: difference ? 'Diferença explicada pela equipe (exemplo).' : 'Conferido com o resumo da equipe.', reviewed_at: `${date}T22:30:00-03:00` } });
  }
  return days.reverse();
}
export function fixtures(scenario: Scenario): DemoState {
  const first = scenario === 'primeiro-uso';
  const items: Item[] = [
    { id: 1, name: 'Coca-Cola Lata 350ml', category: 'Bebidas', unit: 'un', minimum: '6', balance: '12', active: true },
    { id: 2, name: 'Coxinha de Frango', category: 'Salgados', unit: 'un', minimum: '10', balance: '18', active: true },
    { id: 3, name: 'Café em Pó 500g', category: 'Mercearia', unit: 'un', minimum: '2', balance: '4', active: true },
    { id: 4, name: 'Tomate', category: 'Verduras', unit: 'kg', minimum: '1', balance: '3', active: true },
    { id: 5, name: 'Leite Integral', category: 'Mercearia', unit: 'un', minimum: '3', balance: '8', active: true },
    { id: 6, name: 'Detergente de Louça 500ml', category: 'Limpeza', unit: 'un', minimum: '2', balance: '4', active: true },
  ];
  const receipt: Receipt = { id: 1, document: '1245', supplier: 'Distribuidora de bebidas (exemplo)', purchase_id: 1, occurred_at: '2026-11-09T10:00:00-03:00', total_cents: 16800, invoice_total_cents: 16800, invoice_difference_cents: 0, issues: [], ok: true,
    lines: [{ name: items[0].name, unit: 'un', quantity: '48', unit_cost_cents: 350, cost_variation_pct: null }] };
  const octoberReceipts: Receipt[] = [
    { id: 2, document: '0871', supplier: 'Atacado (exemplo)', purchase_id: 2, occurred_at: '2026-10-05T10:00:00-03:00', total_cents: 124000, invoice_total_cents: 124000, invoice_difference_cents: 0, issues: [], ok: true,
      lines: [{ name: items[1].name, unit: 'un', quantity: '400', unit_cost_cents: 200, cost_variation_pct: null }, { name: items[2].name, unit: 'un', quantity: '20', unit_cost_cents: 2200, cost_variation_pct: null }] },
    { id: 3, document: '1190', supplier: receipt.supplier, purchase_id: 3, occurred_at: '2026-10-19T10:00:00-03:00', total_cents: 16800, invoice_total_cents: 16800, invoice_difference_cents: 0, issues: [], ok: true,
      lines: [{ name: items[0].name, unit: 'un', quantity: '48', unit_cost_cents: 350, cost_variation_pct: null }] },
  ];
  const purchaseExpense = (r: Receipt, id: number): Expense => ({ id, description: 'Compra de produtos', category: 'Mercadorias', amount_cents: r.total_cents, occurred_at: r.occurred_at, payee: r.supplier, document: r.document, receipt_id: r.id });
  const octoberExpenses: Expense[] = [
    purchaseExpense(octoberReceipts[0], 10), purchaseExpense(octoberReceipts[1], 11),
    { id: 12, description: 'Gás da cantina', category: 'Gás', amount_cents: 11000, occurred_at: '2026-10-01T10:00:00-03:00', payee: 'Revenda de gás (exemplo)', document: '131', receipt_id: null },
    { id: 13, description: 'Produtos de limpeza', category: 'Limpeza', amount_cents: 8640, occurred_at: '2026-10-07T10:00:00-03:00', payee: 'Mercadinho (exemplo)', document: '5521', receipt_id: null },
    { id: 14, description: 'Embalagens para quentinha', category: 'Embalagens', amount_cents: 6490, occurred_at: '2026-10-14T10:00:00-03:00', payee: 'Descartáveis (exemplo)', document: '772', receipt_id: null },
    { id: 15, description: 'Gás da cantina', category: 'Gás', amount_cents: 11000, occurred_at: '2026-10-15T10:00:00-03:00', payee: 'Revenda de gás (exemplo)', document: '139', receipt_id: null },
    { id: 16, description: 'Conserto do liquidificador', category: 'Manutenção', amount_cents: 18000, occurred_at: '2026-10-21T10:00:00-03:00', payee: 'Assistência técnica (exemplo)', document: '88', receipt_id: null },
    { id: 17, description: 'Gás da cantina', category: 'Gás', amount_cents: 11500, occurred_at: '2026-10-29T10:00:00-03:00', payee: 'Revenda de gás (exemplo)', document: '146', receipt_id: null },
  ];
  return {
    cash_days: first ? [] : [fixtureDay('2026-11-09', 6, 38000, 64000, 32000, 12000, -2000), fixtureDay('2026-11-06', 5, 35000, 61000, 30000, 12000, -2000), fixtureDay('2026-11-05', 4, 32000, 58000, 30000, 10000), fixtureDay('2026-11-04', 3, 36000, 60000, 29000, 11000), fixtureDay('2026-11-03', 2, 33000, 57000, 30000, 10000), fixtureDay('2026-11-02', 1, 30000, 50000, 30000, 12000), ...octoberDays()],
    items: first ? items.map(i => ({ ...i, balance: '0' })) : items,
    purchase_receipts: { receipts: first ? [] : [receipt, ...octoberReceipts], pending_orders: [], cost_tolerance_pct: 10 },
    expenses: first ? [] : [...octoberExpenses, { id: 1, description: 'Compra de bebidas', category: 'Mercadorias', amount_cents: receipt.total_cents, occurred_at: receipt.occurred_at, payee: receipt.supplier, document: receipt.document, receipt_id: receipt.id }, { id: 2, description: 'Gás da cantina', category: 'Gás', amount_cents: 11000, occurred_at: '2026-11-06T10:00:00-03:00', payee: 'Revenda de gás (exemplo)', document: '158', receipt_id: null }, { id: 3, description: 'Produtos de limpeza', category: 'Limpeza', amount_cents: 8640, occurred_at: '2026-11-03T10:00:00-03:00', payee: 'Mercadinho (exemplo)', document: '5604', receipt_id: null }, { id: 4, description: 'Produtos de limpeza', category: 'Limpeza', amount_cents: 8640, occurred_at: '2026-11-05T15:00:00-03:00', payee: 'Mercadinho (exemplo)', document: '5611', receipt_id: null }, { id: 5, description: 'Gás da cantina (entrega urgente)', category: 'Gás', amount_cents: 24000, occurred_at: '2026-11-09T09:00:00-03:00', payee: 'Revenda de gás (exemplo)', document: '163', receipt_id: null }],
    school_events: [{ id: 1, title: 'Nossa Senhora Aparecida', starts_on: '2026-10-12', effect: 'closed', source: 'Calendário nacional' }, { id: 2, title: 'Dia da Consciência Negra', starts_on: '2026-11-20', effect: 'closed', source: 'Calendário nacional' }], meta: { uncounted_item_ids: first ? items.map(i => i.id) : [], reported_times: {} },
  };
}
/** Derivado exclusivamente dos registros, no formato utilizado por /reports/weekly. */
export function weekly(state: DemoState, week: string) {
  const start = mondayOf(week), end = shift(start, 6);
  const days = state.cash_days.filter(d => d.day >= start && d.day <= end);
  const expenses = state.expenses.filter(e => e.occurred_at.slice(0, 10) >= start && e.occurred_at.slice(0, 10) <= end);
  const pending = days.filter(d => d.state !== 'reviewed');
  const totals = { sales_cents: days.reduce((n, d) => n + sales(d), 0), purchases_cents: expenses.filter(e => e.receipt_id !== null).reduce((n, e) => n + e.amount_cents, 0), expenses_cents: expenses.filter(e => e.receipt_id === null).reduce((n, e) => n + e.amount_cents, 0) };
  return { week_start: start, week_end: end, complete_week: end < TODAY, totals, cash_pending_days: pending.length, actions: pending.map(d => `Conferir o caixa de ${d.day}.`), days, pending };
}
export function draftFromDay(day: CashDay, meta: DemoMeta): Draft {
  const s = day.sessions[0]; const text = (n: number) => (n / 100).toFixed(2).replace('.', ',');
  const times = meta.reported_times[day.day];
  return { day: day.day, opened_by: s.opened_by, closed_by: s.closed_by, opening: text(s.opening_cents),
    opening_time: times ? times.opening : s.opened_at.slice(11, 16), closing_time: times ? times.closing : (s.closed_at?.slice(11, 16) || ''),
    cash: text(s.cash_sales_cents), pix: text(s.pix_cents), card: text(s.card_cents), voucher: text(s.voucher_cents), withdrawn: text(s.withdrawals_cents), drawer: text(s.counted_cents), note: '', confirmed: false, correction_day: day.day, correction_reason: '' };
}
