import { spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import { config, migrate, root, python, exists, run } from './common.mjs';

const children = [];
let stopping = false;

async function shutdown(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children.reverse()) {
    if (child.exitCode === null && child.pid) {
      await new Promise(resolve => {
        const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
        killer.on('exit', resolve);
        killer.on('error', resolve);
      });
    }
  }
  process.exit(code);
}
process.on('SIGINT', () => shutdown());
process.on('SIGTERM', () => shutdown());

async function assertFree(port) {
  await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', () => reject(new Error(`A porta ${port} já está em uso. Feche a outra instância ou ajuste .env.`)));
    server.listen(port, '127.0.0.1', () => server.close(resolve));
  });
}

function launch(command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env, windowsHide: true, stdio: 'inherit' });
  children.push(child);
  child.on('error', error => { console.error(error.message); shutdown(1); });
  child.on('exit', code => { if (!stopping) shutdown(code || 0); });
}

async function waitFor(url) {
  for (let attempt = 0; attempt < 50; attempt++) {
    try { if ((await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('O serviço não iniciou a tempo. Confira as mensagens acima.');
}

try {
  if (!(await exists(python))) throw new Error('Execute npm run setup antes de iniciar.');
  const cfg = await config();
  await assertFree(cfg.apiPort);
  await assertFree(cfg.webPort);
  const env = { ...cfg.values, PYTHONUNBUFFERED: '1', PYTHONUTF8: '1' };
  await migrate(env);
  if (!/^(0|false|off|no|n|f)$/i.test(String(cfg.values.CANTINA_AUTO_BACKUP || '1'))) {
    try { await run(python, ['-m', 'app.backup', 'create', '--if-due'], { cwd: path.join(root, 'backend'), env }); }
    catch { console.warn('A cópia de segurança diária não foi concluída. A aplicação continuará disponível.'); }
  }
  launch(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(cfg.apiPort)], path.join(root, 'backend'), env);
  await waitFor(`http://127.0.0.1:${cfg.apiPort}/api/health/database`);
  launch(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(cfg.webPort), '--strictPort'], path.join(root, 'frontend'), { ...env, API_PORT: String(cfg.apiPort) });
  await waitFor(`http://127.0.0.1:${cfg.webPort}`);
  console.log(`\nCantina em Dia: http://127.0.0.1:${cfg.webPort}\nAPI: http://127.0.0.1:${cfg.apiPort}/docs\nCtrl+C encerra os serviços desta sessão.\n`);
} catch (error) {
  // Mensagens de bibliotecas podem conter parâmetros de conexão: mostrar só falhas conhecidas.
  const safe = ['Execute ', 'A porta ', 'O serviço ', 'Comando ', 'Configure '];
  console.error(safe.some(prefix => error.message?.startsWith(prefix)) ? error.message : 'Não foi possível iniciar. Verifique se o serviço MySQL está ligado, as dependências e o arquivo .env.');
  await shutdown(1);
}
