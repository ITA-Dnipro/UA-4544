import pytest
from django.urls import reverse

@pytest.mark.api
def test_health_check(client):
    """
    Перевірка доступності /api/health/
    Тест валідує статус-код 200 та коректність відповіді.
    """
    url = "/api/health/" 
    
    response = client.get(url)
    
    # Перевіряємо, що статус-код саме 200 (OK)
    assert response.status_code == 200
    
    # Перевіряємо тіло відповіді
    expected_data = {"status": "ok"}
    assert response.json() == expected_data
    
    # Перевіряємо Content-Type
    assert response.headers["Content-Type"] == "application/json"
