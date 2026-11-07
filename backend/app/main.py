import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, settings
from .database import engine, get_session
from .models import AppSettings
from .schemas import SettingsRead, SettingsUpdate
from .team import router as team_router
from .inventory import router as inventory_router
from .purchases import router as purchases_router
from .finance import router as finance_router
from alembic.config import Config
from alembic.script import ScriptDirectory

app = FastAPI(title="Cantina em Dia", version="0.1.0")
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{settings.web_port}", f"http://localhost:{settings.web_port}"],
    allow_methods=["GET", "PUT", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

SessionDep = Annotated[Session, Depends(get_session)]
app.include_router(team_router)
app.include_router(inventory_router)
app.include_router(purchases_router)
app.include_router(finance_router)
DOCUMENTS = {
    "projeto": ("Projeto de gestão", "PROJETO_GESTAO_CANTINA.md", "Operação, responsabilidades e plano de implantação."),
    "sistema": ("Especificação do sistema", "ESPECIFICACAO_SISTEMA_PYTHON.md", "Requisitos do aplicativo e regras dos controles."),
    "perguntas": ("Perguntas para seu pai", "PERGUNTAS_PARA_O_PAI.md", "Informações que ainda precisamos levantar."),
    "desenvolvimento": ("Prompt de desenvolvimento", "PROMPT_DESENVOLVIMENTO.md", "Orientações para continuar no VS Code por etapas."),
}


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request, exc):
    # Não expor a URL de conexão nem parâmetros potencialmente privados.
    logging.getLogger("cantina").error("Operação de banco falhou: %s", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Banco indisponível ou desatualizado. Confira o PostgreSQL e execute as migrações."},
    )


@app.get("/api/health")
def health():
    """Verifica o processo da API, sem afirmar que o banco está disponível."""
    return {"status": "ok", "service": "Cantina em Dia", "version": "0.1.0"}


@app.get("/api/health/database")
def database_health():
    # Verificar conexão, versão da migração e configuração inicial separadamente.
    with engine.connect() as connection:
        database = connection.execute(text("SELECT current_database()")).scalar_one()
        version = connection.execute(text("SHOW server_version")).scalar_one()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        configured = connection.execute(text("SELECT count(*) FROM app_settings WHERE id = 1")).scalar_one()
    expected_revision = ScriptDirectory.from_config(Config(str(ROOT / "backend/alembic.ini"))).get_current_head()
    if revision != expected_revision or configured != 1:
        raise HTTPException(503, "Migração pendente. Execute alembic upgrade head.")
    return {
        "status": "ok", "database": database, "engine": "PostgreSQL",
        "server_version": version, "migration": revision,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def get_app_settings(session: Session) -> AppSettings:
    value = session.get(AppSettings, 1)
    if value is None:
        raise HTTPException(503, "Configuração inicial ausente. Execute as migrações.")
    return value


@app.get("/api/settings", response_model=SettingsRead)
def read_settings(session: SessionDep):
    return get_app_settings(session)


@app.put("/api/settings", response_model=SettingsRead)
def update_settings(data: SettingsUpdate, session: SessionDep):
    current = get_app_settings(session)
    for key, value in data.model_dump().items():
        setattr(current, key, value)
    session.commit()
    session.refresh(current)
    return current


@app.get("/api/documents")
def documents():
    return [
        {"id": key, "title": value[0], "filename": value[1], "description": value[2]}
        for key, value in DOCUMENTS.items()
    ]


def document_path(document_id: str) -> tuple[str, Path]:
    # Lista permitida fixa: não aceitar caminhos enviados pelo navegador.
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise HTTPException(404, "Documento não encontrado.")
    path = ROOT / document[1]
    if not path.is_file():
        raise HTTPException(404, "O arquivo ainda não está nesta pasta do projeto.")
    return document[0], path


@app.get("/api/documents/{document_id}")
def read_document(document_id: str):
    title, path = document_path(document_id)
    return {"title": title, "content": path.read_text(encoding="utf-8")}


@app.get("/api/documents/{document_id}/download")
def download_document(document_id: str):
    _, path = document_path(document_id)
    return FileResponse(path, filename=path.name, media_type="text/markdown; charset=utf-8")
