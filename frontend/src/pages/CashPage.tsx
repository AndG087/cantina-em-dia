import { Badge, DataTable, ErrorNote, PageHeading, RecordForm, cents, dateTime, instant, localNow, money, send, shortDate, useRemote } from '../components/ui';

type Session = { id: number; opened_at: string; opened_by: string; opening_cents: number; closed_at: string | null; closed_by: string; cash_sales_cents: number | null; pix_cents: number | null; card_cents: number | null;
  withdrawals_cents: number | null; counted_cents: number | null; expected_cents: number | null; difference_cents: number | null; note: string };
type CashDay = { day: string; calendar_status: string; sessions: Session[]; cash_sales_cents: number; pix_cents: number; card_cents: number; withdrawals_cents: number; difference_cents: number; issues: string[];
  state: 'not_applicable' | 'in_progress' | 'pending' | 'reviewed' | 'outdated'; state_label: string; review: { status: string; note: string; reviewed_at: string } | null };
const stateTone = { not_applicable: 'muted', in_progress: 'info', pending: 'warn', reviewed: 'ok', outdated: 'danger' } as const;
const calendarNames: Record<string, string> = { open: 'Normal', closed: 'Fechada', reduced: 'Reduzido', increased: 'Maior movimento' };
const weekday = (iso: string) => ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'][new Date(`${iso}T12:00:00`).getDay()];

