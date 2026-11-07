import { useState } from 'react';
import { api } from '../api';
import type { CashSession } from './CashPage';
import { DataTable, ModuleHeading, ErrorNote, useRemote, dateTime } from '../components/ui';
type Configuration = { kinds: Record<string, { label: string; required: string[]; optional: string[] }>; labels: Record<string, string> };
type Preview = { row_count: number; sha256: string; sample: Record<string, string>[]; kind: string };
export default function ImportsPage() {
  const config = useRemote<Configuration>('/imports/config');
  const history = useRemote<{ id: number; kind: string; filename: string; row_count: number; recorded_at: string }[]>('/imports');
  const cash = useRemote<CashSession[]>('/cash-sessions');
  const [kind, setKind] = useState('items'); const [content, setContent] = useState(''); const [filename, setFilename] = useState('');
  const [headers, setHeaders] = useState<string[]>([]); const [mapping, setMapping] = useState<Record<string, string>>({});
  const [cashId, setCashId] = useState(''); const [encoding, setEncoding] = useState('utf-8');
  const [preview, setPreview] = useState<Preview | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState('');
  async function refresh() { await Promise.all([config.refresh(), history.refresh(), cash.refresh()]); }
  async function readFile(file?: File) {
    setPreview(null); setError(''); setMessage('');
    if (!file) return;
    if (file.size > 2_000_000) { setError('Selecione um CSV com até 2 MB e 2.000 linhas.'); return; }
    setBusy(true);
    try {
      const text = new TextDecoder(encoding).decode(await file.arrayBuffer());
      const inspected = await api<{ headers: string[]; row_count: number }>('/imports/inspect', { method: 'POST', body: JSON.stringify({ content: text }) });
      setContent(text); setFilename(file.name); setHeaders(inspected.headers); setMapping({});
    } catch (e) { setContent(''); setHeaders([]); setError(e instanceof Error ? e.message : 'Falha ao ler o arquivo.'); }
    finally { setBusy(false); }
  }
  function request() { return { kind, content, filename, mapping, cash_session_id: cashId ? Number(cashId) : null }; }
  async function validate() {
    setBusy(true); setError(''); setMessage(''); setPreview(null);
    try { setPreview(await api<Preview>('/imports/preview', { method: 'POST', body: JSON.stringify(request()), signal: AbortSignal.timeout(120000) })); }
    catch (e) { setError(e instanceof Error ? e.message : 'Falha na validação.'); }
    finally { setBusy(false); }
  }
  async function commit() {
    if (!preview) return;
    setBusy(true); setError('');
    try {
      const result = await api<{ id: number; row_count: number }>('/imports/commit', { method: 'POST', body: JSON.stringify({ ...request(), expected_hash: preview.sha256 }), signal: AbortSignal.timeout(120000) });
      setMessage(`Importação #${result.id} concluída: ${result.row_count} registros. Os dados ficaram salvos no PostgreSQL.`); setPreview(null); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Falha ao importar.'); }
    finally { setBusy(false); }
  }
  const selected = config.data?.kinds[kind];
  return <><ModuleHeading title="Importação de CSV" description="Selecione as colunas, confira a prévia e importe registros com referências únicas." onRefresh={() => void refresh()} /><ErrorNote errors={[config.error, history.error, cash.error, error]} />
    <div className="notice">Não há conexão automática com a Stone. Use o CSV exportado e confirme o significado das colunas. Um resumo financeiro não baixa produtos do estoque; vendas por produto precisam de código, quantidade e preço unitário.</div>
    <section className="panel import-panel"><h2>1. Escolher o arquivo e o tipo de registro</h2><div className="operation-fields"><label>Tipo de importação<select value={kind} onChange={e => { setKind(e.target.value); setMapping({}); setPreview(null); setMessage(''); }}>{Object.entries(config.data?.kinds || {}).map(([key, value]) => <option value={key} key={key}>{value.label}</option>)}</select></label><label>Codificação do arquivo<select value={encoding} onChange={e => { setEncoding(e.target.value); setContent(''); setHeaders([]); setPreview(null); }}><option value="utf-8">UTF-8</option><option value="windows-1252">Windows-1252 / Excel antigo</option></select></label><label>Arquivo CSV (até 2 MB)<input type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values" disabled={busy} onChange={e => void readFile(e.target.files?.[0])} /></label><label>Caixa para registros em dinheiro<select value={cashId} onChange={e => { setCashId(e.target.value); setPreview(null); }}><option value="">Sem caixa — apenas digital</option>{(cash.data || []).filter(c => !c.closed_at).map(c => <option key={c.id} value={c.id}>Caixa #{c.id} · {dateTime(c.opened_at)}</option>)}</select></label></div><div className="operation-form-foot"><a className="button secondary" href={`/api/imports/template/${kind}`}>Baixar modelo de cabeçalho</a><span>{filename || 'Nenhum arquivo carregado'}</span></div></section>
    {headers.length > 0 && selected && <section className="panel import-panel"><h2>2. Conferir as colunas</h2><div className="operation-fields">{[...selected.required, ...selected.optional].map(field => <label key={field}>{config.data?.labels[field]}{selected.required.includes(field) ? ' *' : ' (opcional)'}<select value={mapping[field] ?? (headers.includes(field) ? field : '')} onChange={e => { setMapping({ ...mapping, [field]: e.target.value }); setPreview(null); }}><option value="">Selecione a coluna…</option>{headers.map(h => <option key={h} value={h}>{h}</option>)}</select></label>)}</div><div className="operation-form-foot"><button className="button primary" disabled={busy || !content} onClick={() => void validate()}>{busy ? 'Validando…' : 'Validar e mostrar prévia'}</button></div></section>}
    <div className="notice">Datas sem fuso são interpretadas em Brasília. Para dinheiro, informe também o horário dentro do caixa aberto. Use referências externas únicas e duráveis; cada linha de vendas por produto representa um registro desse produto. Para valores monetários, informe reais com até duas casas decimais. Tipos de item: product, ingredient, packaging. Unidades: un, kg, L.</div>
    {preview && <><DataTable title={`3. Prévia validada — ${preview.row_count} linhas (primeiras 10 abaixo)`} rows={preview.sample} columns={Object.keys(preview.sample[0] || {}).map(key => ({ label: config.data?.labels[key] || key, render: (row: Record<string, string>) => row[key] || '—' }))} /><div className="import-confirm"><span>A validação não gravou lançamentos. A importação será conferida novamente antes de salvar.</span><button className="button primary" disabled={busy} onClick={() => void commit()}>{busy ? 'Importando…' : `Importar ${preview.row_count} linhas`}</button></div></>}
    {message && <div className="notice" role="status">{message}</div>}
    <DataTable title="Histórico de importações" rows={history.data || []} columns={[{ label: 'ID / arquivo', render: h => `#${h.id} · ${h.filename}` }, { label: 'Tipo', render: h => config.data?.kinds[h.kind]?.label || h.kind }, { label: 'Registros', render: h => h.row_count }, { label: 'Quando', render: h => dateTime(h.recorded_at) }, { label: 'Origem preservada', render: h => <a className="text-button" href={`/api/imports/${h.id}/source`}>Baixar conteúdo original</a> }]} />
  </>;
}
