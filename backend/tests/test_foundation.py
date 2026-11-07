from sqlalchemy import create_engine, text

from app.database import engine
from app import main


def test_health_checks_real_postgres_and_migration(client):
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.get("/api/health/database")
    assert response.status_code == 200
    assert response.json()["database"] == "cantina_em_dia_test"
    assert response.json()["migration"] == "0001_foundation"


def test_settings_saved_to_postgres_and_read_again(client):
    response = client.put("/api/settings", json={
        "business_name": "Cantina de teste", "location": "Paulista", "manager_name": "Gerente",
    })
    assert response.status_code == 200
    assert client.get("/api/settings").json()["business_name"] == "Cantina de teste"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT manager_name FROM app_settings WHERE id=1")).scalar_one() == "Gerente"


def test_invalid_settings_do_not_overwrite_saved_data(client):
    response = client.put("/api/settings", json={"business_name": "  ", "location": "Paulista"})
    assert response.status_code == 422
    assert client.get("/api/settings").json()["business_name"] == "Cantina em Dia"


def test_database_failure_is_not_reported_as_healthy(client, monkeypatch):
    unavailable = create_engine("postgresql+psycopg://test:private@127.0.0.1:1/unavailable", connect_args={"connect_timeout": 1})
    monkeypatch.setattr(main, "engine", unavailable)
    try:
        assert client.get("/api/health").status_code == 200
        response = client.get("/api/health/database")
        assert response.status_code == 503
        assert "private" not in response.text
        assert "indisponível" in response.json()["detail"]
    finally:
        unavailable.dispose()


def test_documents_are_allowlisted_and_readable(client):
    docs = client.get("/api/documents").json()
    assert len(docs) == 4
    for document in docs:
        response = client.get(f"/api/documents/{document['id']}")
        assert response.status_code == 200
        assert response.json()["content"].startswith("#")
        assert client.get(f"/api/documents/{document['id']}/download").status_code == 200
    assert client.get("/api/documents/.env").status_code == 404
