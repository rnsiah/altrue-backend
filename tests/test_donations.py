"""
Test donation processing functionality
"""
import pytest
from decimal import Decimal
from django.db import transaction

from api.models import UserDonation, Donation, Balance, AltruePoints
from Alt.models import NonProfitDonation, AtrocityDonation, NonProfitProjectDonation
from tests.factories import (
    UserFactory, UserProfileFactory, BalanceFactory, NonProfitFactory,
    AtrocityFactory, NonProfitProjectFactory, UserDonationFactory,
    DonorFactory, DonationFactory
)


@pytest.mark.django_db
class TestUserDonation:
    """Test user donation creation and processing"""
    
    def test_create_user_donation_nonprofit(self):
        """Test creating a user donation to nonprofit"""
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile, balance=Decimal('100.00'))
        nonprofit = NonProfitFactory()
        
        donation = UserDonation.objects.create(
            user=profile,
            wallet=balance,
            dollar_amount=Decimal('25.00'),
            nonprofit=nonprofit,
            donation_type='S',
            stripe_id='pi_test123',
            paid_for=True
        )
        
        assert donation.pk is not None
        assert donation.user == profile
        assert donation.nonprofit == nonprofit
        assert donation.dollar_amount == Decimal('25.00')
        assert donation.donation_type == 'S'
    
    def test_create_user_donation_atrocity(self):
        """Test creating a user donation to atrocity"""
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile)
        atrocity = AtrocityFactory()
        
        donation = UserDonation.objects.create(
            user=profile,
            wallet=balance,
            dollar_amount=Decimal('50.00'),
            atrocity=atrocity,
            donation_type='S'
        )
        
        assert donation.atrocity == atrocity
        assert donation.dollar_amount == Decimal('50.00')
    
    def test_create_user_donation_project(self):
        """Test creating a user donation to project"""
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile)
        project = NonProfitProjectFactory()
        
        donation = UserDonation.objects.create(
            user=profile,
            wallet=balance,
            dollar_amount=Decimal('75.00'),
            project=project,
            nonprofit=project.nonprofit,
            donation_type='S'
        )
        
        assert donation.project == project
        assert donation.nonprofit == project.nonprofit


@pytest.mark.django_db  
class TestDonationBalanceUpdate:
    """Test that donations update balances correctly"""
    
    def test_external_donation_updates_balance(self):
        """Test that external donor donations update user balance"""
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile, balance=Decimal('0.00'))
        
        donor = DonorFactory(
            sent_to=profile,
            amount_donated=Decimal('50.00'),
            stripe_charge_id='ch_test123'
        )
        
        # Signal should create Donation and update balance
        donation = Donation.objects.get(donor=donor)
        balance.refresh_from_db()
        
        assert donation.receiver == balance
        assert balance.balance == Decimal('50.00')
    
    def test_wallet_donation_decreases_balance(self):
        """Test that wallet donations decrease user balance"""
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile, balance=Decimal('100.00'))
        nonprofit = NonProfitFactory()
        
        # Create donation that uses wallet balance (no stripe_id = wallet)
        donation = UserDonation.objects.create(
            user=profile,
            wallet=balance,
            dollar_amount=Decimal('30.00'),
            nonprofit=nonprofit,
            donation_type='S'
        )
        
        balance.refresh_from_db()
        assert balance.balance == Decimal('70.00')


@pytest.mark.django_db
class TestNonProfitDonation:
    """Test nonprofit donation tracking"""
    
    def test_nonprofit_donation_creation(self):
        """Test creating nonprofit donation record"""
        user = UserFactory()
        profile = user.profile
        nonprofit = NonProfitFactory()
        
        donation = NonProfitDonation.objects.create(
            nonprofit=nonprofit,
            donation_amount=Decimal('100.00'),
            profile_donated=profile
        )
        
        assert donation.nonprofit == nonprofit
        assert donation.donation_amount == Decimal('100.00')
        assert donation.profile_donated == profile
    
    def test_nonprofit_balance_update_on_donation(self):
        """Test that nonprofit balance updates when donation is made"""
        nonprofit = NonProfitFactory()
        # Signal creates balance automatically
        balance = nonprofit.balance
        initial_balance = balance.balance
        
        user = UserFactory()
        profile = user.profile
        
        NonProfitDonation.objects.create(
            nonprofit=nonprofit,
            donation_amount=Decimal('50.00'),
            profile_donated=profile
        )
        
        balance.refresh_from_db()
        assert balance.balance == initial_balance + Decimal('50.00')


@pytest.mark.django_db
class TestAtrocityDonation:
    """Test atrocity donation tracking"""
    
    def test_atrocity_donation_creation(self):
        """Test creating atrocity donation record"""
        user = UserFactory()
        profile = user.profile
        atrocity = AtrocityFactory()
        
        donation = AtrocityDonation.objects.create(
            atrocity=atrocity,
            donation_amount=Decimal('75.00'),
            profile_donated=profile
        )
        
        assert donation.atrocity == atrocity
        assert donation.donation_amount == Decimal('75.00')
    
    def test_atrocity_balance_update_on_donation(self):
        """Test that atrocity balance updates when donation is made"""
        atrocity = AtrocityFactory()
        balance = atrocity.balance
        initial_balance = balance.balance
        
        user = UserFactory()
        profile = user.profile
        
        AtrocityDonation.objects.create(
            atrocity=atrocity,
            donation_amount=Decimal('25.00'),
            profile_donated=profile
        )
        
        balance.refresh_from_db()
        assert balance.balance == initial_balance + Decimal('25.00')


@pytest.mark.django_db
class TestCompanyMatching:
    """Test company donation matching functionality"""
    
    def test_user_donation_triggers_company_match(self):
        """Test that user donations trigger company matching"""
        from tests.factories import ForProfitCompanyFactory, CompanyNonProfitRelationshipFactory
        from Alt.models import CompanyMatchDonation
        
        # Setup
        user = UserFactory()
        profile = user.profile
        balance = BalanceFactory(account=profile, balance=Decimal('200.00'))
        nonprofit = NonProfitFactory()
        company = ForProfitCompanyFactory()
        
        # Create company-nonprofit relationship
        relationship = CompanyNonProfitRelationshipFactory(
            company=company,
            nonprofit=nonprofit,
            match_level=50,  # 50% match
            funding_limit=1000
        )
        
        # Create user donation with company match
        donation = UserDonation.objects.create(
            user=profile,
            wallet=balance,
            dollar_amount=Decimal('100.00'),
            nonprofit=nonprofit,
            donation_type='S',
            is_matched=True
        )
        
        # Check if company match donation was created
        matches = CompanyMatchDonation.objects.filter(
            transaction_matched=donation,
            company=company,
            nonprofit=nonprofit
        )
        
        # Should have created a match (50% of $100 = $50)
        assert matches.exists()
        match = matches.first()
        assert match.amount == Decimal('50.00')
