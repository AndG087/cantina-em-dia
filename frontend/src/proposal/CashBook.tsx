import { useState } from 'react';
import { ChevronRight, CircleCheck, CircleDashed, ReceiptText, TriangleAlert } from 'lucide-react';
import type { CashDay, DemoState, Expense } from './data';
import { TODAY, dateLabel, mondayOf, sales, shift } from './data';
import { Empty, Heading, Link, money, Notice } from './components';
import { dayStatus } from './Today';

/** Caixa: o caderno de caixa. Dias agrupados por semana, com vendas, gaveta e conferência em colunas separadas. */
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const weekday = (iso: string) => cap(dateLabel(iso).split(',')[0].replace('-feira', ''));
const drawerText = (d: number) => d < 0 ? `Faltaram ${money(-d)}` : d > 0 ? `Sobraram ${money(d)}` : 'Bateu';

type Slot = { date: string; day?: CashDay; closed?: string };

function Drawer({ difference }: { difference: number }) {
  return difference
    ? <span className="c-drawer c-off"><TriangleAlert size={17} aria-hidden="true" />{drawerText(difference)}</span>
    : <span className="c-drawer c-even"><CircleCheck size={17} aria-hidden="true" />Bateu</span>;
}
function Review({ day }: { day: CashDay }) {
  return day.state === 'reviewed'
    ? <span className="c-review c-done">Conferido</span>
    : <span className="p-badge p-badge-warning">Falta conferir</span>;
}

/** Uma linha do caderno. Usada também no resumo da semana e no histórico. */
export function LedgerRow({ slot }: { slot: Slot }) {
  const { date, day, closed } = slot;
  const name = <span className="c-day"><strong>{weekday(date)}</strong> {short(date)}</span>;
  if (day) return <li><a className="c-row" href={`#day/${date}`} aria-label={`${dateLabel(date)}: vendas de ${money(sales(day))}, gaveta: ${drawerText(day.difference_cents).toLowerCase()}, ${day.state === 'reviewed' ? 'conferido' : 'falta conferir'}`}>
    {name}<span className="c-sales">{money(sales(day))}</span><Drawer difference={day.difference_cents} /><Review day={day} /><ChevronRight className="c-chevron" size={20} aria-hidden="true" />
  </a></li>;
  if (closed) return <li><div className="c-row c-quiet">{name}<span className="c-note">Cantina fechada: {closed}</span></div></li>;
  if (date === TODAY) return <li><a className="c-row c-missing" href="#daily/start">{name}<span className="c-note"><CircleDashed size={17} aria-hidden="true" />Hoje, ainda em aberto</span><span className="c-action">Registrar</span></a></li>;
  return <li><a className="c-row c-missing" href="#daily/start">{name}<span className="c-note"><CircleDashed size={17} aria-hidden="true" />Sem registro</span><span className="c-action">Registrar</span></a></li>;
}
function LedgerHead() {
  return <div className="c-head" aria-hidden="true"><span>Dia</span><span>Vendas</span><span>Gaveta</span><span>Conferência</span><span /></div>;
}
/** Lista simples de dias já registrados (sem semanas), para o resumo e o histórico. */
export function DayLedger({ days }: { days: CashDay[] }) {
  if (!days.length) return <Empty>Nenhum dia registrado neste período. <Link to="daily/start">Registrar um dia</Link></Empty>;
  return <div className="c-book"><LedgerHead /><ul className="c-rows">{days.map(d => <LedgerRow key={d.day} slot={{ date: d.day, day: d }} />)}</ul></div>;
}

const FILTERS = [{ id: '', label: 'Todos os dias' }, { id: 'conferir', label: 'Falta conferir' }, { id: 'diferenca', label: 'Com diferença' }];

export default function CashBook({ state, parts }: { state: DemoState; parts: string[] }) {
  return parts[1] === 'gastos' ? <Expenses state={state} parts={parts} /> : <CashDays state={state} parts={parts} />;
}

