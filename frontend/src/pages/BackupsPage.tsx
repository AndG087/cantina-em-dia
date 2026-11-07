import { useState } from 'react';
import { api } from '../api';
import { Composer, DataTable, ErrorNote, ModuleHeading, dateTime, useRemote } from '../components/ui';

type Backup = { id: number; filename: string; label: string; size_bytes: number; created_at: string; snapshot_at: string | null; verified_at: string | null; last_restore_database: string | null; last_restored_at: string | null; file_available: boolean };
type Result = { database: string | null; verified: boolean; rows: number; attachments: number; snapshot_at: string };
export default function BackupsPage() {
  const records = useRemote<Backup[]>('/backups'); const config = useRemote<{ max_bytes: number; revision: string; auto_enabled: boolean }>('/backups/config');
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [restored, setRestored] = useState<string | null>(null);
  async function refresh() { await Promise.all([records.refresh(), config.refresh()]); }
  async function create() {
    setBusy(true); setError(''); setMessage('Gerando cópia dos registros e comprovantes…');
    try {
      const result = await api<Backup>('/backups', { method: 'POST', body: '{}', signal: AbortSignal.timeout(180000) });
      setMessage(`Backup #${result.id} criado. Baixe uma cópia para outro local e teste a restauração.`); await refresh();
    } catch (e) { setMessage(''); setError(e instanceof Error ? e.message : 'Não foi possível criar o backup.'); }
    finally { setBusy(false); }
  }
  async function verify(record: Backup) {
    setBusy(true); setError(''); setMessage(`Testando a restauração do backup #${record.id} em um banco temporário…`);
    try {
      const result = await api<Result>(`/backups/${record.id}/verify`, { method: 'POST', body: '{}', signal: AbortSignal.timeout(180000) });
      setMessage(`Teste concluído: ${result.rows} registros e ${result.attachments} comprovantes conferidos. O banco temporário foi removido.`); await refresh();
    } catch (e) { setMessage(''); setError(e instanceof Error ? e.message : 'Não foi possível verificar o backup.'); }
    finally { setBusy(false); }
  }
  const rows = records.data || []; const latest = rows[0];
  return <><ModuleHeading title="Backup e recuperação" description="Guarde uma cópia dos dados e comprovantes e confira se ela pode ser recuperada." onRefresh={() => void refresh()} /><ErrorNote errors={[records.error, config.error, error]} />
    <div className="responsibility-grid"><div className="panel stat-box"><span>Última cópia registrada</span><strong>{latest ? dateTime(latest.snapshot_at || latest.created_at) : 'Nenhuma cópia'}</strong><small>{latest ? latest.file_available ? 'Arquivo encontrado neste computador' : 'Arquivo não encontrado nesta pasta' : 'Crie o primeiro backup'}</small></div><div className="panel stat-box"><span>Último teste dessa cópia</span><strong>{latest?.verified_at ? dateTime(latest.verified_at) : 'Ainda não testado'}</strong><small>Conferência dos registros em outro banco</small></div><div className="panel stat-box"><span>Cópias no histórico</span><strong>{rows.length}</strong><small>Arquivos de até 512 MB neste formato</small></div></div>
    <section className="panel backup-intro"><div><h2>Registros e comprovantes na mesma cópia</h2><p>Inclui estoque, caixa, vendas, despesas, equipe, apurações, arquivos importados e anexos, inclusive arquivados.</p><p>{config.data?.auto_enabled ? 'Ao iniciar com npm.cmd start, uma cópia local é criada na primeira inicialização de cada dia.' : 'A cópia automática na inicialização está desativada; use o botão para criar uma cópia.'} Baixe também para outro dispositivo ou local de sua escolha.</p></div><button className="button primary" onClick={() => void create()} disabled={busy}>{busy ? 'Aguarde…' : 'Criar backup agora'}</button></section>
    {message && <div className="notice" role="status">{message}</div>}
    {restored && <div className="notice"><strong>Cópia restaurada e conferida: <code>{restored}</code></strong><p>Para usar essa cópia, encerre o aplicativo e altere somente o nome do banco em <code>DATABASE_URL</code>, no arquivo <code>.env</code>. Mantenha o usuário, a senha e os outros campos; depois execute <code>npm.cmd start</code>. O banco anterior permanece disponível.</p></div>}
    <div className="forms-grid"><Composer title="Importar uma cópia guardada fora do aplicativo" submit="Importar arquivo de backup" onSubmit={async form => {
      const file = form.get('backup'); if (!(file instanceof File) || !file.size) throw new Error('Selecione um arquivo .zip de backup.');
      if (file.size > (config.data?.max_bytes || 512 * 1024 * 1024)) throw new Error('O arquivo deve ter até 512 MB.');
      await api('/backups/import?filename=' + encodeURIComponent(file.name), { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file, signal: AbortSignal.timeout(180000) }); await refresh();
    }}><div className="operation-fields"><label>Backup .zip gerado pelo Cantina em Dia<input type="file" name="backup" accept=".zip,application/zip" required /><small>Use esta opção também para recuperar o histórico após instalar o sistema em outro computador.</small></label></div></Composer>
    <Composer title="Restaurar uma cópia em outro banco" submit="Criar banco restaurado" onSubmit={async form => {
      const result = await api<Result>(`/backups/${form.get('id')}/restore`, { method: 'POST', body: '{}', signal: AbortSignal.timeout(180000) });
      setRestored(result.database); setMessage(`${result.rows} registros e ${result.attachments} comprovantes recuperados e conferidos.`); await refresh();
    }}><div className="operation-fields"><label>Cópia a recuperar<select name="id" required><option value="">Selecione…</option>{rows.filter(r => r.file_available).map(r => <option key={r.id} value={r.id}>#{r.id} · {dateTime(r.snapshot_at || r.created_at)}</option>)}</select></label></div><div className="notice">A restauração cria outro banco e recupera os comprovantes ausentes. A cópia será conferida antes de ficar disponível para uso. O aplicativo continua usando o banco atual até você alterar a configuração.</div></Composer></div>
    <DataTable title="Cópias registradas (últimas 500)" rows={rows} columns={[
      { label: 'Backup', render: r => `#${r.id} · ${r.label || r.filename}` }, { label: 'Retrato de', render: r => dateTime(r.snapshot_at || r.created_at) },
      { label: 'Arquivo', render: r => `${(r.size_bytes / 1024 / 1024).toFixed(2)} MB · ${r.file_available ? 'Encontrado' : 'Ausente'}` },
      { label: 'Último teste', render: r => r.verified_at ? dateTime(r.verified_at) : 'Não testado' },
      { label: 'Última cópia restaurada', render: r => r.last_restore_database ? <><code>{r.last_restore_database}</code><small className="restore-date">{dateTime(r.last_restored_at)}</small></> : '—' },
      { label: 'Ações', render: r => r.file_available ? <div className="attachment-actions"><a className="text-button" href={`/api/backups/${r.id}/download`}>Baixar .zip</a><button className="text-button" disabled={busy} onClick={() => void verify(r)}>Testar restauração</button></div> : 'Importe a cópia externa' },
    ]} />
    <div className="notice">O arquivo contém dados privados da cantina e não é criptografado. Ele não inclui credenciais, programas ou outras cópias de backup. Este formato exige a mesma revisão de estrutura do aplicativo; guarde também o código correspondente. O PostgreSQL precisa permitir a criação de bancos para executar o teste e a recuperação.</div>
  </>;
}
