import { spawn } from 'node:child_process';
import { access, mkdir, readFile, writeFile, unlink } from 'node:fs/promises';
import { constants } from 'node:fs';
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { parse } from 'dotenv';
import pg from 'pg';
import { initdb, pg_ctl } from '@embedded-postgres/windows-x64';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const python = path.join(root, '.venv', 'Scripts', 'python.exe');
export const runtime = path.join(process.env.LOCALAPPDATA || os.homedir(), 'CantinaEmDia');
export const dataDir = path.join(runtime, 'postgres');
export const exists = async p => access(p, constants.F_OK).then(() => true, () => false);

export function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: root, windowsHide: true, stdio: 'inherit', ...options });
    child.on('error', reject);
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`Comando falhou (${code}): ${path.basename(command)}`)));
  });
}

export async function config() {
  await mkdir(runtime, { recursive: true });
  const envPath = path.join(root, '.env');
  if (!(await exists(envPath))) {
    const password = randomBytes(30).toString('hex');
    await writeFile(envPath, [
      `DATABASE_URL=postgresql+psycopg://cantina:${password}@127.0.0.1:55432/cantina_em_dia`,
      'CANTINA_MANAGED_POSTGRES=1', 'API_PORT=8000', 'WEB_PORT=5173', '',
    ].join('\n'), { flag: 'wx' });
    console.log('Configuração local criada em .env (credenciais não serão exibidas).');
  }
  const values = { ...parse(await readFile(envPath)), ...process.env };
  const url = new URL(values.DATABASE_URL?.replace('postgresql+psycopg:', 'postgresql:'));
  if (url.protocol !== 'postgresql:') throw new Error('Configure uma DATABASE_URL PostgreSQL válida.');
  const managed = values.CANTINA_MANAGED_POSTGRES === '1';
  if (managed && (!['127.0.0.1', 'localhost'].includes(url.hostname) || url.username !== 'cantina' || !/^\/cantina_(em_dia|restore_[a-f0-9]{12})$/.test(url.pathname))) {
    throw new Error('O PostgreSQL gerenciado usa o banco cantina_em_dia ou uma cópia restaurada e o usuário cantina em loopback. Para outro banco, configure CANTINA_MANAGED_POSTGRES=0.');
  }
  return { values, url, managed, apiPort: Number(values.API_PORT || 8000), webPort: Number(values.WEB_PORT || 5173) };
}

export async function ensurePostgres(cfg) {
  let owned = false;
  if (cfg.managed) {
    if (!(await exists(path.join(dataDir, 'PG_VERSION')))) {
      const passwordFile = path.join(runtime, `init-${randomBytes(6).toString('hex')}.tmp`);
      await writeFile(passwordFile, decodeURIComponent(cfg.url.password), { mode: 0o600 });
      try {
        await run(initdb, ['-D', dataDir, '-U', 'cantina', '--pwfile', passwordFile, '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C']);
      } finally { await unlink(passwordFile).catch(() => {}); }
    }
    const status = await new Promise(resolve => {
      const p = spawn(pg_ctl, ['status', '-D', dataDir], { windowsHide: true, stdio: 'ignore' });
      p.on('error', () => resolve(false));
      p.on('exit', code => resolve(code === 0));
    });
    if (!status) {
      await run(pg_ctl, ['start', '-D', dataDir, '-l', path.join(runtime, 'postgres.log'), '-o', `-p ${cfg.url.port || '55432'} -h 127.0.0.1`, '-w', '-t', '30']);
      owned = true;
    }
    try {
      const adminUrl = new URL(cfg.url);
      adminUrl.pathname = '/postgres';
      const client = new pg.Client({ connectionString: adminUrl.toString(), connectionTimeoutMillis: 4000 });
      await client.connect();
      try {
        const database = cfg.url.pathname.slice(1);
        const found = await client.query('SELECT 1 FROM pg_database WHERE datname = $1', [database]);
        if (!found.rowCount) {
          if (database !== 'cantina_em_dia') throw new Error('O PostgreSQL não encontrou a cópia restaurada. Confira o nome no .env.');
          await client.query('CREATE DATABASE cantina_em_dia');
        }
      } finally { await client.end(); }
    } catch (error) {
      if (owned) await run(pg_ctl, ['stop', '-D', dataDir, '-m', 'fast', '-w']).catch(() => {});
      throw error;
    }
  }
  return async () => {
    if (owned) {
      owned = false;
      await run(pg_ctl, ['stop', '-D', dataDir, '-m', 'fast', '-w', '-t', '30']);
    }
  };
}

export async function migrate(env) {
  await run(python, ['-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'], { env });
}
