import pytest
from django.contrib.auth import get_user_model
# from startups.models import StartupProfile 

User = get_user_model()

@pytest.mark.django_db
def test_user_creation():
    """Перевірка створення базового користувача"""
    user = User.objects.create_user(
        email="test@example.com", 
        password="password123",
        role_id=1  
    )
    assert user.email == "test@example.com"
    assert user.is_active is True

@pytest.mark.django_db
def test_startup_profile_placeholder():
    """Заготовка для тесту StartupProfile"""
    assert True