function CashDays({ state, parts }: { state: DemoState; parts: string[] }) {
  const [weeksShown, setWeeksShown] = useState(3);
  const filter = FILTERS.some(f => f.id === parts[1]) ? parts[1] : '';
  const days = [...state.cash_days].sort((a, b) => b.day.localeCompare(a.day));
  const counts: Record<string, number> = { '': days.length, conferir: days.filter(d => d.state !== 'reviewed').length, diferenca: days.filter(d => d.difference_cents !== 0).length };
  const header = <>
    <Heading title="Caixa" description="O caderno de caixa: cada dia registrado, quanto vendeu e como ficou a gaveta." />
    <CashTabs current="dias" state={state} />
    <div className="p-actions"><Link to="daily/start" primary>Registrar um dia</Link></div>
  </>;
  if (!days.length) return <>{header}<Empty>Nenhum dia registrado ainda. O primeiro registro começa pelo resumo que a equipe manda no fim do dia.</Empty></>;

  // Semanas de segunda a sexta, da atual para trás, até a semana do primeiro registro.
  const first = days[days.length - 1].day;
  const weeks: { monday: string; slots: Slot[] }[] = [];
  for (let monday = mondayOf(TODAY); monday >= mondayOf(first); monday = shift(monday, -7)) {
    const slots: Slot[] = [];
    for (let i = 4; i >= 0; i--) {
      const date = shift(monday, i); if (date > TODAY) continue;
      const day = days.find(d => d.day === date), status = dayStatus(state, date);
      if (day) slots.push({ date, day });
      else if (!status.open) slots.push({ date, closed: status.reason });
      else if (date >= first) slots.push({ date });
    }
    // Sábado ou domingo só entram quando houve registro (funcionamento a pedido).
    for (const extra of [6, 5]) { const date = shift(monday, extra); const day = days.find(d => d.day === date); if (day) slots.unshift({ date, day }); }
    const visible = slots.filter(s => filter === 'conferir' ? s.day && s.day.state !== 'reviewed' : filter === 'diferenca' ? s.day && s.day.difference_cents !== 0 : true);
    if (visible.length) weeks.push({ monday, slots: visible });
  }
  const shown = filter ? weeks : weeks.slice(0, weeksShown);

  return <>{header}
    <nav className="c-filters" aria-label="Filtrar dias">{FILTERS.map(f => <a key={f.id} href={`#cash${f.id ? `/${f.id}` : ''}`} aria-current={filter === f.id ? 'true' : undefined}>{f.label}<span className="c-filter-count">{counts[f.id]}</span></a>)}</nav>
    {!shown.length && <Empty>Nenhum dia nesta situação. <Link to="cash" quiet>Ver todos os dias</Link></Empty>}
    {shown.map(week => {
      const registered = week.slots.filter(s => s.day).map(s => s.day!);
      const total = registered.reduce((n, d) => n + sales(d), 0), off = registered.filter(d => d.difference_cents).length;
      const friday = shift(week.monday, 4);
      return <section className="c-week" key={week.monday} aria-labelledby={`semana-${week.monday}`}>
        <header className="c-week-head">
          <h2 id={`semana-${week.monday}`}>{week.monday === mondayOf(TODAY) ? 'Esta semana' : `Semana de ${short(week.monday)} a ${short(friday)}`}</h2>
          <p><strong>{money(total)}</strong> em vendas{off > 0 && <span className="c-week-off">, {off} {off === 1 ? 'dia' : 'dias'} com diferença</span>}</p>
        </header>
        <div className="c-book"><LedgerHead /><ul className="c-rows">{week.slots.map(slot => <LedgerRow key={slot.date} slot={slot} />)}</ul></div>
      </section>;
    })}
    {!filter && weeks.length > weeksShown && <button type="button" className="p-button p-secondary c-more" onClick={() => setWeeksShown(n => n + 4)}>Mostrar semanas anteriores</button>}
    <div className="p-context-links"><Link to="inicio/semana" quiet>Gráficos da semana</Link><Link to="summary" quiet>Resumo da semana</Link></div>
  </>;
}

