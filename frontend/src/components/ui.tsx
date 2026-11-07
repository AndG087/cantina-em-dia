import { useCallback, useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { api } from '../api';

export function useRemote<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    try { setData(await api<T>(path)); setError(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Falha ao carregar.'); }
    finally { setLoading(false); }
  }, [path]);
  useEffect(() => { void refresh(); }, [refresh]);
  return { data, error, loading, refresh };
}

export const money = (cents: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
export function cents(value: unknown) { const text = String(value).replace(',', '.'); if (!/^\d+(\.\d{1,2})?$/.test(text)) throw new Error('Informe o valor em reais com até duas casas decimais.'); const [whole, part = ''] = text.split('.'); return Number(whole) * 100 + Number(part.padEnd(2, '0')); }
export const count = (value: string | number) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(Number(value));
export const dateTime = (value?: string | null) => value ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date(value)) : '—';
export function localNow() { return new Date(Date.now() - 3 * 3600000).toISOString().slice(0, 16); }
export function instant(value: unknown) { return `${String(value)}:00-03:00`; }
export type Values = Record<string, string | boolean>;
export type Field = { name: string; label: string; type?: string; required?: boolean; options?: { value: string | number; label: string }[]; value?: string; min?: string | number; max?: string | number; step?: string; hint?: string };
export function RecordForm({ title, fields, onSubmit, submit = 'Salvar registro' }: { title: string; fields: Field[]; onSubmit: (values: Values) => Promise<void>; submit?: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(false);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget;
    const values: Values = Object.fromEntries(new FormData(form).entries()) as Values;
    fields.filter(f => f.type === 'checkbox').forEach(f => { values[f.name] = new FormData(form).has(f.name); });
    setBusy(true); setMessage('');
    try { await onSubmit(values); form.reset(); setError(false); setMessage('Registro salvo.'); }
    catch (e) { setError(true); setMessage(e instanceof Error ? e.message : 'Não foi possível salvar.'); }
    finally { setBusy(false); }
  }
  return <details className="panel record-form"><summary>{title}<span>Adicionar / editar</span></summary><form onSubmit={save}><div className="operation-fields">{fields.map(f => <label key={f.name}>{f.label}{f.options ? <select name={f.name} required={f.required !== false} defaultValue={f.value || ''}><option value="">Selecione…</option>{f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select> : f.type === 'textarea' ? <textarea name={f.name} required={f.required !== false} defaultValue={f.value} maxLength={1000} /> : <input name={f.name} type={f.type || 'text'} defaultValue={f.value} required={f.type !== 'checkbox' && f.required !== false} min={f.min} max={f.max} step={f.step || (f.type === 'number' ? '0.01' : undefined)} maxLength={f.type === 'text' || !f.type ? 300 : undefined} />}{f.hint && <small>{f.hint}</small>}</label>)}</div><div className="operation-form-foot">{message && <span role={error ? 'alert' : 'status'} className={error ? 'form-error' : 'success-message'}>{message}</span>}<button className="button primary" disabled={busy} type="submit">{busy && <Loader2 className="spin" size={15} />}{busy ? 'Salvando…' : submit}</button></div></form></details>;
}
export function DataTable<T>({ title, rows, columns }: { title: string; rows: T[]; columns: { label: string; render: (row: T) => ReactNode }[] }) {
  return <section className="panel data-panel"><h2>{title}<span>{rows.length} registros</span></h2><div className="table-scroll"><table><thead><tr>{columns.map(c => <th key={c.label}>{c.label}</th>)}</tr></thead><tbody>{rows.length ? rows.map((row, index) => <tr key={index}>{columns.map(c => <td key={c.label}>{c.render(row)}</td>)}</tr>) : <tr><td colSpan={columns.length} className="empty-cell">Nenhum registro. Cadastre as informações reais da cantina para começar.</td></tr>}</tbody></table></div></section>;
}
export function ModuleHeading({ title, description, onRefresh }: { title: string; description: string; onRefresh: () => void }) {
  return <div className="page-heading"><div><span className="eyebrow">GESTÃO DA CANTINA</span><h1>{title}</h1><p>{description}</p></div><button className="button secondary" onClick={onRefresh}><RefreshCw size={15} />Atualizar</button></div>;
}
export function ErrorNote({ errors }: { errors: (string | undefined)[] }) {
  const found = errors.filter(Boolean); return found.length ? <div className="error-banner" role="alert">{[...new Set(found)].join(' ')}</div> : null;
}
export async function save(path: string, data: unknown, refresh: () => Promise<unknown>, method = 'POST') {
  await api(path, { method, body: JSON.stringify(data) }); await refresh();
}
