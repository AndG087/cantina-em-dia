import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.main import app
from app.database import get_session
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def isolated_test_database():
    # Bloquear a execução acidental contra o banco operacional.
    assert engine.url.database == "cantina_em_dia_test", "Execute npm test para usar o banco de testes isolado."
    connection = engine.connect()
    transaction = connection.begin()
    connection.execute(text("UPDATE app_settings SET business_name='Cantina em Dia', location='SENAI · Paulista', manager_name='' WHERE id=1"))
    def override():
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            yield session
    app.dependency_overrides[get_session] = override
    yield connection
    app.dependency_overrides.clear()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value
