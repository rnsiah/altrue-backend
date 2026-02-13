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
