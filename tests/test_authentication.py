"""
Tests for User Authentication flows using dj_rest_auth
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.unit
class TestUserRegistration:
    """Test user registration via dj_rest_auth"""

    def test_user_registration_success(self, api_client):
        """
        Test successful user registration creates user, profile, and token.
        
        Expected: HTTP 201 with user data and auth token
        """
        url = reverse('rest_register')
        data = {
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'key' in response.data
        assert 'user' in response.data

    def test_user_registration_password_mismatch(self, api_client):
        """
        Test registration fails when passwords don't match.
        
        Expected: HTTP 400 with password error
        """
        url = reverse('rest_register')
        data = {
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'different123!',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
class TestUserLogin:
    """Test user login endpoint"""

    def test_login_success(self, api_client, test_user):
        """
        Test successful login returns auth token.
        
        Setup: Create user with known password
        Expected: HTTP 200 with token key
        """
        test_user.set_password('testpass123!')
        test_user.save()
        
        url = reverse('rest_login')
        data = {
            'email': test_user.email,
            'password': 'testpass123!',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'key' in response.data

    def test_login_invalid_credentials(self, api_client, test_user):
        """
        Test login with wrong password fails.
        
        Expected: HTTP 400 Bad Request
        """
        test_user.set_password('correctpass123!')
        test_user.save()
        
        url = reverse('rest_login')
        data = {
            'email': test_user.email,
            'password': 'wrongpassword',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
class TestTokenAuthentication:
    """Test token-based authentication"""

    def test_access_protected_endpoint_with_token(self, authenticated_client):
        """
        Test that authenticated requests work with valid token.
        
        Expected: HTTP 200 OK
        """
        url = reverse('userprofile-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

    def test_access_protected_endpoint_without_token(self, api_client):
        """
        Test that unauthenticated requests to protected endpoints fail.
        
        Expected: HTTP 401 Unauthorized
        """
        url = reverse('userprofile-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
