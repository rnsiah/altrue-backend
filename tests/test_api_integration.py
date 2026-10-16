"""
Integration tests for API endpoints
"""
import pytest
from rest_framework import status
from rest_framework.authtoken.models import Token

from tests.factories import (
    UserFactory, UserProfileFactory, NonProfitFactory, AtrocityFactory,
    ShirtFactory, CategoryFactory, ForProfitCompanyFactory, NonProfitProjectFactory
)


@pytest.mark.django_db
class TestUserProfileAPI:
    """Test UserProfile API endpoints"""
    
    def test_list_user_profiles(self, client, auth_client):
        """Test listing user profiles"""
        # Create some profiles
        UserProfileFactory()
        UserProfileFactory()
        
        response = auth_client.get('/api/userprofile/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_user_profile(self, client, auth_client):
        """Test retrieving specific user profile"""
        profile = UserProfileFactory()
        
        response = auth_client.get(f'/api/userprofile/{profile.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == profile.username
    
    def test_update_user_profile(self, auth_client):
        """Test updating user profile"""
        profile = UserProfileFactory()
        
        data = {
            'city': 'New York',
            'state': 'NY',
            'country': 'USA'
        }
        
        response = auth_client.patch(
            f'/api/userprofile/{profile.pk}/',
            data,
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['city'] == 'New York'


@pytest.mark.django_db
class TestNonProfitAPI:
    """Test NonProfit API endpoints"""
    
    def test_list_nonprofits(self, auth_client):
        """Test listing nonprofits"""
        NonProfitFactory()
        NonProfitFactory()
        
        response = auth_client.get('/api/nonprofits/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_nonprofit(self, auth_client):
        """Test retrieving specific nonprofit"""
        nonprofit = NonProfitFactory()
        
        response = auth_client.get(f'/api/nonprofits/{nonprofit.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == nonprofit.name


@pytest.mark.django_db
class TestAtrocityAPI:
    """Test Atrocity API endpoints"""
    
    def test_list_atrocities(self, auth_client):
        """Test listing atrocities"""
        AtrocityFactory()
        AtrocityFactory()
        
        response = auth_client.get('/api/atrocities/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_atrocity(self, auth_client):
        """Test retrieving specific atrocity"""
        atrocity = AtrocityFactory()
        
        response = auth_client.get(f'/api/atrocities/{atrocity.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == atrocity.title


@pytest.mark.django_db
class TestShirtAPI:
    """Test Shirt API endpoints"""
    
    def test_list_shirts(self, auth_client):
        """Test listing shirts"""
        ShirtFactory()
        ShirtFactory()
        
        response = auth_client.get('/api/shirts/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_shirt(self, auth_client):
        """Test retrieving specific shirt"""
        shirt = ShirtFactory()
        
        response = auth_client.get(f'/api/shirts/{shirt.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == shirt.name


@pytest.mark.django_db
class TestCompanyAPI:
    """Test ForProfitCompany API endpoints"""
    
    def test_list_companies(self, auth_client):
        """Test listing companies"""
        ForProfitCompanyFactory()
        ForProfitCompanyFactory()
        
        response = auth_client.get('/api/companies/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_company(self, auth_client):
        """Test retrieving specific company"""
        company = ForProfitCompanyFactory()
        
        response = auth_client.get(f'/api/companies/{company.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == company.name


@pytest.mark.django_db
class TestCategoryAPI:
    """Test Category API endpoints"""
    
    def test_list_categories(self, auth_client):
        """Test listing categories"""
        CategoryFactory()
        CategoryFactory()
        
        response = auth_client.get('/api/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2


@pytest.mark.django_db
class TestProjectAPI:
    """Test NonProfitProject API endpoints"""
    
    def test_list_projects(self, auth_client):
        """Test listing projects"""
        NonProfitProjectFactory()
        NonProfitProjectFactory()
        
        response = auth_client.get('/api/projects/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_retrieve_project(self, auth_client):
        """Test retrieving specific project"""
        project = NonProfitProjectFactory()
        
        response = auth_client.get(f'/api/projects/{project.pk}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == project.title


@pytest.fixture
def auth_client(client):
    """Fixture to create authenticated client"""
    user = UserFactory()
    token, _ = Token.objects.get_or_create(user=user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Token {token.key}'
    return client
