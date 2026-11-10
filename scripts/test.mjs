import { config, migrate, run, python } from './common.mjs';

// Os testes usam um banco separado, cantina_em_dia_test, criado por npm run setup.
const cfg = await config();
const url = new URL(cfg.values.DATABASE_URL.replace('mysql+pymysql:', 'mysql:'));
url.pathname = '/cantina_em_dia_test';
const env = { ...cfg.values, DATABASE_URL: url.toString().replace('mysql:', 'mysql+pymysql:'), PYTHONUTF8: '1' };
await migrate(env);
await run(python, ['-m', 'pytest', 'backend/tests', '-q'], { env });
