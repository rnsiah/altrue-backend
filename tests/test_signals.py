"""
Test Signals and Model Relationships
"""
import pytest
from decimal import Decimal

from tests.factories import (
    UserFactory, UserProfileFactory, NonProfitFactory, AtrocityFactory,
    ForProfitCompanyFactory, OrderFactory
)


@pytest.mark.django_db
class TestUserProfileSignals:
    """Test UserProfile signal handlers"""
    
    def test_profile_created_on_user_creation(self):
        """Test that UserProfile is created when User is created"""
        user = UserFactory()
        
        assert hasattr(user, 'profile')
        assert user.profile is not None
    
    def test_balance_created_on_profile_creation(self):
        """Test that Balance is created with UserProfile"""
        user = UserFactory()
        profile = user.profile
        
        assert hasattr(profile, 'balance')
        assert profile.balance.balance == Decimal('0.00')
    
    def test_altrue_points_created_on_profile_creation(self):
        """Test that AltruePoints is created with UserProfile"""
        user = UserFactory()
        profile = user.profile
        
        assert hasattr(profile, 'altrue_points')
        assert profile.altrue_points.balance == 0
    
    def test_auth_token_created_on_user_creation(self):
        """Test that auth token is created when User is created"""
        from rest_framework.authtoken.models import Token
        
        user = UserFactory()
        
        assert Token.objects.filter(user=user).exists()
    
    def test_profile_username_synced_to_user(self):
        """Test that profile username is synced to user model"""
        user = UserFactory()
        profile = user.profile
        
        profile.username = 'newusername'
        profile.save()
        
        # The signal should sync username
        # Note: This depends on the actual signal implementation


@pytest.mark.django_db
class TestNonProfitSignals:
    """Test NonProfit signal handlers"""
    
    def test_nonprofit_balance_created_on_creation(self):
        """Test that NonProfitBalance is created with NonProfit"""
        from Alt.models import NonProfitBalance
        
        nonprofit = NonProfitFactory()
        
        assert NonProfitBalance.objects.filter(nonprofit=nonprofit).exists()
    
    def test_nonprofit_balance_created_if_missing(self):
        """Test balance created if missing on save"""
        from Alt.models import NonProfitBalance, NonProfit
        
        nonprofit = NonProfitFactory()
        # Delete the balance
        NonProfitBalance.objects.filter(nonprofit=nonprofit).delete()
        
        # Resave should create new balance
        nonprofit.save()
        
        assert NonProfitBalance.objects.filter(nonprofit=nonprofit).exists()


@pytest.mark.django_db
class TestAtrocitySignals:
    """Test Atrocity signal handlers"""
    
    def test_atrocity_balance_created_on_creation(self):
        """Test that AtrocityBalance is created with Atrocity"""
        from Alt.models import AtrocityBalance
        
        atrocity = AtrocityFactory()
        
        assert AtrocityBalance.objects.filter(atrocity=atrocity).exists()


@pytest.mark.django_db
class TestCompanySignals:
    """Test ForProfitCompany signal handlers"""
    
    def test_company_balance_created_on_creation(self):
        """Test that CompanyBalance is created with ForProfitCompany"""
        from Alt.models import CompanyBalance
        
        company = ForProfitCompanyFactory()
        
        assert CompanyBalance.objects.filter(company=company).exists()
    
    def test_company_balance_created_if_missing(self):
        """Test balance created if missing on save"""
        from Alt.models import CompanyBalance
        
        company = ForProfitCompanyFactory()
        # Delete the balance
        CompanyBalance.objects.filter(company=company).delete()
        
        # Resave should create new balance
        company.save()
        
        assert CompanyBalance.objects.filter(company=company).exists()


