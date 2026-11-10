import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def connection():
    # Cada teste roda em uma transação desfeita ao final, no banco de testes separado.
    assert engine.url.database == 'cantina_em_dia_test', 'Execute npm test para usar o banco de testes isolado.'
    connection = engine.connect()
    transaction = connection.begin()

    def override():
        with Session(bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False) as session:
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


def at(day, hm='10:00'):
    return f'{day}T{hm}:00-03:00'
