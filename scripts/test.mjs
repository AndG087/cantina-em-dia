import pg from 'pg';
import { config, ensurePostgres, migrate, run, python } from './common.mjs';

const cfg = await config();
const stopDatabase = await ensurePostgres(cfg);
try {
  const url = new URL(cfg.url);
  const adminUrl = new URL(cfg.url);
  adminUrl.pathname = '/postgres';
  const client = new pg.Client({ connectionString: adminUrl.toString() });
  await client.connect();
  try {
    const found = await client.query('SELECT 1 FROM pg_database WHERE datname = $1', ['cantina_em_dia_test']);
    if (!found.rowCount) await client.query('CREATE DATABASE cantina_em_dia_test');
  } finally { await client.end(); }
  url.pathname = '/cantina_em_dia_test';
  const env = { ...cfg.values, DATABASE_URL: url.toString().replace('postgresql:', 'postgresql+psycopg:'), PYTHONUTF8: '1' };
  await migrate(env);
  await run(python, ['-m', 'pytest', 'backend/tests', '-q'], { env });
} finally { await stopDatabase(); }
