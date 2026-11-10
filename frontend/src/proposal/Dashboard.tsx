import { useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, CircleCheck, TriangleAlert } from 'lucide-react';
import type { CashDay, DemoState } from './data';
import { TODAY, dateLabel, mondayOf, sales, shift } from './data';
import { Heading, money } from './components';

/** Formas de pagamento: identidade fixa (cor por forma, nunca por posição). Paleta validada com o validador da skill dataviz. */
const METHODS = [
  { key: 'cash_sales_cents', label: 'Dinheiro', color: 'var(--s1)', ink: '#fff' },
  { key: 'pix_cents', label: 'Pix', color: 'var(--s2)', ink: '#fff' },
  { key: 'card_cents', label: 'Cartão', color: 'var(--s3)', ink: '#fff' },
  { key: 'voucher_cents', label: 'Voucher', color: 'var(--s4)', ink: '#0b0b0b' },
] as const;
type MethodKey = typeof METHODS[number]['key'];
type Mode = 'dia' | 'semana' | 'mes';
const MODES: { id: Mode; label: string }[] = [{ id: 'dia', label: 'Dia' }, { id: 'semana', label: 'Semana' }, { id: 'mes', label: 'Mês' }];
const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex'];
const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const reais = (cents: number) => `R$ ${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(Math.round(cents / 100))}`;
const pct = (n: number) => `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
const sumBy = (days: CashDay[], key: MethodKey) => days.reduce((n, d) => n + d[key], 0);
const monthShift = (ym: string, n: number) => { const d = new Date(`${ym}-15T12:00:00Z`); d.setUTCMonth(d.getUTCMonth() + n); return d.toISOString().slice(0, 7); };
const monthLabel = (ym: string) => `${MONTHS[Number(ym.slice(5, 7)) - 1]} de ${ym.slice(0, 4)}`;

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null); const [width, setWidth] = useState(640);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(ref.current); return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}
function niceMax(value: number) { const step = [50000, 100000, 200000, 500000, 1000000].find(s => value / s <= 4) || 1000000; return { max: Math.max(step, Math.ceil(value / step) * step), step }; }

/* Peças de interface dos gráficos */
function Tile({ label, value, children }: { label: string; value: ReactNode; children?: ReactNode }) {
  return <div className="d-tile"><span className="d-tile-label">{label}</span><strong className="d-tile-value">{value}</strong>{children}</div>;
}
function Delta({ current, previous, against }: { current: number; previous: number; against: string }) {
  if (!previous) return <span className="d-delta d-neutral">Sem base para comparar com {against}</span>;
  const change = (current - previous) * 100 / previous; const up = change >= 0;
  return <span className={`d-delta ${up ? 'd-good' : 'd-bad'}`}>{up ? <ArrowUp size={16} aria-hidden="true" /> : <ArrowDown size={16} aria-hidden="true" />}{pct(change)} <span>vs. {against}</span></span>;
}
function Legend() {
  return <ul className="d-legend" aria-label="Legenda">{METHODS.map(m => <li key={m.key}><span style={{ background: m.color }} aria-hidden="true" />{m.label}</li>)}</ul>;
}
function TableView({ caption, head, rows }: { caption: string; head: string[]; rows: (string | number)[][] }) {
  return <details className="d-table"><summary>Ver em tabela</summary><div className="d-table-scroll"><table><caption>{caption}</caption><thead><tr>{head.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => j === 0 ? <th key={j} scope="row">{c}</th> : <td key={j}>{c}</td>)}</tr>)}</tbody></table></div></details>;
}
function Card({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return <section className="d-card"><h2>{title}</h2>{note && <p className="d-note">{note}</p>}{children}</section>;
}

/** Uma divisão do total em partes (barra segmentada alta): parte do todo de relance, sem pizza. */
function SplitBar({ days, label }: { days: CashDay[]; label: string }) {
  const parts = METHODS.map(m => ({ ...m, value: sumBy(days, m.key) })); const total = parts.reduce((n, p) => n + p.value, 0);
  const [active, setActive] = useState<string | null>(null);
  if (!total) return <p className="d-empty">Sem vendas registradas no período.</p>;
  const current = parts.find(p => p.key === active);
  return <div className="d-split"><div className="d-split-bar" role="group" aria-label={label}>{parts.filter(p => p.value > 0).map(p => {
    const share = p.value * 100 / total;
    return <div key={p.key} className={`d-split-part${active && active !== p.key ? ' d-dim' : ''}`} style={{ flexGrow: p.value, background: p.color, color: p.ink }} tabIndex={0}
      aria-label={`${p.label}: ${money(p.value)}, ${Math.round(share)}% do total`} onPointerEnter={() => setActive(p.key)} onPointerLeave={() => setActive(null)} onFocus={() => setActive(p.key)} onBlur={() => setActive(null)}>
      {share >= 11 && <span>{Math.round(share)}%</span>}</div>;
  })}</div>
    <p className="d-split-readout" aria-live="polite">{current ? <><strong>{money(current.value)}</strong> {current.label}, {Math.round(current.value * 100 / total)}% do total</> : <>Passe o mouse ou use Tab para ver cada forma.</>}</p>
    <Legend /></div>;
}

/** Vendas por dia útil da semana, empilhadas por forma de pagamento. */
function WeekColumns({ slots }: { slots: { date: string; day?: CashDay }[] }) {
  const [ref, width] = useWidth<HTMLDivElement>(); const [active, setActive] = useState<number | null>(null);
  const totals = slots.map(s => s.day ? sales(s.day) : 0); const { max, step } = niceMax(Math.max(...totals, 1));
  const m = { left: 64, right: 8, top: 30, bottom: 44 }, plotH = 210, height = m.top + plotH + m.bottom;
  const band = (width - m.left - m.right) / slots.length, col = Math.min(24, band * .5), y = (v: number) => m.top + plotH - v * plotH / max;
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const tip = active === null ? null : slots[active];
  return <div className="d-chart" ref={ref}>
    <svg width={width} height={height} role="img" aria-label="Vendas por dia da semana, separadas por forma de pagamento">
      {ticks.map(t => <g key={t}><line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} className={t ? 'd-grid' : 'd-axis'} /><text x={m.left - 10} y={y(t) + 5} className="d-tick" textAnchor="end">{reais(t)}</text></g>)}
      {slots.map((s, i) => {
        const cx = m.left + band * i + band / 2; let base = m.top + plotH; const visible = METHODS.filter(meth => s.day && s.day[meth.key] > 0);
        return <g key={s.date} className={active !== null && active !== i ? 'd-dim' : ''}>
          {visible.map((meth, k) => {
            const h = s.day![meth.key] * plotH / max, top = base - h, gap = k ? 2 : 0, isTop = k === visible.length - 1;
            const rect = { x: cx - col / 2, y: top, w: col, h: Math.max(0, h - gap) }; base = top;
            return isTop ? <path key={meth.key} fill={meth.color} d={`M${rect.x},${rect.y + rect.h} V${rect.y + 4} Q${rect.x},${rect.y} ${rect.x + 4},${rect.y} H${rect.x + rect.w - 4} Q${rect.x + rect.w},${rect.y} ${rect.x + rect.w},${rect.y + 4} V${rect.y + rect.h} Z`} />
              : <rect key={meth.key} x={rect.x} y={rect.y} width={rect.w} height={rect.h} fill={meth.color} />;
          })}
          {s.day ? <text x={cx} y={y(totals[i]) - 9} textAnchor="middle" className="d-cap">{band < 76 ? reais(totals[i]).slice(3) : reais(totals[i])}</text> : s.date <= TODAY ? <text x={cx} y={m.top + plotH - 10} textAnchor="middle" className="d-missing">{s.date === TODAY ? 'hoje, em aberto' : 'sem registro'}</text> : null}
          <text x={cx} y={m.top + plotH + 20} textAnchor="middle" className="d-xlabel">{WEEKDAYS[i]}</text>
          <text x={cx} y={m.top + plotH + 37} textAnchor="middle" className="d-tick">{short(s.date)}</text>
          <rect x={m.left + band * i} y={m.top} width={band} height={plotH} fill="transparent" tabIndex={0} className="d-hit"
            aria-label={s.day ? `${dateLabel(s.date)}: ${money(totals[i])}. ${METHODS.map(meth => `${meth.label} ${money(s.day![meth.key])}`).join(', ')}` : `${dateLabel(s.date)}: ${s.date > TODAY ? 'ainda não chegou' : 'sem registro'}`}
            onPointerEnter={() => setActive(i)} onPointerLeave={() => setActive(null)} onFocus={() => setActive(i)} onBlur={() => setActive(null)} />
        </g>;
      })}
    </svg>
    {tip && active !== null && <div className="d-tooltip" style={{ left: Math.min(Math.max(m.left + band * active + band / 2, 110), width - 110), top: Math.max(0, y(totals[active]) - 150) }} role="status">
      <p className="d-tooltip-title">{dateLabel(tip.date)}</p>
      {tip.day ? <><p><strong>{money(totals[active])}</strong> total</p>{[...METHODS].reverse().map(meth => <p key={meth.key}><i style={{ background: meth.color }} aria-hidden="true" /><strong>{money(tip.day![meth.key])}</strong> {meth.label}</p>)}</> : <p>{tip.date > TODAY ? 'Este dia ainda não chegou.' : 'Sem registro neste dia.'}</p>}
    </div>}
  </div>;
}

/** Linha de vendas por dia registrado no mês (uma série: sem legenda, o título diz o que é). */
function MonthLine({ days }: { days: CashDay[] }) {
  const [ref, width] = useWidth<HTMLDivElement>(); const [active, setActive] = useState<number | null>(null);
  if (!days.length) return <p className="d-empty">Nenhum dia registrado neste mês.</p>;
  const values = days.map(sales); const { max, step } = niceMax(Math.max(...values));
  const m = { left: 64, right: 84, top: 18, bottom: 36 }, plotH = 200, height = m.top + plotH + m.bottom;
  const x = (i: number) => m.left + (days.length === 1 ? (width - m.left - m.right) / 2 : i * (width - m.left - m.right) / (days.length - 1));
  const y = (v: number) => m.top + plotH - v * plotH / max;
  const line = values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
  const area = `${line} L${x(values.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const every = Math.max(1, Math.ceil(days.length / Math.max(2, Math.floor((width - m.left - m.right) / 64))));
  const pick = (clientX: number, rect: DOMRect) => { const px = clientX - rect.left; let best = 0; days.forEach((_, i) => { if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i; }); setActive(best); };
  const keys = (e: KeyboardEvent) => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); setActive(i => Math.min(days.length - 1, Math.max(0, (i ?? days.length - 1) + (e.key === 'ArrowRight' ? 1 : -1)))); } };
  const last = values.length - 1;
  return <div className="d-chart" ref={ref}>
    <svg width={width} height={height} role="img" tabIndex={0} aria-label={`Vendas por dia registrado, de ${short(days[0].day)} a ${short(days[last].day)}. Use as setas para percorrer os dias.`}
      onPointerMove={e => pick(e.clientX, e.currentTarget.getBoundingClientRect())} onPointerLeave={() => setActive(null)} onKeyDown={keys} onBlur={() => setActive(null)} className="d-line-svg">
      {ticks.map(t => <g key={t}><line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} className={t ? 'd-grid' : 'd-axis'} /><text x={m.left - 10} y={y(t) + 5} className="d-tick" textAnchor="end">{reais(t)}</text></g>)}
      {days.map((d, i) => i % every === 0 || i === last ? <text key={d.day} x={x(i)} y={m.top + plotH + 24} textAnchor="middle" className="d-tick">{short(d.day)}</text> : null)}
      <path d={area} className="d-area" />
      <path d={line} className="d-line" />
      {active !== null && <line x1={x(active)} x2={x(active)} y1={m.top} y2={m.top + plotH} className="d-crosshair" />}
      <circle cx={x(active ?? last)} cy={y(values[active ?? last])} r={5} className="d-dot" />
      <text x={x(last) + 12} y={y(values[last]) + 5} className="d-end">{reais(values[last])}</text>
    </svg>
    {active !== null && <div className="d-tooltip" style={{ left: Math.min(Math.max(x(active), 110), width - 110), top: Math.max(0, y(values[active]) - 96) }} role="status">
      <p className="d-tooltip-title">{dateLabel(days[active].day)}</p><p><i style={{ background: 'var(--s1)' }} aria-hidden="true" /><strong>{money(values[active])}</strong> vendas</p>
      {days[active].difference_cents !== 0 && <p className="d-tooltip-flag">{days[active].difference_cents < 0 ? 'Faltaram' : 'Sobraram'} {money(Math.abs(days[active].difference_cents))} na gaveta</p>}
    </div>}
  </div>;
}

