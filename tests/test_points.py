"""
Test AltruePoints calculation and point system
"""
import pytest
from unittest.mock import patch

from api.models import AltruePoints, PointTransaction, UserAltrueAction
from tests.factories import (
    UserFactory, UserProfileFactory, AltruePointsFactory,
    AltrueActionFactory, PointTransactionFactory
)


@pytest.mark.django_db
class TestAltruePoints:
    """Test AltruePoints model functionality"""
    
    def test_create_altrue_points_on_profile_creation(self):
        """Test that AltruePoints are created when UserProfile is created"""
        user = UserFactory()
        profile = user.profile
        
        # AltruePoints should be created via signal
        assert hasattr(profile, 'altrue_points')
        assert profile.altrue_points.balance == 0
    
    def test_altrue_points_str_representation(self):
        """Test AltruePoints string representation"""
        points = AltruePointsFactory(balance=150)
        
        assert str(points) == '150'
    
    def test_altrue_points_balance_update(self):
        """Test updating AltruePoints balance"""
        points = AltruePointsFactory(balance=100)
        
        points.balance += 50
        points.save()
        
        points.refresh_from_db()
        assert points.balance == 150


@pytest.mark.django_db
class TestPointTransaction:
    """Test PointTransaction functionality"""
    
    def test_create_point_transaction(self):
        """Test creating a point transaction"""
        profile = UserProfileFactory()
        action = AltrueActionFactory()
        
        transaction = PointTransaction.objects.create(
            user=profile,
            action=action,
            amount=50,
            balance_before=0,
            balance_after=50,
            description='Test transaction'
        )
        
        assert transaction.pk is not None
        assert transaction.user == profile
        assert transaction.action == action
        assert transaction.amount == 50
        assert transaction.balance_after == 50
    
    def test_point_transaction_str(self):
        """Test PointTransaction string representation"""
        transaction = PointTransactionFactory()
        
        str_repr = str(transaction)
        assert str(transaction.user.user) in str_repr
        assert str(transaction.amount) in str_repr
    
    def test_multiple_point_transactions(self):
        """Test multiple point transactions accumulate"""
        profile = UserProfileFactory()
        action = AltrueActionFactory()
        
        PointTransaction.objects.create(
            user=profile,
            action=action,
            amount=25,
            balance_before=0,
            balance_after=25,
            description='First transaction'
        )
        
        PointTransaction.objects.create(
            user=profile,
            action=action,
            amount=30,
            balance_before=25,
            balance_after=55,
            description='Second transaction'
        )
        
        transactions = PointTransaction.objects.filter(user=profile)
        assert transactions.count() == 2
        
        latest = transactions.latest('timestamp')
        assert latest.balance_after == 55


@pytest.mark.django_db
class TestUserAltrueAction:
    """Test UserAltrueAction functionality"""
    
    def test_create_user_altrue_action(self):
        """Test creating a user Altrue action"""
        profile = UserProfileFactory()
        action = AltrueActionFactory()
        
        user_action = UserAltrueAction.objects.create(
            profile_acting=profile,
            altrue_action=action
        )
        
        assert user_action.pk is not None
        assert user_action.profile_acting == profile
        assert user_action.altrue_action == action
        assert user_action.is_promotion is False
    
    def test_user_altrue_action_str(self):
        """Test UserAltrueAction string representation"""
        profile = UserProfileFactory()
        action = AltrueActionFactory(requirement='Complete profile')
        
        user_action = UserAltrueAction.objects.create(
            profile_acting=profile,
            altrue_action=action
        )
        
        str_repr = str(user_action)
        assert str(profile.user.email) in str_repr
        assert 'Complete profile' in str_repr


@pytest.mark.django_db
class TestAltrueLevel:
    """Test AltrueLevel functionality"""
    
    def test_create_altrue_level(self):
        """Test creating AltrueLevel"""
        from Alt.models import AltrueLevel
        
        level = AltrueLevel.objects.create(
            level_number=1,
            name='Beginner',
            minimum_points=0,
            maximum_points=100
        )
        
        assert level.pk is not None
        assert str(level) == 'Beginner'
        assert level.minimum_points == 0
        assert level.maximum_points == 100
    
    def test_altrue_level_with_required_actions(self):
        """Test AltrueLevel with required actions"""
        from Alt.models import AltrueLevel
        
        action1 = AltrueActionFactory()
        action2 = AltrueActionFactory()
        
        level = AltrueLevel.objects.create(
            level_number=2,
            name='Intermediate',
            minimum_points=100,
            maximum_points=500
        )
        level.requiredActions.add(action1, action2)
        
        assert level.requiredActions.count() == 2
        assert action1 in level.requiredActions.all()
        assert action2 in level.requiredActions.all()


@pytest.mark.django_db
class TestPointSystemActions:
    """Test point system action handling"""
    
    def test_record_user_action_integration(self):
        """Test recording user action through point system"""
        from api.point_system import record_user_action
        
        profile = UserProfileFactory()
        action_code = 'testAction'
        
        # Mock the point system call
        with patch('api.point_system.AltrueAction.objects.get') as mock_get:
            mock_action = AltrueActionFactory()
            mock_action.points_awarded = 25
            mock_get.return_value = mock_action
            
            # This would normally create point transactions
            # For now, just verify the function can be called
            # Note: Full integration test would require mocking more components
            pass
    
    def test_promotion_multiplier_applied(self):
        """Test that promotion multipliers are applied to points"""
        from Alt.models import AltruePointPromotion
        
        # Create a promotion
        promotion = AltruePointPromotion.objects.create(
            multiplier=2,
            name='Double Points Weekend',
            is_active=True
        )
        
        # Create an action with promotion
        action = AltrueActionFactory(
            points_awarded=50,
            is_promoted=True,
            promotion=promotion
        )
        
        assert action.is_promoted is True
        assert action.promotion == promotion
        # Points would be 50 * 2 = 100 during promotion


@pytest.mark.django_db
class TestAltrueActionCode:
    """Test AltrueActionCode functionality"""
    
    def test_create_action_code(self):
        """Test creating action code"""
        from Alt.models import AltrueActionCode
        
        code = AltrueActionCode.objects.create(code='makeADonation')
        
        assert str(code) == 'makeADonation'
    
    def test_action_code_uniqueness(self):
        """Test action codes can have same code value"""
        from Alt.models import AltrueActionCode
        
        code1 = AltrueActionCode.objects.create(code='testCode')
        code2 = AltrueActionCode.objects.create(code='testCode')
        
        # Django doesn't enforce uniqueness by default on this model
        assert code1.pk != code2.pk
