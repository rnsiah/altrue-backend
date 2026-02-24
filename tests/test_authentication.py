"""
Test authentication flows for Altrue Django backend.

Tests cover:
- User registration with email/password
- User login/logout with token authentication  
- Profile auto-creation via signals
- Token generation
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration endpoint at /dj-rest-auth/registration/"""
    
    def test_registration_success(self, client):
        """Test successful registration creates user, profile, balance, points, token."""
        data = {
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'username': 'testuser'
        }
        response = client.post(
            '/dj-rest-auth/registration/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email='test@example.com').exists()
        
        user = User.objects.get(email='test@example.com')
        assert hasattr(user, 'profile')
        assert hasattr(user.profile, 'balance')
        assert hasattr(user.profile, 'altrue_points')
        assert Token.objects.filter(user=user).exists()
    
    def test_registration_duplicate_email(self, client):
        """Test registration fails when email already exists."""
        User.objects.create_user(
            email='existing@example.com',
            username='existing',
            password='testpass123'
        )
        
        data = {
            'email': 'existing@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'username': 'testuser'
        }
        response = client.post(
            '/dj-rest-auth/registration/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_registration_password_mismatch(self, client):
        """Test registration fails when passwords do not match."""
        data = {
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'DifferentPass123!',
            'username': 'testuser'
        }
        response = client.post(
            '/dj-rest-auth/registration/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login endpoint at /dj-rest-auth/login/"""
    
    def test_login_success(self, client):
        """Test successful login returns auth token."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = client.post(
            '/dj-rest-auth/login/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'key' in response.data
        assert Token.objects.filter(user=user).exists()
    
    def test_login_invalid_password(self, client):
        """Test login fails with incorrect password."""
        User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword!'
        }
        response = client.post(
            '/dj-rest-auth/login/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_nonexistent_user(self, client):
        """Test login fails for user that does not exist."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        }
        response = client.post(
            '/dj-rest-auth/login/', 
            data, 
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogout:
    """Test user logout endpoint at /dj-rest-auth/logout/"""
    
    def test_logout_success(self, client):
        """Test logout invalidates token."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        token = Token.objects.create(user=user)
        
        response = client.post(
            '/dj-rest-auth/logout/',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_logout_unauthorized(self, client):
        """Test logout without authentication fails."""
        response = client.post('/dj-rest-auth/logout/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestProfileCreation:
    """Test profile auto-creation via Django signals"""
    
    def test_profile_created_with_user(self):
        """Test that UserProfile is auto-created when User is created."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        assert hasattr(user, 'profile')
        assert user.profile is not None
    
    def test_balance_created_with_profile(self):
        """Test that Balance is auto-created with profile."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        assert hasattr(user.profile, 'balance')
        assert user.profile.balance.balance == 0
    
    def test_points_created_with_profile(self):
        """Test that AltruePoints is auto-created with profile."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        assert hasattr(user.profile, 'altrue_points')
        assert user.profile.altrue_points.balance == 0
    
    def test_token_created_with_user(self):
        """Test that auth token is auto-created with user."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        assert Token.objects.filter(user=user).exists()
