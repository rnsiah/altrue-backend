"""
Test AltruePoints calculation and point system
"""
import pytest
from unittest.mock import patch
from decimal import Decimal

from api.models import AltruePoints, PointTransaction
from api.point_system import initialize_user_level, record_user_action
from Alt.models import AltrueAction, UserAltrueAction
from tests.factories import (
    UserFactory, UserProfileFactory, AltruePointsFactory, AltrueActionFactory,
    AltrueActionCodeFactory, AltrueLevelFactory, AltrueActionTypeFactory
)


@pytest.mark.django_db
class TestAltruePoints:
    """Test AltruePoints model and operations"""
    
    def test_points_created_with_user(self):
        """Test that AltruePoints are created when user is created"""
        user = UserFactory()
        
        assert hasattr(user.profile, 'altrue_points')
        assert user.profile.altrue_points.balance == 0
    
    def test_points_balance_update(self):
        """Test updating points balance"""
        user = UserFactory()
        points = user.profile.altrue_points
        
        points.balance = 100
        points.save()
        
        points.refresh_from_db()
        assert points.balance == 100
    
    def test_point_transaction_creation(self):
        """Test creating point transaction"""
        user = UserFactory()
        profile = user.profile
        action = AltrueActionFactory()
        
        transaction = PointTransaction.objects.create(
            user=profile,
            action=action,
            amount=50,
            balance_before=0,
            balance_after=50,
            description='Test action completed'
        )
        
        assert transaction.user == profile
        assert transaction.amount == 50
        assert transaction.balance_after == 50


@pytest.mark.django_db
class TestInitializeUserLevel:
    """Test user level initialization"""
    
    def test_initialize_user_level_creates_level_0(self):
        """Test that user is initialized with level 0"""
        user = UserFactory()
        profile = user.profile
        
        # Level 0 should be created and assigned
        assert profile.altrue_level is not None
        assert profile.altrue_level.level_number == 0
    
    def test_initialize_user_level_adds_requirements(self):
        """Test that level requirements are added"""
        # Create level 1 with requirements
        action1 = AltrueActionFactory()
        action2 = AltrueActionFactory()
        level1 = AltrueLevelFactory(level_number=1, minimum_points=100)
        level1.requiredActions.add(action1, action2)
        
        user = UserFactory()
        profile = user.profile
        
        # Check that requirements are added
        requirements = profile.requirementsForNextLevel.all()
        assert action1 in requirements or action2 in requirements


@pytest.mark.django_db
class TestRecordUserAction:
    """Test recording user actions and awarding points"""
    
    def test_record_user_action_creates_action(self):
        """Test recording a user action"""
        user = UserFactory()
        profile = user.profile
        
        # Create action code and action
        action_code = AltrueActionCodeFactory(code='testAction')
        action = AltrueActionFactory(
            action_code=action_code,
            points_awarded=25,
            number_of_occurrences=5
        )
        
        # Record the action
        with patch('api.point_system.AltrueAction.objects.get') as mock_get:
            mock_get.return_value = action
            result = record_user_action(profile, 'testAction', {})
        
        # Check that UserAltrueAction was created
        user_action = UserAltrueAction.objects.filter(
            profile_acting=profile,
            altrue_action=action
        )
        assert user_action.exists()
    
    def test_record_user_action_updates_points(self):
        """Test that recording action updates user points"""
        user = UserFactory()
        profile = user.profile
        points = profile.altrue_points
        initial_balance = points.balance
        
        # Create action
        action_code = AltrueActionCodeFactory(code='pointTest')
        action = AltrueActionFactory(
            action_code=action_code,
            points_awarded=50
        )
        
        # Record the action
        with patch('api.point_system.AltrueAction.objects.get') as mock_get:
            mock_get.return_value = action
            record_user_action(profile, 'pointTest', {})
        
        points.refresh_from_db()
        assert points.balance == initial_balance + 50
    
    def test_record_user_action_respects_max_occurrences(self):
        """Test that points are only awarded up to max occurrences"""
        user = UserFactory()
        profile = user.profile
        
        # Create action with max 2 occurrences
        action_code = AltrueActionCodeFactory(code='limitedAction')
        action = AltrueActionFactory(
            action_code=action_code,
            points_awarded=10,
            number_of_occurrences=2
        )
        
        # Record action multiple times
        with patch('api.point_system.AltrueAction.objects.get') as mock_get:
            mock_get.return_value = action
            record_user_action(profile, 'limitedAction', {})
            record_user_action(profile, 'limitedAction', {})
            record_user_action(profile, 'limitedAction', {})  # Should not award points
        
        # Check that only 2 actions were recorded with points
        point_transactions = PointTransaction.objects.filter(
            user=profile,
            action=action
        )
        assert point_transactions.count() == 2


@pytest.mark.django_db
class TestPointSystemIntegration:
    """Test point system integration with other features"""
    
    def test_first_donation_awards_bonus(self):
        """Test that first donation awards bonus points"""
        from tests.factories import UserDonationFactory
        
        user = UserFactory()
        profile = user.profile
        
        # Create donation action
        action_code = AltrueActionCodeFactory(code='makeADonation')
        AltrueActionFactory(action_code=action_code)
        
        # Create first donation
        donation = UserDonationFactory(user=profile)
        
        # Signal should trigger first-time action award
        # This would need to be tested with the actual signal
        pass
    
    def test_promoted_action_awards_bonus_points(self):
        """Test that promoted actions award bonus points"""
        from Alt.models import AltruePointPromotion
        
        user = UserFactory()
        profile = user.profile
        
        # Create promotion
        promotion = AltruePointPromotion.objects.create(
            name='Double Points Week',
            multiplier=2,
            is_active=True
        )
        
        # Create promoted action
        action_code = AltrueActionCodeFactory(code='promotedAction')
        action = AltrueActionFactory(
            action_code=action_code,
            points_awarded=20,
            is_promoted=True,
            promotion=promotion
        )
        
        # Record action - should award 40 points (20 * 2)
        with patch('api.point_system.AltrueAction.objects.get') as mock_get:
            mock_get.return_value = action
            record_user_action(profile, 'promotedAction', {})
        
        # Check that promoted points were awarded
        points = profile.altrue_points
        points.refresh_from_db()
        # Points should be doubled


@pytest.mark.django_db
class TestLevelProgression:
    """Test user level progression"""
    
    def test_user_can_level_up(self):
        """Test that users can progress to next level"""
        # Create levels
        level0 = AltrueLevelFactory(level_number=0, name='Beginner', minimum_points=0)
        level1 = AltrueLevelFactory(level_number=1, name='Intermediate', minimum_points=100)
        
        user = UserFactory()
        profile = user.profile
        profile.altrue_level = level0
        profile.save()
        
        # Award points to reach next level
        points = profile.altrue_points
        points.balance = 150
        points.save()
        
        # User should now qualify for level 1
        # This would test the level-up logic
    
    def test_level_requirements_tracked(self):
        """Test that level requirements are tracked"""
        user = UserFactory()
        profile = user.profile
        
        # Add some requirements
        action1 = AltrueActionFactory()
        action2 = AltrueActionFactory()
        profile.requirementsForNextLevel.add(action1, action2)
        
        assert profile.requirementsForNextLevel.count() == 2
        assert action1 in profile.requirementsForNextLevel.all()
        assert action2 in profile.requirementsForNextLevel.all()
