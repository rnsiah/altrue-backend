"""
Test Donation processing functionality
"""
import pytest
from decimal import Decimal
from django.db import transaction

from api.models import UserDonation, Donation, Donor, Balance, CompanyMatchDonation
from Alt.models import NonProfitDonation, AtrocityDonation, NonProfitProjectDonation
from tests.factories import (
    UserFactory, UserProfileFactory, BalanceFactory, NonProfitFactory,
    AtrocityFactory, NonProfitProjectFactory, UserDonationFactory, DonorFactory,
    ForProfitCompanyFactory, CompanyNonProfitRelationshipFactory,
    CompanyAtrocityRelationshipFactory, CompanyBalanceFactory
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
            stripe_id='pi_test123'
        )
        
        assert donation.pk is not None
        assert donation.user == profile
        assert donation.nonprofit == nonprofit
        assert donation.dollar_amount == Decimal('25.00')
    
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
        
        assert donation.pk is not None
        assert donation.atrocity == atrocity
    
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
        
        assert donation.pk is not None
        assert donation.project == project
    
    def test_donation_str_representation(self):
        """Test donation string representation"""
        donation = UserDonationFactory()
        
        assert str(donation) == donation.user.user.email


@pytest.mark.django_db
class TestExternalDonation:
    """Test external donor functionality"""
    
    def test_create_donor(self):
        """Test creating an external donor"""
        profile = UserProfileFactory()
        
        donor = Donor.objects.create(
            email='donor@example.com',
            first_name='John',
            last_name='Doe',
            amount_donated=Decimal('100.00'),
            sent_to=profile,
            stripe_charge_id='ch_test123'
        )
        
        assert donor.pk is not None
        assert donor.email == 'donor@example.com'
        assert str(donor) == 'donor@example.com'
    
    def test_donor_creates_donation_signal(self):
        """Test that creating a Donor creates a Donation via signal"""
        profile = UserProfileFactory()
        balance = BalanceFactory(account=profile)
        
        initial_donation_count = Donation.objects.count()
        
        donor = DonorFactory(sent_to=profile)
        
        assert Donation.objects.count() == initial_donation_count + 1
        donation = Donation.objects.filter(donor=donor).first()
        assert donation is not None
        assert donation.receiver == balance


@pytest.mark.django_db
class TestDonationBalanceUpdates:
    """Test balance updates after donations"""
    
    def test_donation_updates_receiver_balance(self):
        """Test that donation updates receiver's balance"""
        profile = UserProfileFactory()
        balance = BalanceFactory(account=profile, balance=Decimal('50.00'))
        donor = DonorFactory(sent_to=profile, amount_donated=Decimal('25.00'))
        
        # Trigger signal by creating Donation
        Donation.objects.create(
            donor=donor,
            donation_amount=Decimal('25.00'),
            receiver=balance,
            stripe_charge_id='ch_test123'
        )
        
        balance.refresh_from_db()
        assert balance.balance == Decimal('75.00')
    
    def test_nonprofit_donation_updates_balance(self):
        """Test nonprofit donation updates nonprofit balance"""
        nonprofit = NonProfitFactory()
        from Alt.models import NonProfitBalance
        np_balance = NonProfitBalance.objects.create(nonprofit=nonprofit, balance=Decimal('0.00'))
        
        user = UserFactory()
        profile = user.profile
        
        NonProfitDonation.objects.create(
            nonprofit=nonprofit,
            donation_amount=Decimal('100.00'),
            profile_donated=profile
        )
        
        np_balance.refresh_from_db()
        assert np_balance.balance == Decimal('100.00')
    
    def test_atrocity_donation_updates_balance(self):
        """Test atrocity donation updates atrocity balance"""
        atrocity = AtrocityFactory()
        from Alt.models import AtrocityBalance
        at_balance = AtrocityBalance.objects.create(atrocity=atrocity, balance=Decimal('0.00'))
        
        user = UserFactory()
        profile = user.profile
        
        AtrocityDonation.objects.create(
            atrocity=atrocity,
            donation_amount=Decimal('75.00'),
            profile_donated=profile
        )
        
        at_balance.refresh_from_db()
        assert at_balance.balance == Decimal('75.00')


