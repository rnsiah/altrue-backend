"""
Test factories for Altrue models using factory_boy
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users"""
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    is_active = True


class UserProfileFactory(DjangoModelFactory):
    """Factory for creating user profiles"""
    class Meta:
        model = 'api.UserProfile'

    user = factory.SubFactory(UserFactory)
    username = factory.SelfAttribute('user.username')
    city = 'Test City'
    state = 'TC'
    country = 'US'


class NonProfitFactory(DjangoModelFactory):
    """Factory for creating nonprofits"""
    class Meta:
        model = 'Alt.NonProfit'

    name = factory.Sequence(lambda n: f'NonProfit {n}')
    description = 'Test nonprofit description'
    slug = factory.Sequence(lambda n: f'nonprofit{n}')


class AtrocityFactory(DjangoModelFactory):
    """Factory for creating atrocities"""
    class Meta:
        model = 'Alt.Atrocity'

    title = factory.Sequence(lambda n: f'Atrocity {n}')
    region = 'Test Region'
    slug = factory.Sequence(lambda n: f'atrocity{n}')


class BalanceFactory(DjangoModelFactory):
    """Factory for user escrow balances"""
    class Meta:
        model = 'api.Balance'

    account = factory.SubFactory(UserProfileFactory)
    balance = 0


class AltruePointsFactory(DjangoModelFactory):
    """Factory for user point wallets"""
    class Meta:
        model = 'api.AltruePoints'

    account = factory.SubFactory(UserProfileFactory)
    balance = 0


class ForProfitCompanyFactory(DjangoModelFactory):
    """Factory for for-profit companies"""
    class Meta:
        model = 'Alt.ForProfitCompany'

    owner = factory.SubFactory(UserProfileFactory)
    name = factory.Sequence(lambda n: f'Company {n}')
    year_started = '2024'
    description = 'Test company description'


class CategoryFactory(DjangoModelFactory):
    """Factory for cause categories"""
    class Meta:
        model = 'Alt.Category'

    name = factory.Sequence(lambda n: f'Category {n}')
    image = 'https://example.com/cat.png'
    information = 'Test category information'


class ShirtFactory(DjangoModelFactory):
    """Factory for shirts"""
    class Meta:
        model = 'Alt.Shirt'

    name = factory.Sequence(lambda n: f'Shirt {n}')
    price = 35.00
    discount_price = 35.00
    points_needed_to_purchase = 3500
    shirt_type = 'tshirt'
    shirt_image = 'https://example.com/img.png'
    original_image = 'https://example.com/orig.png'
    quantity_limited = False
    shirt_style = 'standard'
    shirt_materials = 'cotton'
    category = factory.SubFactory(CategoryFactory)


class CategoryFactory(DjangoModelFactory):
    """Factory for cause categories"""
    class Meta:
        model = 'Alt.Category'

    name = factory.Sequence(lambda n: f'Category {n}')
    image = 'https://example.com/cat.png'
    information = 'Test category information'


class AltrueActionFactory(DjangoModelFactory):
    """Factory for platform actions (points rate card)"""
    class Meta:
        model = 'Alt.AltrueAction'

    requirement = factory.Sequence(lambda n: f'Test action requirement {n}')
    info = 'Test action info'
    points_awarded = 15


class NonProfitProjectFactory(DjangoModelFactory):
    """Factory for nonprofit projects"""
    class Meta:
        model = 'Alt.NonProfitProject'

    nonprofit = factory.SubFactory(NonProfitFactory)
    title = factory.Sequence(lambda n: f'Project {n}')
    information = 'Test project information'
    fundraising_goal = 10000


class OrderFactory(DjangoModelFactory):
    """Factory for orders"""
    class Meta:
        model = 'Alt.Order'

    user = factory.SubFactory(UserProfileFactory)
    stripe_id = factory.Sequence(lambda n: f'order_test_{n}')


class RatingFactory(DjangoModelFactory):
    """Factory for ratings"""
    class Meta:
        model = 'Alt.Rating'

    user = factory.SubFactory(UserProfileFactory)
    nonprofit = factory.SubFactory(NonProfitFactory)
    stars = 5


class UserDonationFactory(DjangoModelFactory):
    """Factory for user wallet donations"""
    class Meta:
        model = 'api.UserDonation'

    user = factory.SubFactory(UserProfileFactory)
    # Reuse the wallet the user-creation signal already minted —
    # Balance.account is a OneToOne; a second Balance violates it.
    wallet = factory.SelfAttribute('user.balance')
    dollar_amount = 25.00
    donation_type = 'S'


class CompanyNonProfitRelationshipFactory(DjangoModelFactory):
    """Factory for company match relationships"""
    class Meta:
        model = 'Alt.CompanyNonProfitRelationship'

    company = factory.SubFactory(ForProfitCompanyFactory)
    nonprofit = factory.SubFactory(NonProfitFactory)
    match_level = 50


class AltrueActionCodeFactory(DjangoModelFactory):
    """Factory for action codes"""
    class Meta:
        model = 'Alt.AltrueActionCode'

    code = factory.Sequence(lambda n: f'ACTION_CODE_{n}')


class DonorFactory(DjangoModelFactory):
    """Factory for donors (external donor chain)"""
    class Meta:
        model = 'api.Donor'

    email = factory.Sequence(lambda n: f'donor{n}@example.com')
    first_name = 'Test'
    last_name = factory.Sequence(lambda n: f'Donor{n}')
    amount_donated = 25.00
    sent_to = factory.SubFactory(UserProfileFactory)
    stripe_charge_id = factory.Sequence(lambda n: f'ch_test_{n}')


class AltrueLevelFactory(DjangoModelFactory):
    """Factory for point levels"""
    class Meta:
        model = 'Alt.AltrueLevel'

    level_number = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f'Level {n + 1}')
    minimum_points = 0
    maximum_points = 1000000


class DonationFactory(DjangoModelFactory):
    """Factory for donation records"""
    class Meta:
        model = 'api.Donation'

    stripe_charge_id = factory.Sequence(lambda n: f'ch_don_{n}')
    donor = factory.SubFactory(DonorFactory)
    donation_amount = 25.00
    receiver = factory.SubFactory(BalanceFactory)


class AltrueActionTypeFactory(DjangoModelFactory):
    """Factory for action types"""
    class Meta:
        model = 'Alt.AltrueActionType'

    code = factory.Sequence(lambda n: f'ACTION_TYPE_{n}')
    description = factory.Sequence(lambda n: f'Test action type {n}')
