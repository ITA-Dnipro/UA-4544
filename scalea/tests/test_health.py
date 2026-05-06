import pytest


@pytest.mark.api
def test_health_check(client):
    """
    Перевірка доступності /api/health/
    Тест валідує статус-код 200 та коректність відповіді.
    """
    url = '/api/health/'

    response = client.get(url)

    assert response.status_code == 200

    expected_data = {'status': 'ok'}
    assert response.json() == expected_data

    assert response.headers['Content-Type'] == 'application/json'
