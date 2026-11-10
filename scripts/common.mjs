import { spawn } from 'node:child_process';
import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'dotenv';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const python = path.join(root, '.venv', 'Scripts', 'python.exe');
export const exists = async p => access(p, constants.F_OK).then(() => true, () => false);

export function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: root, windowsHide: true, stdio: 'inherit', ...options });
    child.on('error', reject);
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Comando falhou (${code}): ${path.basename(command)}`)));
  });
}

/** Lê o .env. O MySQL roda como serviço do Windows; o banco é preparado por npm run setup. */
export async function config() {
  const envPath = path.join(root, '.env');
  const values = { ...((await exists(envPath)) ? parse(await readFile(envPath)) : {}), ...process.env };
  if (!values.DATABASE_URL?.startsWith('mysql+pymysql://')) throw new Error('Configure o MySQL: execute npm.cmd run setup.');
  return { values, apiPort: Number(values.API_PORT || 8000), webPort: Number(values.WEB_PORT || 5173) };
}

export async function migrate(env) {
  await run(python, ['-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'], { env });
}
