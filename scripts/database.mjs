import { config, ensurePostgres } from './common.mjs';
const cfg = await config();
const stop = await ensurePostgres(cfg);
console.log('PostgreSQL local disponível. Ctrl+C encerra esta sessão.');
const timer = setInterval(() => {}, 1000);
async function close() { clearInterval(timer); await stop(); process.exit(0); }
process.on('SIGINT', close);
process.on('SIGTERM', close);