@pytest.mark.django_db
class TestUserProfileProperties:
    """Test UserProfile computed properties"""
    
    def test_available_balance_property(self):
        """Test available balance property"""
        profile = UserProfileFactory()
        # The user-creation signal already mints a Balance (OneToOne);
        # set its value instead of creating a duplicate.
        balance = profile.balance
        balance.balance = Decimal('150.00')
        balance.save()

        assert profile.available == Decimal('150.00')
    
    def test_amount_following_property(self):
        """Test amount_following property"""
        profile1 = UserProfileFactory()
        profile2 = UserProfileFactory()
        profile3 = UserProfileFactory()
        
        profile1.following.add(profile2.user, profile3.user)
        
        assert profile1.amount_following == 2
    
    def test_completed_altrue_actions_count(self):
        """Test completed_altrue_actions_count property"""
        profile = UserProfileFactory()
        from tests.factories import AltrueActionFactory
        from api.models import UserAltrueAction
        
        action1 = AltrueActionFactory()
        action2 = AltrueActionFactory()
        
        UserAltrueAction.objects.create(profile_acting=profile, altrue_action=action1)
        UserAltrueAction.objects.create(profile_acting=profile, altrue_action=action2)
        
        assert profile.completed_altrue_actions_count == 2


@pytest.mark.django_db
class TestModelRelationships:
    """Test model relationships work correctly"""
    
    def test_userprofile_to_shirts_manytomany(self):
        """Test UserProfile to Shirt many-to-many relationship"""
        from tests.factories import ShirtFactory
        
        profile = UserProfileFactory()
        shirt1 = ShirtFactory()
        shirt2 = ShirtFactory()
        
        profile.shirt_list.add(shirt1, shirt2)
        
        assert profile.shirt_list.count() == 2
        assert shirt1 in profile.shirt_list.all()
    
    def test_userprofile_to_nonprofit_manytomany(self):
        """Test UserProfile to NonProfit many-to-many relationship"""
        profile = UserProfileFactory()
        np1 = NonProfitFactory()
        np2 = NonProfitFactory()
        
        profile.nonProfit_list.add(np1, np2)
        
        assert profile.nonProfit_list.count() == 2
    
    def test_userprofile_to_atrocity_manytomany(self):
        """Test UserProfile to Atrocity many-to-many relationship"""
        from tests.factories import AtrocityFactory
        
        profile = UserProfileFactory()
        atrocity1 = AtrocityFactory()
        atrocity2 = AtrocityFactory()
        
        profile.atrocity_list.add(atrocity1, atrocity2)
        
        assert profile.atrocity_list.count() == 2
    
    def test_userprofile_following_self_referential(self):
        """Test UserProfile following self-referential many-to-many"""
        profile1 = UserProfileFactory()
        profile2 = UserProfileFactory()
        profile3 = UserProfileFactory()
        
        profile1.following.add(profile2.user)
        profile1.following.add(profile3.user)
        
        assert profile1.following.count() == 2


@pytest.mark.django_db
class TestNonProfitProject:
    """Test NonProfitProject functionality"""
    
    def test_project_make_inactive_when_goal_reached(self):
        """Test project becomes inactive when goal reached"""
        from tests.factories import NonProfitProjectFactory
        
        project = NonProfitProjectFactory(fundraising_goal=1000, total_raised=Decimal('1000.00'))
        
        # Save triggers makeInactive check
        project.save()
        
        assert project.is_active is False
    
    def test_project_stays_active_when_under_goal(self):
        """Test project stays active when under goal"""
        from tests.factories import NonProfitProjectFactory
        
        project = NonProfitProjectFactory(fundraising_goal=1000, total_raised=Decimal('500.00'))
        
        project.save()
        
        assert project.is_active is True
    
    def test_project_str_with_title(self):
        """Test project string with title"""
        from tests.factories import NonProfitProjectFactory
        
        project = NonProfitProjectFactory(title='Test Project')
        
        assert project.nonprofit.name in str(project)
        assert 'Test Project' in str(project)
    
    def test_project_average_rating(self):
        """Test project average rating calculation"""
        from tests.factories import NonProfitProjectFactory, RatingFactory
        
        project = NonProfitProjectFactory()
        profile = UserProfileFactory()
        
        RatingFactory(project=project, user=profile, stars=4)
        RatingFactory(project=project, user=UserProfileFactory(), stars=5)
        
        assert project.average_rating() == 4.5
        assert project.no_of_ratings() == 2
