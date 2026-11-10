import logging
from datetime import datetime, timezone

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import cash, expenses, purchases, school, stock, weekly
from .config import APP_VERSION, ROOT, settings
from .database import engine

app = FastAPI(title='Cantina em Dia', version=APP_VERSION)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
app.add_middleware(CORSMiddleware, allow_origins=[f'http://127.0.0.1:{settings.web_port}', f'http://localhost:{settings.web_port}'],
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])
for module in (school, purchases, stock, cash, expenses, weekly):
    app.include_router(module.router)


@app.middleware('http')
async def local_origin_only(request, call_next):
    # Somente a própria interface local pode alterar os dados.
    origin = request.headers.get('origin')
    allowed = {f'http://{host}:{port}' for host in ['localhost', '127.0.0.1'] for port in [settings.web_port, settings.api_port]}
    if request.method != 'GET' and origin and origin not in allowed:
        return JSONResponse(status_code=403, content={'detail': 'Origem não autorizada.'})
    return await call_next(request)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    # Não expor a URL de conexão nem parâmetros.
    logging.getLogger('cantina').error('Operação de banco falhou: %s', type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'Banco indisponível ou desatualizado. Confira o PostgreSQL e as migrações.'})


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': APP_VERSION}


@app.get('/api/health/database')
def database_health():
    with engine.connect() as connection:
        database = connection.execute(text('SELECT current_database()')).scalar_one()
        revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    if revision != ScriptDirectory.from_config(Config(str(ROOT / 'backend/alembic.ini'))).get_current_head():
        raise HTTPException(503, 'Migração pendente. Execute npm start para atualizar o banco.')
    return {'status': 'ok', 'database': database, 'migration': revision, 'checked_at': datetime.now(timezone.utc)}
