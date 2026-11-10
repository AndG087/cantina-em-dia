import type { ReactNode } from 'react';
import { Circle, CircleCheck, DoorClosed, DoorOpen, ReceiptText, TriangleAlert, Wallet } from 'lucide-react';
import type { CashDay, DemoState } from './data';
import { TODAY, dateLabel, sales, shift } from './data';
import { Link, Notice, money } from './components';

/** Aba Hoje: a comanda do dia. Mostra se a cantina abre, a rotina do dia em ordem e o que ficou para trás. */
const OPEN_AT = '07:30', CLOSE_AT = '22:00';
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const weekdayName = (iso: string) => cap(dateLabel(iso).split(',')[0]);
const dayName = (iso: string) => `${weekdayName(iso)}, ${short(iso)}`;
const clock = (time: string) => time.replace(':', 'h');
const timeOf = (iso: string | null) => (iso ? iso.slice(11, 16) : '');
const drawer = (difference: number) => difference < 0 ? `Faltaram ${money(-difference)} na gaveta` : difference > 0 ? `Sobraram ${money(difference)} na gaveta` : 'A gaveta bateu';

/** Mesma regra do sistema: fim de semana só abre com pedido; feriado ou evento da escola fecha. */
export function dayStatus(state: DemoState, date: string): { open: boolean; reason: string } {
  const events = state.school_events.filter(e => e.starts_on === date);
  const closed = events.find(e => e.effect === 'closed'), opened = events.find(e => e.effect === 'open');
  const weekend = [0, 6].includes(new Date(`${date}T12:00:00Z`).getUTCDay());
  if (closed) return { open: false, reason: closed.title };
  if (weekend) return opened ? { open: true, reason: `Aberta a pedido: ${opened.title}` } : { open: false, reason: 'Fim de semana' };
  return { open: true, reason: '' };
}

type Step = { label: string; detail: string; status: 'done' | 'todo' | 'alert'; to?: string };
const STATUS_TEXT = { done: 'Feito', todo: 'Falta', alert: 'Atenção' };
function StepIcon({ status }: { status: Step['status'] }) {
  if (status === 'done') return <CircleCheck size={22} aria-hidden="true" />;
  if (status === 'alert') return <TriangleAlert size={22} aria-hidden="true" />;
  return <Circle size={22} aria-hidden="true" />;
}

function todaySteps(day: CashDay | undefined, friday: boolean): Step[] {
  const steps: Step[] = [];
  if (!day) {
    steps.push(
      { label: 'Abertura', detail: `às ${clock(OPEN_AT)}, com o troco contado`, status: 'todo' },
      { label: 'Fechamento', detail: `às ${clock(CLOSE_AT)}, com o resumo da equipe`, status: 'todo' },
      { label: 'Registrar e conferir', detail: 'depois do fechamento', status: 'todo' },
    );
  } else {
    const s = day.sessions[0], opened = timeOf(s.opened_at), closed = timeOf(s.closed_at);
    steps.push({ label: 'Abertura', detail: `${clock(opened)}, troco de ${money(s.opening_cents)}`, status: opened > OPEN_AT ? 'alert' : 'done' });
    steps.push(closed
      ? { label: 'Fechamento', detail: `${clock(closed)}, ${money(sales(day))} em vendas`, status: closed < CLOSE_AT ? 'alert' : 'done' }
      : { label: 'Fechamento', detail: `às ${clock(CLOSE_AT)}`, status: 'todo' });
    steps.push(day.state === 'reviewed'
      ? { label: 'Conferência', detail: drawer(day.difference_cents), status: day.difference_cents ? 'alert' : 'done' }
      : { label: 'Conferência', detail: day.difference_cents ? drawer(day.difference_cents) : 'falta conferir os valores', status: day.difference_cents ? 'alert' : 'todo', to: `day/${day.day}` });
  }
  if (friday) steps.push({ label: 'Resumo da semana', detail: 'fechar antes de ir embora', status: 'todo', to: 'summary' });
  return steps;
}

function QuickAction({ to, Icon, title, detail }: { to: string; Icon: typeof Wallet; title: string; detail: string }) {
  return <a className="h-quick" href={`#${to}`}><span className="h-quick-icon" aria-hidden="true"><Icon size={22} strokeWidth={2} /></span><span><strong>{title}</strong><small>{detail}</small></span></a>;
}

