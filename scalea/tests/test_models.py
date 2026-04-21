import pytest
from django.contrib.auth import get_user_model
from startups.models import StartupProfile, Project
from investors.models import InvestorProfile, Investment

User = get_user_model()

ROLE_ADMIN = 1
ROLE_STARTUP = 2
ROLE_INVESTOR = 3

@pytest.mark.django_db
@pytest.mark.models  
class TestModels:
    
    def test_user_creation(self):
        user = User.objects.create_user(
            email="test@scalea.com",
            username="testuser",
            password="password123",
            role_id=ROLE_ADMIN
        )
        assert user.email == "test@scalea.com"
        assert user.role_id == ROLE_ADMIN

    def test_startup_profile_creation(self):
        owner = User.objects.create_user(
            email="founder@scalea.com",
            username="founder",
            password="password123",
            role_id=ROLE_STARTUP
        )
        startup = StartupProfile.objects.create(
            user=owner,
            company_name="Scalea Innovation",
            description="Testing coverage"
        )
        assert startup.company_name == "Scalea Innovation"
        assert startup.user == owner

    def test_project_creation(self):
        owner = User.objects.create_user(email="p@s.com", username="p", role_id=ROLE_STARTUP)
        startup = StartupProfile.objects.create(user=owner, company_name="Project Base")
        
        project = Project.objects.create(
            startup=startup,
            title="AI Engine",
            status=True,
            short_description="Short desc",
            description="Full desc",
            current_funding=0
        )
        assert project.title == "AI Engine"

    def test_investment_flow(self):
        inv_user = User.objects.create_user(email="i@s.com", username="inv", role_id=ROLE_INVESTOR)
        investor = InvestorProfile.objects.create(user=inv_user, company_name="VC Fund")
        
        owner = User.objects.create_user(email="f@s.com", username="f", role_id=ROLE_STARTUP)
        startup = StartupProfile.objects.create(user=owner, company_name="Target")
        project = Project.objects.create(
            startup=startup, title="App", status=True, 
            short_description="S", description="L", current_funding=0
        )
        
        investment = Investment.objects.create(
            investor_profile=investor,
            project=project,
            amount=1000.00
        )
        assert investment.amount == 1000.00