/** Gastos por categoria: barras horizontais ordenadas, uma cor, valor na ponta. */
function RankedBars({ rows }: { rows: { label: string; value: number }[] }) {
  if (!rows.length) return <p className="d-empty">Nenhum gasto lançado no período.</p>;
  const max = Math.max(...rows.map(r => r.value));
  return <ul className="d-ranked">{rows.map(r => <li key={r.label} tabIndex={0} aria-label={`${r.label}: ${money(r.value)}`}><span className="d-ranked-name">{r.label}</span><span className="d-ranked-track"><span style={{ width: `${Math.max(2, r.value * 100 / max)}%` }} /></span><span className="d-ranked-value">{money(r.value)}</span></li>)}</ul>;
}

function CashTile({ days }: { days: CashDay[] }) {
  const off = days.filter(d => d.difference_cents !== 0); const net = off.reduce((n, d) => n + d.difference_cents, 0);
  if (!days.length) return <Tile label="Dinheiro na gaveta" value="—"><span className="d-delta d-neutral">Sem dias registrados</span></Tile>;
  if (!off.length) return <Tile label="Dinheiro na gaveta" value={days.length === 1 ? 'Bateu' : 'Todos bateram'}><span className="d-status d-ok"><CircleCheck size={17} aria-hidden="true" /><span>Sem diferença {days.length === 1 ? 'no dia' : `em ${days.length} dias`}</span></span></Tile>;
  return <Tile label="Dinheiro na gaveta" value={days.length === 1 ? (net < 0 ? `Faltaram ${money(-net)}` : `Sobraram ${money(net)}`) : `${off.length} ${off.length === 1 ? 'dia' : 'dias'} com diferença`}>
    <span className="d-status d-alert"><TriangleAlert size={17} aria-hidden="true" /><span>{off.length === 1 ? (days.length === 1 ? 'Confira o dia e registre o motivo' : `No dia ${short(off[0].day)}`) : `Saldo das diferenças: ${net < 0 ? '−' : '+'}${money(Math.abs(net))}`}</span></span></Tile>;
}