export default function Today({ state }: { state: DemoState }) {
  const today = state.cash_days.find(d => d.day === TODAY);
  const status = dayStatus(state, TODAY);
  const friday = new Date(`${TODAY}T12:00:00Z`).getUTCDay() === 5;
  const steps = status.open ? todaySteps(today, friday) : [];
  const registered = [...state.cash_days].filter(d => d.day < TODAY).sort((a, b) => b.day.localeCompare(a.day));
  const last = registered[0], first = registered[registered.length - 1]?.day;
  let nextOpen = shift(TODAY, 1); while (!dayStatus(state, nextOpen).open) nextOpen = shift(nextOpen, 1);

  // Ficou para trás: dias sem conferência, dias úteis sem registro (desde o primeiro registro) e notas com diferença.
  const behind: { key: string; title: string; detail: string; to: string; action: string }[] = [];
  for (const d of registered.filter(d => d.state !== 'reviewed'))
    behind.push({ key: `d${d.day}`, title: `Caixa de ${dayName(d.day).toLowerCase()}`, detail: d.difference_cents ? `${drawer(d.difference_cents)}.` : 'Valores ainda não conferidos.', to: `day/${d.day}`, action: 'Conferir' });
  if (first) for (let i = 1; i <= 14; i++) {
    const date = shift(TODAY, -i);
    if (date < first || !dayStatus(state, date).open || state.cash_days.some(d => d.day === date)) continue;
    behind.push({ key: `m${date}`, title: `${dayName(date)} sem registro`, detail: 'A cantina abriu, mas o dia não foi registrado.', to: 'daily/start', action: 'Registrar' });
  }
  for (const r of state.purchase_receipts.receipts.filter(r => !r.ok))
    behind.push({ key: `r${r.id}`, title: `Nota ${r.document}, ${r.supplier}`, detail: 'A nota e os produtos somam valores diferentes.', to: `receipt/${r.id}`, action: 'Ver nota' });

  let action: ReactNode = null;
  if (status.open && !today) action = <Link to="daily/start" primary>Registrar o dia de hoje</Link>;
  else if (today && today.state !== 'reviewed') action = <Link to={`day/${today.day}`} primary>Conferir o dia de hoje</Link>;
  else if (today) action = <Link to={`day/${today.day}`} quiet>Ver o dia registrado</Link>;

  const methods = last ? [['Dinheiro', last.cash_sales_cents], ['Pix', last.pix_cents], ['Cartão', last.card_cents], ['Voucher', last.voucher_cents]] as const : [];
  const top = [...methods].sort((a, b) => b[1] - a[1])[0];

  return <>
    <section className={`h-ticket${status.open ? '' : ' h-closed'}`} aria-labelledby="hoje-titulo">
      <div className="h-ticket-head">
        <div><h1 id="hoje-titulo" tabIndex={-1} data-page-title>{cap(dateLabel(TODAY))}</h1></div>
        <span className={`h-pill ${status.open ? 'h-pill-open' : 'h-pill-closed'}`}>{status.open ? <DoorOpen size={18} aria-hidden="true" /> : <DoorClosed size={18} aria-hidden="true" />}{status.open ? 'Cantina aberta' : 'Cantina fechada'}</span>
      </div>
      <p className="h-ticket-sub">{status.open ? `Contrato: ${clock(OPEN_AT)} às ${clock(CLOSE_AT)}${status.reason ? `. ${status.reason}` : ''}` : `${status.reason}. Volta a abrir em ${dayName(nextOpen).toLowerCase()}.`}</p>
      {status.open && <>
        <ol className="h-steps" aria-label="Rotina de hoje">{steps.map(step => <li key={step.label} className={`h-step-${step.status}`}>
          <StepIcon status={step.status} /><span className="p-sr-only">{STATUS_TEXT[step.status]}: </span>
          <span className="h-step-label">{step.to ? <a href={`#${step.to}`}>{step.label}</a> : step.label}</span>
          <span className="h-step-detail">{step.detail}</span>
        </li>)}</ol>
        {!today && <p className="h-ticket-note">Os horários e valores entram no sistema quando o dia é registrado com o resumo da equipe.</p>}
      </>}
      {action && <div className="h-ticket-action">{action}</div>}
    </section>

    {behind.length > 0 && <section aria-labelledby="hoje-atras">
      <h2 id="hoje-atras" className="p-section-title h-section-title">Ficou para trás <span className="h-count">{behind.length}</span></h2>
      <div className="p-card p-list p-pending">{behind.map(item => <div className="p-list-row" key={item.key}><div><strong>{item.title}</strong><p>{item.detail}</p></div><Link to={item.to}>{item.action}</Link></div>)}</div>
    </section>}

    <section aria-labelledby="hoje-durante">
      <h2 id="hoje-durante" className="p-section-title">Durante o dia</h2>
      <div className="h-quick-grid">
        <QuickAction to="buy" Icon={ReceiptText} title="Chegou uma nota" detail="Confira a nota com o que foi entregue" />
        <QuickAction to="expense" Icon={Wallet} title="Anotar um gasto" detail="Gás, limpeza, conserto e outros" />
      </div>
      {!!state.meta.uncounted_item_ids.length && <Notice>Há produtos cadastrados que ainda não foram contados. <Link to="stock" quiet>Fazer a contagem</Link></Notice>}
    </section>

    {last && top && <section className="p-card h-last" aria-labelledby="hoje-ultimo">
      <h2 id="hoje-ultimo">{last.day === shift(TODAY, -1) ? 'Ontem foi assim' : `${weekdayName(last.day)}, ${short(last.day)}, foi assim`}</h2>
      <dl className="p-facts">
        <div><dt>Vendas</dt><dd>{money(sales(last))}</dd></div>
        <div><dt>Gaveta</dt><dd className={last.difference_cents ? 'h-bad' : 'h-good'}>{last.difference_cents ? drawer(last.difference_cents).replace(' na gaveta', '') : 'Bateu'}</dd></div>
        <div><dt>Forma mais usada</dt><dd>{top[0]}, {Math.round(top[1] * 100 / Math.max(1, sales(last)))}% das vendas</dd></div>
      </dl>
      <Link to={`inicio/dia/${last.day}`} quiet>Ver Gráficos</Link>
    </section>}

    <div className="p-context-links"><Link to="summary" quiet>Resumo da semana</Link><Link to="school" quiet>Dias de funcionamento</Link></div>
  </>;
}
