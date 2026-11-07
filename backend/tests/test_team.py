def person(client, name="Dona Gel"):
    response = client.post('/api/employees', json={'name': name, 'role': 'Atendimento'})
    assert response.status_code == 201
    return response.json()['id']


def test_shift_overlap_override_and_closure(client):
    first = person(client)
    second = person(client, 'Outro funcionário')
    shift = {'employee_id': first, 'weekday': 0, 'start_time': '08:00', 'end_time': '12:00', 'valid_from': '2026-01-01'}
    assert client.post('/api/shifts', json=shift).status_code == 201
    assert client.post('/api/shifts', json={**shift, 'employee_id': second, 'start_time': '09:00'}).status_code == 409
    at = {'at': '2026-11-02T10:00:00-03:00'}
    assert client.get('/api/cash-responsibility', params=at).json()['expected']['id'] == first
    assert client.post('/api/shift-overrides', json={'employee_id': second, 'day': '2026-11-02', 'start_time': '09:00', 'end_time': '11:00', 'reason': 'Substituição combinada'}).status_code == 201
    assert client.get('/api/cash-responsibility', params=at).json()['expected']['id'] == second
    assert client.post('/api/closures', json={'day': '2026-11-02', 'reason': 'Feriado'}).status_code == 201
    assert client.get('/api/cash-responsibility', params=at).json()['closed'] is True


def test_manual_confirmations_preserve_history(client):
    first, second = person(client), person(client, 'Segundo responsável')
    for key, hour in [(first, '09:00'), (second, '10:00')]:
        assert client.post('/api/assignments', json={'employee_id': key, 'started_at': f'2026-11-02T{hour}:00-03:00', 'reason': 'Confirmação recebida'}).status_code == 201
    result = client.get('/api/cash-responsibility', params={'at': '2026-11-02T10:30:00-03:00'}).json()
    assert result['confirmed']['id'] == second
    history = client.get('/api/assignments').json()
    assert len(history) == 2 and history[1]['ended_at'] is not None
    weekend = client.get('/api/cash-responsibility', params={'at': '2026-11-07T10:00:00-03:00'}).json()
    assert weekend['closed'] is True and weekend['confirmed'] is None


def test_inactive_employee_cannot_take_cash_responsibility(client):
    key = person(client)
    assert client.put(f'/api/employees/{key}', json={'name': 'Dona Gel', 'role': 'Cozinha', 'active': False}).status_code == 200
    assert client.post('/api/assignments', json={'employee_id': key, 'started_at': '2026-11-02T10:00:00-03:00', 'reason': 'Teste de confirmação'}).status_code == 409
