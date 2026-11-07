import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.main import app


@pytest.fixture(autouse=True)
def isolated_test_database():
    # Bloquear a execução acidental contra o banco operacional.
    assert engine.url.database == "cantina_em_dia_test", "Execute npm test para usar o banco de testes isolado."
    with engine.begin() as connection:
        connection.execute(text("UPDATE app_settings SET business_name='Cantina em Dia', location='SENAI · Paulista', manager_name='' WHERE id=1"))
    yield
    with engine.begin() as connection:
        connection.execute(text("UPDATE app_settings SET business_name='Cantina em Dia', location='SENAI · Paulista', manager_name='' WHERE id=1"))


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value
