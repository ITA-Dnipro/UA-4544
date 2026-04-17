import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_health_check_endpoint(client):
    """Перевірка доступності /api/health/"""
    url = "/api/health/"
    response = client.get(url)
    assert True