@pytest.mark.django_db
class TestCompanyMatching:
    """Test company donation matching functionality"""
    
    def test_company_match_donation_nonprofit(self):
        """Test company matches user donation to nonprofit"""
        # Setup
        user = UserFactory()
        profile = user.profile
        company = ForProfitCompanyFactory()
        company_balance = CompanyBalanceFactory(company=company, balance=Decimal('1000.00'))
        nonprofit = NonProfitFactory()
        
        # Create matching relationship
        CompanyNonProfitRelationshipFactory(
            company=company,
            nonprofit=nonprofit,
            match_level=50,  # 50% match
            funding_limit=500
        )
        
        # Create user donation with is_matched=True
        user_donation = UserDonationFactory(
            user=profile,
            nonprofit=nonprofit,
            dollar_amount=Decimal('100.00'),
            is_matched=True
        )
        
        # Verify company match donation was created
        match_donation = CompanyMatchDonation.objects.filter(
            transaction_matched=user_donation
        ).first()
        
        assert match_donation is not None
        assert match_donation.company == company
        assert match_donation.nonprofit == nonprofit
        # 50% of $100 = $50
        assert match_donation.amount == Decimal('50.00')
    
    def test_company_match_respects_funding_limit(self):
        """Test company match respects funding limit"""
        user = UserFactory()
        profile = user.profile
        company = ForProfitCompanyFactory()
        company_balance = CompanyBalanceFactory(company=company, balance=Decimal('1000.00'))
        nonprofit = NonProfitFactory()
        
        # Create matching relationship with low limit
        relationship = CompanyNonProfitRelationshipFactory(
            company=company,
            nonprofit=nonprofit,
            match_level=100,  # 100% match
            funding_limit=50  # Only $50 limit
        )
        
        # User donates $100, but limit is $50
        user_donation = UserDonationFactory(
            user=profile,
            nonprofit=nonprofit,
            dollar_amount=Decimal('100.00'),
            is_matched=True
        )
        
        match_donation = CompanyMatchDonation.objects.filter(
            transaction_matched=user_donation
        ).first()
        
        assert match_donation is not None
        # Should be capped at $50 due to limit
        assert match_donation.amount == Decimal('50.00')


@pytest.mark.django_db
class TestUserMatchRelationship:
    """Test user-to-user donation matching"""
    
    def test_user_match_relationship_creation(self):
        """Test creating a user match relationship"""
        matcher = UserProfileFactory()
        matched = UserProfileFactory()
        
        from Alt.models import UserMatchRelationShip
        relationship = UserMatchRelationShip.objects.create(
            user_matching_donation=matcher,
            user_being_matched=matched,
            match_level=25,  # 25% match
            funding_limit=100
        )
        
        assert relationship.pk is not None
        assert relationship.user_matching_donation == matcher
        assert relationship.user_being_matched == matched
    
    def test_user_match_transaction_created_on_donation(self):
        """Test user match transaction created when matched user donates"""
        matcher = UserProfileFactory()
        matched = UserProfileFactory()
        
        from Alt.models import UserMatchRelationShip, UserMatchTransaction
        relationship = UserMatchRelationShip.objects.create(
            user_matching_donation=matcher,
            user_being_matched=matched,
            match_level=50,  # 50% match
            funding_limit=200
        )
        
        # Create donation as matched user
        donation = UserDonationFactory(
            user=matched,
            dollar_amount=Decimal('100.00')
        )
        
        # Verify transaction was created
        transaction = UserMatchTransaction.objects.filter(
            relationship=relationship
        ).first()
        
        assert transaction is not None
        assert transaction.total_amount == 50.00  # 50% of $100
