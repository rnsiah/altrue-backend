"""
Test user authentication flows
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from tests.factories import UserFactory, UserProfileFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration endpoints"""
    
    def test_user_registration_success(self, client):
        """Test successful user registration creates user and profile"""
        data = {
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'username': 'testuser'
        }
        response = client.post('/dj-rest-auth/registration/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='test@example.com').exists()
        user = User.objects.get(email='test@example.com')
        assert hasattr(user, 'profile')
        assert Token.objects.filter(user=user).exists()
    
    def test_user_registration_duplicate_email(self, client):
        """Test registration with duplicate email fails"""
        UserFactory(email='existing@example.com')
        data = {
            'email': 'existing@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'username': 'testuser'
        }
        response = client.post('/dj-rest-auth/registration/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_user_registration_password_mismatch(self, client):
        """Test registration with mismatched passwords fails"""
        data = {
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'DifferentPass123!',
            'username': 'testuser'
        }
        response = client.post('/dj-rest-auth/registration/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login endpoints"""
    
    def test_user_login_success(self, client):
        """Test successful user login returns token"""
        user = UserFactory(email='test@example.com')
        user.set_password('TestPass123!')
        user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = client.post('/auth/login/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'key' in response.data
        assert Token.objects.filter(user=user).exists()
    
    def test_user_login_invalid_credentials(self, client):
        """Test login with invalid credentials fails"""
        data = {
            'email': 'test@example.com',
            'password': 'WrongPass123!'
        }
        response = client.post('/auth/login/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_user_login_missing_password(self, client):
        """Test login without password fails"""
        data = {
            'email': 'test@example.com'
        }
        response = client.post('/auth/login/', data, content_type='application/json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogout:
    """Test user logout endpoints"""
    
    def test_user_logout_success(self, client, auth_user):
        """Test successful logout invalidates token"""
        client.force_login(auth_user)
        response = client.post('/auth/logout/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_logout_unauthorized(self, client):
        """Test logout without authentication fails"""
        response = client.post('/auth/logout/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserProfile:
    """Test user profile endpoints"""
    
    def test_get_profile_authenticated(self, client, auth_user):
        """Test getting own profile when authenticated"""
        profile = auth_user.profile
        profile.username = 'testuser'
        profile.save()
        
        client.force_login(auth_user)
        token = Token.objects.get(user=auth_user)
        response = client.get(
            f'/api/userprofile/{profile.pk}/',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'
    
    def test_get_profile_unauthorized(self, client):
        """Test getting profile without authentication fails"""
        response = client.get('/api/userprofiles/1/')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_update_profile_success(self, client, auth_user):
        """Test updating profile fields"""
        profile = auth_user.profile
        client.force_login(auth_user)
        token = Token.objects.get(user=auth_user)
        
        data = {
            'city': 'New City',
            'state': 'NY',
            'zip': '54321'
        }
        response = client.patch(
            f'/api/userprofile/{profile.pk}/update_profile/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.city == 'New City'
        assert profile.state == 'NY'
    
    def test_profile_completion_creates_balance_and_points(self, client):
        """Test that creating a user creates Balance and AltruePoints"""
        user = UserFactory()
        
        assert hasattr(user, 'profile')
        assert hasattr(user.profile, 'balance')
        assert hasattr(user.profile, 'altrue_points')


@pytest.fixture
def auth_user():
    """Fixture to create authenticated user"""
    return UserFactory()


@pytest.fixture
def auth_client(client, auth_user):
    """Fixture to create authenticated client"""
    token, _ = Token.objects.get_or_create(user=auth_user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Token {token.key}'
    return client
