import { useEffect, useState } from 'react';
import type { InputHTMLAttributes } from 'react';
import type { CashDay, DemoState, Draft, Scenario, Session } from './data';
import { blankDraft, cents, dateLabel, draftFromDay, loadDraft, makeDay, shift, storeDraft, TODAY } from './data';
import { Difference, Field, focusError, Heading, Link, money, Notice } from './components';
import type { Errors } from './components';
import { dayStatus } from './Today';

type Props = { state: DemoState; scenario: Scenario; segment: string; update: (state: DemoState) => void };
const saleFields = [['cash', 'Dinheiro'], ['pix', 'Pix'], ['card', 'Cartão'], ['voucher', 'Voucher']] as const;
const STEPS = ['Abertura e fechamento', 'Vendas do dia', 'Dinheiro na gaveta'];
const OPEN_AT = '07:30', CLOSE_AT = '22:00';
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const short = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const clock = (time: string) => time.replace(':', 'h');

/** Campo de valor em reais, com o "R$" fixo à esquerda para ninguém digitar o símbolo. */
function MoneyField({ label, error, hint, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string; id: string }) {
  const descriptions = [error ? `${id}-error` : '', hint ? `${id}-hint` : ''].filter(Boolean).join(' ') || undefined;
  return <div className="p-field"><label htmlFor={id}>{label}</label><div className="r-money"><span aria-hidden="true">R$</span><input {...props} id={id} inputMode="decimal" autoComplete="off" placeholder="0,00" aria-invalid={!!error} aria-describedby={descriptions} /></div>{hint && <small id={`${id}-hint`}>{hint}</small>}{error && <p id={`${id}-error`} className="p-error">{error}</p>}</div>;
}

/** Cupom ao lado do formulário: vai se preenchendo enquanto a pessoa digita. */
function Receipt({ draft, total, expected, difference, step }: { draft: Draft; total: number | null; expected: number | null; difference: number | null; step: number }) {
  const value = (text: string) => { const n = cents(text); return n === null ? <span className="r-blank">—</span> : money(n); };
  const who = (time: string, name: string) => [time && clock(time), name.trim()].filter(Boolean).join(', ') || <span className="r-blank">—</span>;
  return <aside className={`r-receipt${step === 1 ? ' r-first' : ''}`} aria-label="Resumo do registro">
    <p className="r-receipt-day">{draft.day ? cap(dateLabel(draft.day)) : 'Dia ainda não escolhido'}</p>
    <dl className={`r-block${step === 1 ? ' r-current' : step > 1 ? ' r-past' : ''}`}>
      <div><dt>Abertura</dt><dd>{who(draft.opening_time, draft.opened_by)}</dd></div>
      <div><dt>Fechamento</dt><dd>{who(draft.closing_time, draft.closed_by)}</dd></div>
      <div><dt>Troco</dt><dd>{value(draft.opening)}</dd></div>
    </dl>
    <dl className={`r-block${step === 2 ? ' r-current' : step > 2 ? ' r-past' : ''}`}>
      {saleFields.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{value(draft[key])}</dd></div>)}
      <div className="r-sum"><dt>Total das vendas</dt><dd>{total === null ? <span className="r-blank">—</span> : money(total)}</dd></div>
    </dl>
    <dl className={`r-block${step === 3 ? ' r-current' : step > 3 ? ' r-past' : ''}`}>
      <div><dt>Retirado</dt><dd>{value(draft.withdrawn)}</dd></div>
      <div><dt>Deveria ficar</dt><dd>{expected === null ? <span className="r-blank">—</span> : money(expected)}</dd></div>
      <div><dt>Contado</dt><dd>{value(draft.drawer)}</dd></div>
      <div className={`r-sum${difference ? ' r-off' : difference === 0 ? ' r-even' : ''}`}><dt>Gaveta</dt><dd>{difference === null ? <span className="r-blank">—</span> : difference === 0 ? 'Bateu' : `${difference < 0 ? 'Faltaram' : 'Sobraram'} ${money(Math.abs(difference))}`}</dd></div>
    </dl>
  </aside>;
}

