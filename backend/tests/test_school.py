def event(client, **extra):
    data = {'kind': 'holiday', 'title': 'Feriado municipal', 'starts_on': '2026-11-05', 'ends_on': '2026-11-05', 'effect': 'closed', 'source': 'Secretaria do Senai', **extra}
    return client.post('/api/school/events', json=data)


def test_courses_events_and_calendar(client):
    course = {'name': 'Técnico em Eletrotécnica', 'shift': 'evening', 'starts_on': '2026-08-01', 'ends_on': '2026-11-20', 'students': 30, 'source': 'Quadro de turmas'}
    assert client.post('/api/school/courses', json={**course, 'ends_on': '2026-07-01'}).status_code == 422
    created = client.post('/api/school/courses', json=course)
    assert created.status_code == 201 and created.json()['weekdays'] == [0, 1, 2, 3, 4]
    morning = client.post('/api/school/courses', json={**course, 'name': 'Aprendizagem', 'shift': 'morning', 'students': None, 'weekdays': [2, 0]}).json()
    assert morning['weekdays'] == [0, 2]
    assert event(client).status_code == 201 and event(client).status_code == 409
    strike = event(client, kind='strike', title='Paralisação dos docentes', starts_on='2026-11-09', ends_on='2026-11-10', effect='reduced').json()
    days = {d['day']: d for d in client.get('/api/school/calendar', params={'start': '2026-11-02', 'days': 9}).json()['days']}
    assert days['2026-11-02']['status'] == 'open' and days['2026-11-02']['courses_count'] == 2 and days['2026-11-02']['students_estimate'] == 30
    assert days['2026-11-03']['courses_count'] == 1
    assert days['2026-11-05']['status'] == 'closed' and days['2026-11-07']['status'] == 'closed' and days['2026-11-09']['status'] == 'reduced'
    assert client.post(f"/api/school/events/{strike['id']}/cancel", json={'reason': 'Suspensa'}).status_code == 200
    assert client.get('/api/school/calendar', params={'start': '2026-11-09', 'days': 1}).json()['days'][0]['status'] == 'open'
    updated = client.put(f"/api/school/courses/{morning['id']}", json={**course, 'name': 'Aprendizagem', 'shift': 'afternoon'})
    assert updated.status_code == 200 and updated.json()['shift_label'] == 'Tarde'


def test_calendar_check_is_recorded(client):
    assert client.get('/api/school/calendar').json()['last_check'] is None
    assert client.post('/api/school/checks', json={'source': 'Coordenação', 'note': 'Sem mudanças'}).status_code == 201
    check = client.get('/api/school/calendar').json()['last_check']
    assert check['age_days'] == 0 and check['overdue'] is False
