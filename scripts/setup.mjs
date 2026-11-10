import { spawn } from 'node:child_process';
import { access, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
if (process.platform !== 'win32') throw new Error('Este inicializador foi preparado para Windows. Consulte o README para execução manual.');
const npm = path.join(path.dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js');
async function run(command, args) {
  await new Promise((resolve, reject) => {
    const p = spawn(command, args, { cwd: root, stdio: 'inherit', windowsHide: true });
    p.on('error', reject);
    p.on('exit', code => code === 0 ? resolve() : reject(new Error(`Instalação interrompida (${code}).`)));
  });
}
await run(process.execPath, [npm, 'install']);
await run(process.execPath, [npm, '--prefix', 'frontend', 'install']);
const python = path.join(root, '.venv/Scripts/python.exe');
try { await access(python); } catch { await run('python', ['-m', 'venv', '.venv']); }
await run(python, ['-m', 'pip', 'install', '-r', 'backend/requirements.lock.txt']);
// Na primeira vez, cria os bancos e o usuário no MySQL (pede a senha do root).
const env = await readFile(path.join(root, '.env'), 'utf8').catch(() => '');
if (!env.includes('mysql+pymysql://')) await run(python, ['backend/setup_mysql.py']);
console.log('\nInstalação concluída. Execute npm start.');
