import { useState } from 'react';
import { api } from '../api';
import { Composer, DataTable, ErrorNote, ModuleHeading, RecordForm, dateTime, save, useRemote } from '../components/ui';

type Config = { entities: Record<string, string>; extensions: string[]; max_bytes: number };
type Attachment = { id: number; entity: string; entity_id: number; original_name: string; size_bytes: number; note: string; created_at: string; archived_at: string | null };

function fileBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new Error('Não foi possível ler o arquivo selecionado.'));
    reader.readAsDataURL(file);
  });
}

export default function AttachmentsPage() {
  const config = useRemote<Config>('/attachments/config');
  const [entity, setEntity] = useState('inbox'); const [destination, setDestination] = useState('inbox');
  const [filter, setFilter] = useState(''); const [filterId, setFilterId] = useState(''); const [archived, setArchived] = useState(false);
  const [image, setImage] = useState<Attachment | null>(null);
  const query = new URLSearchParams({ include_archived: String(archived) });
  if (filter) query.set('entity', filter);
  if (filterId) query.set('entity_id', filterId);
  const records = useRemote<Attachment[]>(`/attachments?${query.toString()}`);
  const targets = useRemote<{ id: number; label: string }[]>(`/attachments/targets?entity=${entity}`);
  const destinationTargets = useRemote<{ id: number; label: string }[]>(`/attachments/targets?entity=${destination}`);
  const options = Object.entries(config.data?.entities || {}).map(([value, label]) => ({ value, label }));
  const rows = records.data || [];
  async function refresh() { await Promise.all([config.refresh(), records.refresh(), targets.refresh(), destinationTargets.refresh()]); }
  return <><ModuleHeading title="Comprovantes e anexos" description="Guarde o que recebeu pelo WhatsApp e vincule ao registro correspondente." onRefresh={() => void refresh()} />
    <ErrorNote errors={[config.error, records.error, targets.error, destinationTargets.error]} />
    <div className="notice">Anexar um comprovante não cria uma venda ou despesa. Primeiro guarde na caixa de recebidos, se necessário; depois faça o lançamento e vincule o arquivo ao ID. Os arquivos ficam neste computador.</div>
    <div className="forms-grid"><Composer title="Guardar arquivo ou mensagem" submit="Salvar anexo" onSubmit={async form => {
      const file = form.get('file');
      if (!(file instanceof File) || !file.size) throw new Error('Selecione um arquivo com conteúdo.');
      if (file.size > (config.data?.max_bytes || 8 * 1024 * 1024)) throw new Error('O arquivo deve ter no máximo 8 MB.');
      await api('/attachments', { method: 'POST', body: JSON.stringify({ filename: file.name, content_base64: await fileBase64(file), entity, entity_id: entity === 'inbox' ? 0 : Number(form.get('entity_id')), note: form.get('note') || '' }), signal: AbortSignal.timeout(30000) });
      await refresh();
    }}><div className="operation-fields"><label>Tipo de registro<select value={entity} onChange={e => setEntity(e.target.value)}>{options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
      <label>ID do registro{entity === 'inbox' ? <input value="0" readOnly /> : <input required name="entity_id" type="number" min="1" list="attachment-targets" />}<small>O ID aparece na lista de vendas, despesas ou caixas.</small></label>
      <datalist id="attachment-targets">{(targets.data || []).map(t => <option key={t.id} value={t.id}>{t.label}</option>)}</datalist>
      <label>Arquivo (até 8 MB)<input type="file" name="file" accept={(config.data?.extensions || []).join(',')} required /><small>PDF, imagem, texto UTF-8 ou áudio. Para uma mensagem, salve o texto em .txt ou uma captura em imagem.</small></label><label>Descrição / de quem recebeu<textarea name="note" maxLength={300} placeholder="Ex.: nota enviada pela Dona Gel, referente à compra de segunda-feira" /></label></div></Composer>
      <Composer title="Vincular um anexo a outro registro" onSubmit={async form => { await save(`/attachments/${form.get('id')}/link`, { entity: destination, entity_id: destination === 'inbox' ? 0 : Number(form.get('entity_id')), reason: form.get('reason') }, refresh); }}><div className="operation-fields"><label>Anexo<select name="id" required><option value="">Selecione…</option>{rows.map(r => <option key={r.id} value={r.id}>#{r.id} · {r.original_name}</option>)}</select></label><label>Novo tipo<select value={destination} onChange={e => setDestination(e.target.value)}>{options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label><label>Novo ID{destination === 'inbox' ? <input value="0" readOnly /> : <input name="entity_id" required min="1" type="number" list="attachment-destinations" />}</label><datalist id="attachment-destinations">{(destinationTargets.data || []).map(t => <option key={t.id} value={t.id}>{t.label}</option>)}</datalist><label>Motivo da vinculação<input name="reason" required minLength={3} maxLength={500} /></label></div></Composer>
      <RecordForm title="Arquivar ou recuperar anexo" fields={[{ name: 'id', label: 'Anexo da lista', options: rows.map(r => ({ value: r.id, label: `#${r.id} · ${r.original_name}${r.archived_at ? ' · arquivado' : ''}` })) }, { name: 'action', label: 'Ação', options: [{ value: 'archive', label: 'Arquivar (preservar arquivo e histórico)' }, { value: 'unarchive', label: 'Recuperar anexo arquivado' }] }, { name: 'reason', label: 'Justificativa' }]} onSubmit={v => save(`/attachments/${v.id}/${v.action}`, { reason: v.reason }, refresh)} />
    </div>
    <div className="toolbar"><label>Filtrar tipo<select className="toolbar-input" value={filter} onChange={e => setFilter(e.target.value)}><option value="">Todos</option>{options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label><label>ID<input className="toolbar-input" type="number" min="0" value={filterId} onChange={e => setFilterId(e.target.value)} placeholder="Todos" /></label><label className="check-label"><input type="checkbox" checked={archived} onChange={e => setArchived(e.target.checked)} />Mostrar arquivados</label></div>
    {image && <section className="panel attachment-preview"><div><h2>{image.original_name}</h2><button className="text-button" onClick={() => setImage(null)}>Fechar visualização</button></div><img src={`/api/attachments/${image.id}/preview`} alt={`Comprovante: ${image.original_name}`} onError={() => setImage(null)} /></section>}
    <DataTable title="Arquivos recebidos (últimos 500)" rows={rows} columns={[
      { label: 'Arquivo', render: r => `#${r.id} · ${r.original_name}` }, { label: 'Vínculo', render: r => `${config.data?.entities[r.entity] || r.entity}${r.entity === 'inbox' ? '' : ` #${r.entity_id}`}` },
      { label: 'Recebido', render: r => dateTime(r.created_at) }, { label: 'Descrição', render: r => r.note || '—' },
      { label: 'Tamanho / situação', render: r => `${(r.size_bytes / 1024).toFixed(1)} KB · ${r.archived_at ? 'Arquivado' : 'Ativo'}` },
      { label: 'Abrir', render: r => <div className="attachment-actions"><a className="text-button" href={`/api/attachments/${r.id}/download`}>Baixar</a>{/\.(png|jpe?g|webp)$/i.test(r.original_name) && <button className="text-button" onClick={() => setImage(r)}>Ver imagem</button>}</div> },
    ]} />
  </>;
}
