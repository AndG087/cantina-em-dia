import type { InputHTMLAttributes, ReactNode } from 'react';
import { money, count } from '../components/ui';
export { money, count };
export type Errors = Record<string, string>;
export function Field({ label, error, hint, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string; id: string }) {
  const descriptions = [error ? `${id}-error` : '', hint ? `${id}-hint` : ''].filter(Boolean).join(' ') || undefined;
  return <div className="p-field"><label htmlFor={id}>{label}</label><input {...props} id={id} aria-invalid={!!error} aria-describedby={descriptions} />{hint && <small id={`${id}-hint`}>{hint}</small>}{error && <p id={`${id}-error`} className="p-error">{error}</p>}</div>;
}
export function Link({ to, children, primary = false, quiet = false }: { to: string; children: ReactNode; primary?: boolean; quiet?: boolean }) {
  return <a className={primary ? 'p-button p-primary' : quiet ? 'p-link' : 'p-button p-secondary'} href={`#${to}`}>{children}</a>;
}
export function Heading({ title, description, back }: { title: string; description?: string; back?: string }) {
  return <>{back && <Link to={back} quiet>← Voltar</Link>}<div className="p-heading"><h1 tabIndex={-1} data-page-title>{title}</h1>{description && <p>{description}</p>}</div></>;
}
export function Empty({ children }: { children: ReactNode }) { return <div className="p-empty">{children}</div>; }
export function Notice({ children, danger = false }: { children: ReactNode; danger?: boolean }) { return <div className={`p-notice${danger ? ' p-danger' : ''}`}>{children}</div>; }
export function Difference({ difference }: { difference: number | null }) {
  return <div className={`p-total${difference === null ? ' p-empty-total' : difference ? ' p-warning' : ' p-ok'}`} role="status"><span>{difference === null ? 'Falta informar os valores' : difference < 0 ? 'Faltou dinheiro na gaveta' : difference > 0 ? 'Sobrou dinheiro na gaveta' : 'A gaveta bateu'}</span><strong>{difference === null ? '—' : money(Math.abs(difference))}</strong></div>;
}
export function focusError(errors: Errors) {
  const id = Object.keys(errors)[0];
  requestAnimationFrame(() => {
    const field = document.getElementById(id);
    if (!field) return;
    let ancestor = field.parentElement;
    while (ancestor) { if (ancestor instanceof HTMLDetailsElement) ancestor.open = true; ancestor = ancestor.parentElement; }
    field.focus(); field.scrollIntoView({ block: 'center', behavior: 'smooth' });
  });
}