/* ---------- As duas partes do caixa ---------- */
function CashTabs({ current, state }: { current: 'dias' | 'gastos'; state: DemoState }) {
  const pending = state.cash_days.filter(d => d.state !== 'reviewed').length, flagged = expenseAlerts(state.expenses).size;
  return <nav className="c-tabs" aria-label="Partes do caixa">
    <a href="#cash" aria-current={current === 'dias' ? 'page' : undefined}>Vendas e gaveta{pending > 0 && <span className="c-tab-flag" aria-label={`${pending} a conferir`}>{pending}</span>}</a>
    <a href="#cash/gastos" aria-current={current === 'gastos' ? 'page' : undefined}>Gastos{flagged > 0 && <span className="c-tab-flag" aria-label={`${flagged} fora do padrão`}>{flagged}</span>}</a>
  </nav>;
}

/* ---------- Gastos ---------- */
const DAY_MS = 86400000;
const when = (e: Expense) => new Date(e.occurred_at).getTime();
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const monthName = (ym: string) => `${cap(MONTHS[Number(ym.slice(5, 7)) - 1])} de ${ym.slice(0, 4)}`;

/** Mesmas regras do sistema (backend/app/expenses.py): um alerta é convite à conferência, não prova de erro. */
export function expenseAlerts(expenses: Expense[]): Map<number, string[]> {
  const result = new Map<number, string[]>();
  const add = (id: number, text: string) => result.set(id, [...(result.get(id) || []), text]);
  for (const e of expenses) {
    // Valor acima do usual: 50% acima da mediana da categoria, com ao menos 3 lançamentos nos 180 dias anteriores.
    const prior = expenses.filter(o => o.id !== e.id && o.category === e.category && when(o) < when(e) && when(e) - when(o) <= 180 * DAY_MS).map(o => o.amount_cents).sort((a, b) => a - b);
    if (prior.length >= 3) {
      const mid = prior.length % 2 ? prior[(prior.length - 1) / 2] : (prior[prior.length / 2 - 1] + prior[prior.length / 2]) / 2;
      if (e.amount_cents > mid * 1.5) add(e.id, `Valor acima do usual: em ${e.category.toLowerCase()} o comum é ${money(Math.round(mid))}.`);
    }
    // Possível duplicidade: mesmo favorecido e mesmo valor em até 7 dias.
    const twin = expenses.find(o => o.id !== e.id && o.payee === e.payee && o.amount_cents === e.amount_cents && Math.abs(when(o) - when(e)) <= 7 * DAY_MS);
    if (twin) add(e.id, `Possível duplicidade: mesmo valor pago a ${e.payee} em ${short(twin.occurred_at.slice(0, 10))}.`);
  }
  return result;
}

const EXPENSE_FILTERS = [{ id: '', label: 'Todos' }, { id: 'compras', label: 'Compras com nota' }, { id: 'outros', label: 'Outros gastos' }, { id: 'alerta', label: 'Fora do padrão' }];