export default function Dashboard({ state, parts }: { state: DemoState; parts: string[] }) {
  const days = [...state.cash_days].sort((a, b) => a.day.localeCompare(b.day));
  const mode: Mode = (['dia', 'semana', 'mes'] as Mode[]).includes(parts[1] as Mode) ? parts[1] as Mode : 'semana';
  if (!days.length) return <><Heading title="Início" description="Os gráficos aparecem a partir do primeiro dia registrado." /><div className="p-empty">Nenhum dia registrado neste cenário. <a href="#daily/start">Registrar um dia</a></div></>;
  const latest = days[days.length - 1].day, first = days[0].day;
  const ref = parts[2] || (mode === 'dia' ? latest : mode === 'semana' ? mondayOf(latest) : latest.slice(0, 7));
  const go = (m: Mode, r?: string) => `#inicio/${m}${r ? `/${r}` : ''}`;
  const expenses = (from: string, to: string) => state.expenses.filter(e => e.occurred_at.slice(0, 10) >= from && e.occurred_at.slice(0, 10) <= to);
  const spent = (list: typeof state.expenses) => list.reduce((n, e) => n + e.amount_cents, 0);

  let title = '', prev: string | null = null, next: string | null = null, body: ReactNode = null;
  if (mode === 'dia') {
    const index = days.findIndex(d => d.day === ref); const day = days[index] || days[days.length - 1];
    prev = index > 0 ? days[index - 1].day : null; next = index >= 0 && index < days.length - 1 ? days[index + 1].day : null;
    const lastWeek = days.find(d => d.day === shift(day.day, -7));
    title = dateLabel(day.day);
    body = <>
      <div className="d-hero"><span className="d-tile-label">Vendas do dia</span><strong>{money(sales(day))}</strong>{lastWeek ? <Delta current={sales(day)} previous={sales(lastWeek)} against={`${dateLabel(lastWeek.day).split(',')[0]} anterior`} /> : <span className="d-delta d-neutral">Sem o mesmo dia da semana anterior para comparar</span>}</div>
      <div className="d-tiles"><CashTile days={[day]} /><Tile label="Gastos lançados no dia" value={money(spent(expenses(day.day, day.day)))}><span className="d-delta d-neutral">Compras e outros gastos</span></Tile></div>
      <Card title="Como os clientes pagaram"><SplitBar days={[day]} label={`Formas de pagamento em ${dateLabel(day.day)}`} />
        <TableView caption="Vendas do dia por forma de pagamento" head={['Forma', 'Valor', 'Parte do total']} rows={METHODS.map(m => [m.label, money(day[m.key]), `${Math.round(day[m.key] * 100 / Math.max(1, sales(day)))}%`])} /></Card>
      <a className="p-link" href={`#day/${day.day}`}>Abrir o registro deste dia</a></>;
  } else if (mode === 'semana') {
    const monday = mondayOf(ref); const friday = shift(monday, 4), sunday = shift(monday, 6);
    const inWeek = days.filter(d => d.day >= monday && d.day <= sunday);
    // Semana em andamento: compara só com os mesmos dias da semana anterior, para não comparar 1 dia com 5.
    const lastDay = latest < friday ? latest : friday, partial = lastDay < friday;
    const before = days.filter(d => d.day >= shift(monday, -7) && d.day <= shift(lastDay, -7));
    const closed = new Set(state.school_events.filter(e => e.effect === 'closed').map(e => e.starts_on));
    const slots = Array.from({ length: 5 }, (_, i) => shift(monday, i)).map(date => ({ date, day: inWeek.find(d => d.day === date) }));
    const total = inWeek.reduce((n, d) => n + sales(d), 0), totalBefore = before.reduce((n, d) => n + sales(d), 0);
    const missing = slots.filter(s => !s.day && !closed.has(s.date) && s.date <= latest);
    prev = shift(monday, -7) >= mondayOf(first) ? shift(monday, -7) : null; next = shift(monday, 7) <= latest ? shift(monday, 7) : null;
    title = `Semana de ${short(monday)} a ${short(friday)}`;
    body = <>
      <div className="d-tiles d-tiles-4">
        <Tile label="Vendas da semana" value={money(total)}><Delta current={total} previous={totalBefore} against={partial ? `os mesmos dias da semana anterior` : 'semana anterior'} /></Tile>
        <Tile label="Média por dia registrado" value={money(inWeek.length ? Math.round(total / inWeek.length) : 0)}><span className="d-delta d-neutral">{inWeek.length} de 5 dias úteis registrados</span></Tile>
        <Tile label="Gastos da semana" value={money(spent(expenses(monday, sunday)))}><span className="d-delta d-neutral">Compras e outros gastos</span></Tile>
        <CashTile days={inWeek} />
      </div>
      {missing.length > 0 && <p className="d-warning-line"><TriangleAlert size={17} aria-hidden="true" />{missing.length === 1 ? `${dateLabel(missing[0].date)} está sem registro.` : `${missing.length} dias úteis sem registro nesta semana.`}</p>}
      <Card title="Vendas por dia" note="Cada coluna soma as formas de pagamento informadas no fechamento."><Legend /><WeekColumns slots={slots} />
        <TableView caption="Vendas por dia e forma de pagamento" head={['Dia', ...METHODS.map(m => m.label), 'Total']} rows={slots.map(s => [dateLabel(s.date), ...METHODS.map(m => s.day ? money(s.day[m.key]) : '—'), s.day ? money(sales(s.day)) : 'Sem registro'])} /></Card>
      <Card title="Formas de pagamento na semana"><SplitBar days={inWeek} label="Formas de pagamento na semana" /></Card></>;
  } else {
    const month = /^\d{4}-\d{2}$/.test(ref) ? ref : latest.slice(0, 7); const start = `${month}-01`, end = `${month}-31`;
    const inMonth = days.filter(d => d.day.startsWith(month)); const before = days.filter(d => d.day.startsWith(monthShift(month, -1)));
    const total = inMonth.reduce((n, d) => n + sales(d), 0); const avg = inMonth.length ? Math.round(total / inMonth.length) : 0;
    const avgBefore = before.length ? Math.round(before.reduce((n, d) => n + sales(d), 0) / before.length) : 0;
    const monthSpend = expenses(start, end); const byCategory = Object.entries(monthSpend.reduce<Record<string, number>>((acc, e) => ({ ...acc, [e.category]: (acc[e.category] || 0) + e.amount_cents }), {})).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
    prev = monthShift(month, -1) >= first.slice(0, 7) ? monthShift(month, -1) : null; next = monthShift(month, 1) <= latest.slice(0, 7) ? monthShift(month, 1) : null;
    title = monthLabel(month)[0].toUpperCase() + monthLabel(month).slice(1);
    body = <>
      <div className="d-tiles d-tiles-4">
        <Tile label="Vendas no mês" value={money(total)}><span className="d-delta d-neutral">em {inMonth.length} {inMonth.length === 1 ? 'dia registrado' : 'dias registrados'}{month === latest.slice(0, 7) ? ', mês em andamento' : ''}</span></Tile>
        <Tile label="Média por dia" value={money(avg)}><Delta current={avg} previous={avgBefore} against="média do mês anterior" /></Tile>
        <Tile label="Gastos do mês" value={money(spent(monthSpend))}><span className="d-delta d-neutral">Compras e outros gastos</span></Tile>
        <CashTile days={inMonth} />
      </div>
      <Card title="Vendas por dia registrado" note="Fins de semana e feriados não aparecem: a cantina não abriu."><MonthLine days={inMonth} />
        <TableView caption="Vendas por dia registrado" head={['Dia', 'Vendas', 'Diferença na gaveta']} rows={inMonth.map(d => [dateLabel(d.day), money(sales(d)), d.difference_cents ? money(d.difference_cents) : '—'])} /></Card>
      <div className="d-two">
        <Card title="Gastos por categoria"><RankedBars rows={byCategory} /></Card>
        <Card title="Formas de pagamento no mês"><SplitBar days={inMonth} label="Formas de pagamento no mês" /></Card>
      </div></>;
  }
  return <>
    <Heading title="Início" description="Como a cantina está indo, a partir dos dias registrados." />
    <div className="d-filters">
      <div className="d-segmented" role="group" aria-label="Período">{MODES.map(m => <a key={m.id} href={go(m.id)} aria-current={mode === m.id ? 'true' : undefined}>{m.label}</a>)}</div>
      <div className="d-stepper">
        {prev ? <a href={go(mode, prev)} aria-label="Período anterior"><ChevronLeft size={20} /></a> : <span aria-hidden="true"><ChevronLeft size={20} /></span>}
        <h2>{title}</h2>
        {next ? <a href={go(mode, next)} aria-label="Próximo período"><ChevronRight size={20} /></a> : <span aria-hidden="true"><ChevronRight size={20} /></span>}
      </div>
    </div>
    {body}
  </>;
}
