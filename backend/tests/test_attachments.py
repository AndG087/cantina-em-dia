import base64
import hashlib

import pytest

from app import storage
from test_team import person


@pytest.fixture(autouse=True)
def attachment_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DATA_ROOT', tmp_path)


def payload(content=b'Mensagem recebida da equipe', filename='mensagem.txt', **values):
    return {'filename': filename, 'content_base64': base64.b64encode(content).decode('ascii'), 'entity': 'inbox', 'entity_id': 0, **values}


def test_attachment_roundtrip_duplicate_and_integrity(client):
    content = 'Comprovante recebido. Valor a conferir: R$ 25,00.'.encode('utf-8')
    response = client.post('/api/attachments', json=payload(content, note='Enviado pela Dona Gel'))
    assert response.status_code == 201, response.text
    key = response.json()['id']
    assert response.json()['sha256'] == hashlib.sha256(content).hexdigest()
    assert client.get(f'/api/attachments/{key}/download').content == content
    assert client.post('/api/attachments', json=payload(content)).status_code == 409
    saved = next(storage.directory('attachments').iterdir())
    saved.write_bytes(b'arquivo alterado')
    assert client.get(f'/api/attachments/{key}/download').status_code == 409


def test_attachment_rejects_unrecognized_formats_and_invalid_content(client):
    assert client.post('/api/attachments', json=payload(b'<script>bad</script>', 'documento.html')).status_code == 422
    assert client.post('/api/attachments', json=payload(b'nao e imagem', 'documento.png')).status_code == 422
    assert client.post('/api/attachments', json={**payload(), 'content_base64': '%%%%'}).status_code == 422
    assert not list(storage.directory('attachments').iterdir())


def test_attachment_link_and_reversible_archive_preserve_file(client):
    employee = person(client)
    key = client.post('/api/attachments', json=payload()).json()['id']
    assert client.post(f'/api/attachments/{key}/link', json={'entity': 'employee', 'entity_id': employee, 'reason': 'Treinamento registrado'}).status_code == 200
    assert client.get('/api/attachments', params={'entity': 'employee', 'entity_id': employee}).json()[0]['id'] == key
    assert client.post(f'/api/attachments/{key}/archive', json={'reason': 'Guardar no histórico'}).status_code == 200
    assert client.get('/api/attachments').json() == []
    assert len(client.get('/api/attachments?include_archived=true').json()) == 1
    assert client.post(f'/api/attachments/{key}/unarchive', json={'reason': 'Voltar à lista ativa'}).status_code == 200
    assert client.get(f'/api/attachments/{key}/download').content == b'Mensagem recebida da equipe'


def test_attachment_cannot_reference_missing_record_or_escape_storage(client):
    assert client.post('/api/attachments', json=payload(entity='expense', entity_id=999999999)).status_code == 404
    assert client.post('/api/attachments', json=payload(entity='inbox', entity_id=1)).status_code == 422
    with pytest.raises(Exception): storage.attachment_path('../../.env')
    assert not list(storage.directory('attachments').iterdir())
