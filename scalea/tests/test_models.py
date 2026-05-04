import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from investors.models import Investment, InvestorProfile
from projects.models import Project, ProjectStatus
from startups.models import StartupProfile

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.models
class TestModels:
    def test_user_creation(self):
        user = User.objects.create_user(
            email="test@scalea.com",
            username="testuser",
            password="password123",
            is_verified=True
        )
        assert user.email == "test@scalea.com"
        assert user.is_verified is True

    def test_startup_profile_creation(self):
        owner = User.objects.create_user(
            email="founder@scalea.com",
            username="founder",
            password="password123",
            is_startup=True
        )
        startup = StartupProfile.objects.create(
            user=owner,
            company_name="Scalea Innovation",
            description="Testing coverage"
        )
        assert startup.company_name == "Scalea Innovation"
        assert owner.is_startup is True

    def test_project_creation(self):
        owner = User.objects.create_user(
            email="p@s.com", 
            username="p", 
            is_startup=True
        )
        startup = StartupProfile.objects.create(
            user=owner, 
            company_name="Project Base"
        )

        project = Project.objects.create(
            startup=startup,
            title="AI Engine",
            status=ProjectStatus.IDEA,
            short_description="Short desc",
            description="Full desc",
            target_amount=Decimal('5000.00'),
            raised_amount=Decimal('0.00')
        )
        assert project.title == "AI Engine"
        assert project.slug is not None  

    def test_investment_flow(self):
        inv_user = User.objects.create_user(
            email="i@s.com", 
            username="inv", 
            is_investor=True
        )
        investor = InvestorProfile.objects.create(
            user=inv_user, 
            company_name="VC Fund"
        )

    
        owner = User.objects.create_user(
            email="f@s.com", 
            username="f", 
            is_startup=True
        )
        startup = StartupProfile.objects.create(
            user=owner, 
            company_name="Target"
        )
        
        project = Project.objects.create(
            startup=startup, 
            title="App", 
            status=ProjectStatus.FUNDRAISING,
            short_description="S", 
            description="L", 
            target_amount=Decimal('10000.00'),
            raised_amount=Decimal('0.00')
        )

     
        investment = Investment.objects.create(
            investor_profile=investor,
            project=project,
            amount=Decimal('1000.00')
        )
        
        assert investment.amount == Decimal('1000.00')
        assert inv_user.is_investor is True
        assert project.audits.exists()  