export default function DailyFlow({ state, scenario, segment, update }: Props) {
  const [draft, setDraft] = useState<Draft>(() => loadDraft(scenario) || blankDraft());
  const [editing, setEditing] = useState(() => !!draft.correction_day && draft.correction_day === draft.day);
  const [errors, setErrors] = useState<Errors>({});
  const [storageFailed, setStorageFailed] = useState(false);
  const reason = draft.correction_reason;
  const step = ['1', '2', '3'].includes(segment) ? Number(segment) : 1;
  const resume = segment === 'start' && loadDraft(scenario) !== null;
  const existing = state.cash_days.find(d => d.day === draft.day);
  const duplicate = existing && !editing;
  const latest = state.cash_days.map(d => d.day).sort().at(-1);
  const change = (key: keyof Draft, value: string | boolean) => {
    const next = { ...draft, [key]: value };
    setDraft(next); setStorageFailed(!storeDraft(scenario, next));
    setErrors(e => { const copy = { ...e }; delete copy[key]; return copy; });
    if (key === 'day') setEditing(false);
  };
  useEffect(() => { if (segment === 'start' && !loadDraft(scenario)) location.replace('#daily/1'); }, [segment, scenario]);
  useEffect(() => { setErrors({}); }, [segment]);
  function validate(at: number): Errors {
    const e: Errors = {};
    if (at === 1) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.day) || draft.day > TODAY) e.day = 'Escolha o dia do resumo, até 10/11/2026.';
      if (cents(draft.opening) === null) e.opening = 'Informe o troco contado, mesmo quando for zero.';
      if (draft.opened_by.trim().length < 2) e.opened_by = 'Informe o nome de quem abriu o caixa.';
      if (draft.closed_by.trim().length < 2) e.closed_by = 'Informe o nome de quem fechou o caixa.';
      if (draft.opening_time && draft.closing_time && draft.closing_time < draft.opening_time) e.closing_time = 'O fechamento deve ser posterior à abertura.';
    }
    if (at === 2) for (const [key] of saleFields) if (cents(draft[key]) === null) e[key] = 'Informe um valor em reais. Use 0 somente se não houve recebimento.';
    if (at === 3) {
      if (cents(draft.withdrawn) === null) e.withdrawn = 'Confirme quanto foi retirado. Campo vazio não significa zero.';
      if (cents(draft.drawer) === null) e.drawer = 'Informe quanto foi contado na gaveta.';
      const expected = cents(draft.opening)! + cents(draft.cash)! - cents(draft.withdrawn)!;
      if (Number.isFinite(expected) && expected < 0) e.withdrawn = 'As retiradas superam o troco mais as vendas em dinheiro.';
      if (difference !== null && difference !== 0 && draft.note.trim().length < 3) e.note = 'Descreva o que foi apurado sobre a diferença e o encaminhamento.';
      if (!draft.confirmed) e.confirmed = 'Confirme que comparou os valores com o resumo da equipe.';
      if (editing && reason.trim().length < 3) e.correction_reason = 'Informe o motivo da correção.';
    }
    return e;
  }
  function proceed(next: number) {
    const e = validate(step); setErrors(e);
    if (Object.keys(e).length) { focusError(e); return; }
    if (duplicate) return;
    storeDraft(scenario, draft); location.hash = `daily/${next}`;
  }
  const values = saleFields.map(([key]) => cents(draft[key]));
  const total = values.every(v => v !== null) ? values.reduce<number>((n, v) => n + v!, 0) : null;
  const opening = cents(draft.opening), cash = cents(draft.cash), withdrawn = cents(draft.withdrawn), drawer = cents(draft.drawer);
  const expected = opening !== null && cash !== null && withdrawn !== null ? opening + cash - withdrawn : null;
  const difference = expected !== null && drawer !== null ? drawer - expected : null;
  function save() {
    for (const at of [1, 2, 3]) {
      const e = validate(at);
      if (Object.keys(e).length) { location.hash = `daily/${at}`; setTimeout(() => { setErrors(e); focusError(e); }, 0); return; }
    }
    if (existing && (!editing || existing.day !== latest)) { setErrors({ day: 'Esse dia já foi registrado. Abra o dia para conferir as opções.' }); location.hash = 'daily/1'; return; }
    const session: Session = {
      id: existing?.sessions[0].id || Date.now(), opened_at: draft.opening_time ? `${draft.day}T${draft.opening_time}:00-03:00` : '',
      closed_at: draft.closing_time ? `${draft.day}T${draft.closing_time}:00-03:00` : null,
      opened_by: draft.opened_by.trim(), closed_by: draft.closed_by.trim(), opening_cents: opening!, cash_sales_cents: cash!,
      pix_cents: cents(draft.pix)!, card_cents: cents(draft.card)!, voucher_cents: cents(draft.voucher)!, withdrawals_cents: withdrawn!,
      counted_cents: drawer!, expected_cents: expected!, difference_cents: difference!, note: editing ? `Correção: ${reason}. ${draft.note}` : draft.note,
    };
    const day: CashDay = makeDay(draft.day, session, true);
    update({ ...state, cash_days: [day, ...state.cash_days.filter(d => d.day !== day.day)].sort((a, b) => b.day.localeCompare(a.day)),
      meta: { ...state.meta, reported_times: { ...state.meta.reported_times, [day.day]: { opening: draft.opening_time, closing: draft.closing_time } } } });
    storeDraft(scenario, null); location.hash = `day/${day.day}/saved`;
  }
  if (resume) return <><Heading title="Continuar o registro?" description="Há um rascunho de exemplo guardado neste navegador." back="cash" /><div className="p-card"><p>{draft.day ? `Dia escolhido: ${draft.day.split('-').reverse().join('/')}.` : 'O dia ainda não foi escolhido.'} Nada foi enviado ao sistema.</p><div className="p-actions"><Link to="daily/1" primary>Continuar rascunho</Link><button className="p-button p-secondary" onClick={() => { storeDraft(scenario, null); setDraft(blankDraft()); setEditing(false); location.hash = 'daily/1'; }}>Começar de novo</button></div></div></>;

  // Atalhos de dia: hoje e os dias de funcionamento recentes que ainda não têm registro.
  const suggestions = Array.from({ length: 10 }, (_, i) => shift(TODAY, -i))
    .filter(d => dayStatus(state, d).open && !state.cash_days.some(c => c.day === d)).slice(0, 3);
  const lateOpen = draft.opening_time && draft.opening_time > OPEN_AT, earlyClose = draft.closing_time && draft.closing_time < CLOSE_AT;
  const closedDay = draft.day && !dayStatus(state, draft.day).open ? dayStatus(state, draft.day).reason : '';

  return <>
    <Heading title={draft.day ? `Registrar ${dateLabel(draft.day).split(',')[0]}, ${short(draft.day)}` : 'Registrar um dia'} description={['Comece pelo dia e por quem abriu e fechou o caixa. Use o resumo que a equipe mandou.', 'Copie do resumo quanto entrou em cada forma de pagamento. A soma é feita aqui.', 'Informe o que foi retirado e quanto foi contado. A conta da gaveta aparece na hora.'][step - 1]} back={step === 1 ? 'home' : `daily/${step - 1}`} />
    <ol className="p-steps" aria-label="Etapas">{STEPS.map((label, i) => <li key={label} aria-current={step === i + 1 ? 'step' : undefined} className={step > i + 1 ? 'r-step-done' : undefined}><span>{i + 1}</span>{label}</li>)}</ol>
    {storageFailed && <Notice danger>Não foi possível guardar o rascunho neste navegador. Mantenha a página aberta para não perder o preenchimento.</Notice>}
    {step > 1 && !draft.day ? <Notice>Este link aponta para uma etapa sem rascunho neste navegador. <Link to="daily/1">Começar pelo dia</Link></Notice> : <div className="r-layout">
      <form noValidate onSubmit={e => { e.preventDefault(); if (step < 3) proceed(step + 1); else save(); }} className="p-card p-form r-form">
        {Object.keys(errors).length > 0 && <p role="alert" className="p-error-summary">Revise os campos indicados. O que você digitou foi mantido.</p>}
        {step === 1 && <>
          <fieldset className="r-group">
            <legend>Qual dia</legend>
            {suggestions.length > 0 && <div className="r-chips" role="group" aria-label="Dias sem registro">{suggestions.map(d => <button type="button" key={d} className="r-chip" aria-pressed={draft.day === d} onClick={() => change('day', d)}>{d === TODAY ? 'Hoje' : cap(dateLabel(d).split(',')[0])}, {short(d)}</button>)}</div>}
            <Field id="day" label={suggestions.length ? 'Ou escolha outro dia' : 'Dia do resumo'} type="date" max={TODAY} value={draft.day} error={errors.day} onChange={e => change('day', e.target.value)} />
            {closedDay && <p className="r-warn">Pelo calendário, a cantina estava fechada neste dia ({closedDay}). Confira a data antes de continuar.</p>}
            {duplicate && <Notice><h2>Esse dia já foi registrado</h2><p>Não vamos criar outro registro para o mesmo dia.</p><div className="p-actions"><Link to={`day/${existing.day}`} primary>Abrir dia</Link>{existing.day === latest && <button type="button" className="p-button p-secondary" onClick={() => { const next = draftFromDay(existing, state.meta); setDraft(next); storeDraft(scenario, next); setEditing(true); }}>Corrigir último fechamento</button>}</div>{existing.day !== latest && <p className="p-small">Somente o último caixa fechado pode ser reaberto, conforme a regra atual.</p>}</Notice>}
          </fieldset>
          <fieldset className="r-group">
            <legend>Abertura <small>contrato: {clock(OPEN_AT)}</small></legend>
            <div className="p-fields r-fields-3">
              <Field id="opened_by" label="Quem abriu" autoComplete="off" value={draft.opened_by} error={errors.opened_by} onChange={e => change('opened_by', e.target.value)} />
              <Field id="opening_time" type="time" label="Abriu às" hint="Deixe vazio se não souber." value={draft.opening_time} onChange={e => change('opening_time', e.target.value)} />
              <MoneyField id="opening" label="Troco na gaveta" value={draft.opening} error={errors.opening} onChange={e => change('opening', e.target.value)} />
            </div>
            {lateOpen && <p className="r-warn">Abriu depois das {clock(OPEN_AT)} do contrato. Isso fica anotado no dia.</p>}
          </fieldset>
          <fieldset className="r-group">
            <legend>Fechamento <small>contrato: {clock(CLOSE_AT)}</small></legend>
            <div className="p-fields r-fields-3">
              <Field id="closed_by" label="Quem fechou" autoComplete="off" value={draft.closed_by} error={errors.closed_by} onChange={e => change('closed_by', e.target.value)} />
              <Field id="closing_time" type="time" label="Fechou às" hint="Deixe vazio se não souber." value={draft.closing_time} error={errors.closing_time} onChange={e => change('closing_time', e.target.value)} />
            </div>
            {earlyClose && <p className="r-warn">Fechou antes das {clock(CLOSE_AT)} do contrato. Isso fica anotado no dia.</p>}
          </fieldset>
        </>}
        {step === 2 && <>
          <div className="p-fields">{saleFields.map(([key, label]) => <MoneyField key={key} id={key} label={label} value={draft[key]} error={errors[key]} onChange={e => change(key, e.target.value)} />)}</div>
          <div className={`p-total${total === null ? ' p-empty-total' : ''}`} role="status"><span>Total das vendas</span><strong>{total === null ? 'Falta informar' : money(total)}</strong></div>
          <p className="p-small">Use 0 quando tiver certeza de que não entrou nada naquela forma.</p>
        </>}
        {step === 3 && <>
          <div className="p-fields">
            <MoneyField id="withdrawn" label="Dinheiro retirado" hint="Sangrias e pagamentos feitos com o dinheiro da gaveta. Use 0 se não houve." value={draft.withdrawn} error={errors.withdrawn} onChange={e => change('withdrawn', e.target.value)} />
            <MoneyField id="drawer" label="Dinheiro contado na gaveta" hint="O que sobrou na gaveta no fechamento." value={draft.drawer} error={errors.drawer} onChange={e => change('drawer', e.target.value)} />
          </div>
          <dl className="p-facts r-math">
            <div><dt>Troco da abertura</dt><dd>{opening === null ? '—' : money(opening)}</dd></div>
            <div><dt>+ Vendas em dinheiro</dt><dd>{cash === null ? '—' : money(cash)}</dd></div>
            <div><dt>− Dinheiro retirado</dt><dd>{withdrawn === null ? '—' : money(withdrawn)}</dd></div>
            <div className="r-math-sum"><dt>Deveria ter na gaveta</dt><dd>{expected === null ? '—' : money(expected)}</dd></div>
          </dl>
          <Difference difference={difference} />
          {(!draft.opening_time || !draft.closing_time) && <p className="p-small p-hour-status">Sem os horários reais, a conferência do horário do contrato fica pendente neste dia.</p>}
          <div className="p-field"><label htmlFor="note">{difference ? 'O que foi apurado e o que será feito?' : 'Observação (opcional)'}</label><textarea id="note" value={draft.note} aria-invalid={!!errors.note} aria-describedby={errors.note ? 'note-error' : undefined} onChange={e => change('note', e.target.value)} />{errors.note && <p id="note-error" className="p-error">{errors.note}</p>}</div>
          {editing && <Field id="correction_reason" label="Motivo da correção" value={reason} error={errors.correction_reason} onChange={e => change('correction_reason', e.target.value)} />}
          <div className="p-field"><label className="p-check" htmlFor="confirmed"><input type="checkbox" id="confirmed" checked={draft.confirmed} aria-invalid={!!errors.confirmed} aria-describedby={errors.confirmed ? 'confirmed-error' : undefined} onChange={e => change('confirmed', e.target.checked)} />Conferi os valores com o resumo da equipe.</label>{errors.confirmed && <p id="confirmed-error" className="p-error">{errors.confirmed}</p>}</div>
        </>}
        <div className="p-form-footer"><span className="p-small">Rascunho guardado neste navegador enquanto você preenche</span><button className="p-button p-primary" type="submit" disabled={!!duplicate}>{step === 3 ? 'Salvar o dia' : `Continuar para ${STEPS[step].toLowerCase()}`}</button></div>
      </form>
      <Receipt draft={draft} total={total} expected={expected} difference={difference} step={step} />
    </div>}
  </>;
}