function Expenses({ state, parts }: { state: DemoState; parts: string[] }) {
  const filter = EXPENSE_FILTERS.some(f => f.id === parts[2]) ? parts[2] : '';
  const alerts = expenseAlerts(state.expenses);
  const all = [...state.expenses].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at) || b.id - a.id);
  const match = (e: Expense, f: string) => f === 'compras' ? e.receipt_id !== null : f === 'outros' ? e.receipt_id === null : f === 'alerta' ? alerts.has(e.id) : true;
  const list = all.filter(e => match(e, filter));
  const months = [...new Set(list.map(e => e.occurred_at.slice(0, 7)))];
  const flagged = all.filter(e => alerts.has(e.id));
  return <>
    <Heading title="Caixa" description="Tudo o que saiu: compras com nota e os outros gastos da cantina." />
    <CashTabs current="gastos" state={state} />
    {parts[2] === 'salvo' && <Notice>Gasto salvo somente neste exemplo.</Notice>}
    <div className="p-actions"><Link to="expense" primary>Anotar um gasto</Link><Link to="buy">Registrar uma compra com nota</Link></div>
    {flagged.length > 0 && filter !== 'alerta' && <section className="c-alerts" aria-labelledby="fora-do-padrao">
      <h2 id="fora-do-padrao"><TriangleAlert size={20} aria-hidden="true" />{flagged.length} {flagged.length === 1 ? 'gasto fora do padrão' : 'gastos fora do padrão'}</h2>
      <p>Um alerta é um convite para conferir, não prova de erro. Veja se há explicação para cada um.</p>
      <ul>{flagged.slice(0, 3).map(e => <li key={e.id}><strong>{e.description}</strong>, {short(e.occurred_at.slice(0, 10))}, {money(e.amount_cents)}<br /><span>{alerts.get(e.id)!.join(' ')}</span></li>)}</ul>
      {flagged.length > 3 && <Link to="cash/gastos/alerta" quiet>Ver todos</Link>}
    </section>}
    <nav className="c-filters" aria-label="Filtrar gastos">{EXPENSE_FILTERS.map(f => <a key={f.id} href={`#cash/gastos${f.id ? `/${f.id}` : ''}`} aria-current={filter === f.id ? 'true' : undefined}>{f.label}<span className="c-filter-count">{all.filter(e => match(e, f.id)).length}</span></a>)}</nav>
    {!list.length && <Empty>{all.length ? 'Nenhum gasto nesta situação.' : 'Nenhum gasto anotado ainda. Compras com nota entram aqui sozinhas quando a nota é registrada.'}</Empty>}
    {months.map(ym => {
      const rows = list.filter(e => e.occurred_at.startsWith(ym));
      const withNote = rows.filter(e => e.receipt_id !== null).reduce((n, e) => n + e.amount_cents, 0), other = rows.reduce((n, e) => n + e.amount_cents, 0) - withNote;
      return <section className="c-week" key={ym} aria-labelledby={`mes-${ym}`}>
        <header className="c-week-head"><h2 id={`mes-${ym}`}>{monthName(ym)}</h2><p><strong>{money(withNote + other)}</strong> no mês{!filter && <span className="c-week-split">: {money(withNote)} em compras com nota e {money(other)} em outros gastos</span>}</p></header>
        <div className="c-book">
          <div className="c-head c-head-exp" aria-hidden="true"><span>Dia</span><span>Gasto</span><span>Categoria</span><span>Valor</span><span /></div>
          <ul className="c-rows">{rows.map(e => {
            const flags = alerts.get(e.id);
            const cells = <>
              <span className="c-day"><strong>{weekday(e.occurred_at.slice(0, 10))}</strong> {short(e.occurred_at.slice(0, 10))}</span>
              <span className="c-what"><strong>{e.description}</strong><small>{e.payee}{e.document ? `, comprovante ${e.document}` : ''}</small>{flags && <small className="c-flag"><TriangleAlert size={15} aria-hidden="true" />{flags.join(' ')}</small>}</span>
              <span className="c-cat">{e.receipt_id !== null ? <><ReceiptText size={16} aria-hidden="true" />Compra com nota</> : e.category}</span>
              <span className="c-sales">{money(e.amount_cents)}</span>
            </>;
            return <li key={e.id}>{e.receipt_id !== null
              ? <a className={`c-row c-row-exp${flags ? ' c-row-flag' : ''}`} href={`#receipt/${e.receipt_id}`}>{cells}<ChevronRight className="c-chevron" size={20} aria-hidden="true" /></a>
              : <div className={`c-row c-row-exp${flags ? ' c-row-flag' : ''}`}>{cells}<span /></div>}</li>;
          })}</ul>
        </div>
      </section>;
    })}
    <div className="p-context-links"><Link to="purchases" quiet>Compras e notas</Link><Link to="inicio/mes" quiet>Gastos por categoria no Início</Link></div>
  </>;
}
