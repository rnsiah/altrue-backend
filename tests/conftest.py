"""
Pytest fixtures and configuration
"""
import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from tests.factories import UserFactory, UserProfileFactory, NonProfitFactory, AtrocityFactory


@pytest.fixture
def api_client():
    """Return an unauthenticated API client"""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """Return an authenticated API client with token"""
    client = APIClient()
    user = UserFactory()
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def test_user():
    """Create a test user"""
    return UserFactory()


@pytest.fixture
def test_user_with_profile():
    """Create a test user with profile (created via signals)"""
    user = UserFactory()
    user.profile.username = user.username
    user.profile.save()
    return user


@pytest.fixture
def test_nonprofit():
    """Create a test nonprofit"""
    return NonProfitFactory()


@pytest.fixture
def test_atrocity():
    """Create a test atrocity"""
    return AtrocityFactory()