export default function CashPage() {
  const sessions = useRemote<Session[]>('/cash-sessions'); const days = useRemote<CashDay[]>('/cash-reviews/days?days=14');
  const refresh = () => Promise.all([sessions.refresh(), days.refresh()]);
  const open = sessions.data?.find(s => !s.closed_at);
  const latest = sessions.data?.[0]; const last = sessions.data?.find(s => s.closed_at);
  const toReview = (days.data || []).filter(d => d.state === 'pending' || d.state === 'outdated');
  return <>
    <PageHeading title="Caixa" description="Abertura, fechamento com os totais do dia e conferência diária." onRefresh={() => void refresh()} />
    <ErrorNote errors={[sessions.error, days.error]} />
    <div className="stat-grid">
      <div className="panel stat"><span>Caixa agora</span><strong>{open ? `Aberto por ${open.opened_by}` : 'Fechado'}</strong><small>{open ? `${dateTime(open.opened_at)} · troco ${money(open.opening_cents)}` : 'Abra com o troco contado'}</small></div>
      <div className="panel stat"><span>Último fechamento</span><strong className={last?.difference_cents ? 'danger-text' : ''}>{last?.closed_at ? (last.difference_cents ? `Diferença ${money(last.difference_cents)}` : 'Sem diferença') : '—'}</strong><small>{last?.closed_at ? `${dateTime(last.closed_at)} · contado ${money(last.counted_cents || 0)}` : ''}</small></div>
      <div className="panel stat"><span>Dias a conferir (14 dias)</span><strong className={toReview.length ? 'warn-text' : ''}>{toReview.length}</strong><small>Registre a conferência de cada dia</small></div>
    </div>
    <div className="forms-grid">
      <RecordForm title="Abrir caixa" fields={[{ name: 'opened_by', label: 'Quem abriu' }, { name: 'opened_at', label: 'Data e hora', type: 'datetime-local', value: localNow() }, { name: 'opening_cents', label: 'Troco contado (R$)', type: 'number', min: 0 }, { name: 'note', label: 'Observações', required: false }]}
        onSubmit={v => send('/cash-sessions', { ...v, opened_at: instant(v.opened_at), opening_cents: cents(v.opening_cents) }, refresh)} />
      <RecordForm title="Fechar caixa" fields={[{ name: 'closed_by', label: 'Quem fechou' }, { name: 'closed_at', label: 'Data e hora', type: 'datetime-local', value: localNow() },
        { name: 'cash_sales_cents', label: 'Vendas em dinheiro (R$)', type: 'number', min: 0 }, { name: 'pix_cents', label: 'Vendas no Pix (R$)', type: 'number', min: 0, value: '0' }, { name: 'card_cents', label: 'Vendas no cartão (R$)', type: 'number', min: 0, value: '0' },
        { name: 'withdrawals_cents', label: 'Retiradas e pagamentos em dinheiro (R$)', type: 'number', min: 0, value: '0', hint: 'Dinheiro levado ao cofre/banco ou usado para pagar algo.' }, { name: 'counted_cents', label: 'Dinheiro contado na gaveta (R$)', type: 'number', min: 0 }, { name: 'note', label: 'Observações', required: false }]}
        onSubmit={v => { if (!open) throw new Error('Não há caixa aberto.'); return send(`/cash-sessions/${open.id}/close`, { closed_by: v.closed_by, closed_at: instant(v.closed_at), note: v.note, ...Object.fromEntries(['cash_sales_cents', 'pix_cents', 'card_cents', 'withdrawals_cents', 'counted_cents'].map(k => [k, cents(v[k])])) }, refresh); }} />
      <RecordForm title="Registrar conferência do dia" fields={[{ name: 'day', label: 'Dia', options: toReview.map(d => ({ value: d.day, label: `${weekday(d.day)} ${shortDate(d.day)} · ${d.issues.length ? `${d.issues.length} ponto(s) de atenção` : 'sem apontamentos'}` })) },
        { name: 'status', label: 'Resultado', options: [{ value: 'ok', label: 'Conferido sem ressalvas' }, { value: 'issues', label: 'Conferido com ressalvas' }] }, { name: 'note', label: 'O que foi conferido e encaminhamento', type: 'textarea' }]} onSubmit={v => send('/cash-reviews', v, refresh)} />
      <RecordForm title="Reabrir último caixa para corrigir" fields={[{ name: 'reason', label: 'Motivo' }]} onSubmit={v => { if (!latest?.closed_at) throw new Error('Só é possível reabrir o último caixa, depois de fechado.'); return send(`/cash-sessions/${latest.id}/reopen`, v, refresh); }} />
    </div>
    <div className="notice">Esperado na gaveta = troco + vendas em dinheiro − retiradas. Registre as retiradas <strong>antes</strong> da contagem: o valor contado no fechamento deve ser o troco da abertura seguinte.</div>
    <DataTable title="Conferência diária" rows={(days.data || []).filter(d => d.state !== 'not_applicable')} note={toReview.length ? `${toReview.length} dia(s) aguardando` : 'Em dia'} columns={[
      { label: 'Dia', render: d => <strong className="nowrap">{weekday(d.day)} {shortDate(d.day)}</strong> },
      { label: 'Calendário', render: d => <span className="nowrap">{calendarNames[d.calendar_status]}</span> },
      { label: 'Abertura e fechamento', render: d => d.sessions.length ? d.sessions.map(s => <div key={s.id}>Troco {money(s.opening_cents)} · {s.closed_at ? <>contado {money(s.counted_cents || 0)}{s.difference_cents ? <span className="danger-text"> ({money(s.difference_cents)})</span> : null}</> : 'em aberto'}</div>) : '—' },
      { label: 'Vendas', render: d => <div className="nowrap">Dinheiro {money(d.cash_sales_cents)}<div className="muted">Pix {money(d.pix_cents)}</div><div className="muted">Cartão {money(d.card_cents)}</div></div> },
      { label: 'Pontos de atenção', render: d => d.issues.length ? <ul className="issue-list">{d.issues.map(i => <li key={i}>{i}</li>)}</ul> : <span className="muted">Nenhum</span> },
      { label: 'Conferência', render: d => <><Badge tone={stateTone[d.state]}>{d.state_label}</Badge>{d.review && <small className="muted block">{d.review.status === 'ok' ? 'Sem ressalvas' : 'Com ressalvas'}: {d.review.note}</small>}</> },
    ]} />
    <DataTable title="Aberturas e fechamentos" rows={sessions.data || []} columns={[{ label: 'Abertura', render: s => `${dateTime(s.opened_at)} · ${s.opened_by}` }, { label: 'Troco', render: s => money(s.opening_cents) },
      { label: 'Fechamento', render: s => s.closed_at ? `${dateTime(s.closed_at)} · ${s.closed_by}` : 'Em aberto' }, { label: 'Esperado', render: s => s.expected_cents === null ? '—' : money(s.expected_cents) },
      { label: 'Contado', render: s => s.counted_cents === null ? '—' : money(s.counted_cents) }, { label: 'Diferença', render: s => s.difference_cents === null ? '—' : <span className={s.difference_cents ? 'danger-text' : ''}>{money(s.difference_cents)}</span> }, { label: 'Observações', render: s => s.note || '—' }]} />
  </>;
}
