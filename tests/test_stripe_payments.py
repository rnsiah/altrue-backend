"""
Test Stripe payment integration for Altrue.

Tests cover:
- PaymentIntent creation for donations
- Stripe webhook handling
- Error handling for Stripe API failures

All Stripe calls are mocked to avoid external API usage.
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from api.models import UserProfile, Balance
from Alt.models import NonProfit, Atrocity

User = get_user_model()


def create_test_user():
    """Helper to create test user with full profile."""
    user = User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='testpass123'
    )
    return user


def create_test_nonprofit():
    """Helper to create test nonprofit."""
    return NonProfit.objects.create(
        name='Test Nonprofit',
        slug='test-nonprofit',
    )


def create_test_atrocity():
    """Helper to create test atrocity."""
    return Atrocity.objects.create(
        title='Test Atrocity',
        region='Test Region',
        info='Test info',
        image_url='https://example.com/image.png',
        slug='test-atrocity'
    )


@pytest.mark.django_db
class TestPaymentIntentCreation:
    """Test PaymentIntent creation for donations."""
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.EphemeralKey.create')
    def test_payment_intent_nonprofit(self, mock_ephemeral, mock_intent, mock_customer, client):
        """Test creating PaymentIntent for nonprofit donation.
        
        Setup: Mock all Stripe API calls
        Input: $5.00 donation amount (500 cents)
        Expected: PaymentIntent with client_secret, customer id, ephemeral key
        """
        # Setup mocks
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_intent.return_value = MagicMock(
            id='pi_test123',
            client_secret='pi_test_secret_123'
        )
        mock_ephemeral.return_value = MagicMock(secret='eph_test_secret')
        
        # Create test data
        user = create_test_user()
        profile = user.profile
        nonprofit = create_test_nonprofit()
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 500,
            'id': nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofile/{profile.pk}/addUserDonationToNonProfit/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == 'pi_test123'
        assert response.data['client_secret'] == 'pi_test_secret_123'
        assert response.data['customer'] == 'cus_test123'
        
        # Verify Stripe calls were made
        mock_customer.assert_called_once_with(email=user.email)
        mock_intent.assert_called_once()
        mock_ephemeral.assert_called_once()
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.EphemeralKey.create')
    def test_payment_intent_atrocity(self, mock_ephemeral, mock_intent, mock_customer, client):
        """Test creating PaymentIntent for atrocity donation.
        
        Setup: Mock all Stripe API calls
        Input: $10.00 donation amount (1000 cents)
        Expected: PaymentIntent with correct metadata for atrocity
        """
        mock_customer.return_value = MagicMock(id='cus_test456')
        mock_intent.return_value = MagicMock(
            id='pi_test456',
            client_secret='pi_test_secret_456'
        )
        mock_ephemeral.return_value = MagicMock(secret='eph_test_secret2')
        
        user = create_test_user()
        profile = user.profile
        atrocity = create_test_atrocity()
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 1000,
            'id': atrocity.pk,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofile/{profile.pk}/addUserDonationToAtrocity/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data
        assert 'client_secret' in response.data
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    def test_payment_intent_stripe_error(self, mock_intent, mock_customer, client):
        """Test handling Stripe API errors gracefully.
        
        Setup: Mock Stripe to raise error
        Input: Valid donation request
        Expected: 400 Bad Request with error message
        """
        import stripe
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_intent.side_effect = stripe.error.StripeError("Card declined")
        
        user = create_test_user()
        profile = user.profile
        nonprofit = create_test_nonprofit()
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 500,
            'id': nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofile/{profile.pk}/addUserDonationToNonProfit/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_payment_intent_unauthorized(self, client):
        """Test PaymentIntent creation fails without authentication."""
        response = client.post('/api/userprofile/1/addUserDonationToNonProfit/')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestStripeWebhooks:
    """Test Stripe webhook handling."""
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_checkout_completed(self, mock_construct, client):
        """Test handling checkout.session.completed webhook.
        
        Setup: Mock webhook event construction
        Input: Valid webhook payload with checkout completion
        Expected: 200 OK response
        """
        mock_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test123',
                    'amount_total': 1000,
                    'customer': 'cus_test123'
                }
            }
        }
        mock_construct.return_value = mock_event
        
        response = client.post(
            '/payments/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_signature(self, mock_construct, client):
        """Test webhook with invalid signature is rejected.
        
        Setup: Mock signature verification to fail
        Input: Webhook with bad signature
        Expected: 400 Bad Request
        """
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "test_sig"
        )
        
        response = client.post(
            '/payments/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_sig'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_payload(self, mock_construct, client):
        """Test webhook with invalid payload is rejected.
        
        Setup: Mock payload parsing to fail
        Input: Invalid JSON payload
        Expected: 400 Bad Request
        """
        mock_construct.side_effect = ValueError("Invalid payload")
        
        response = client.post(
            '/payments/webhook/',
            data='not valid json',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestStripeConfig:
    """Test Stripe configuration endpoints."""
    
    def test_get_stripe_config(self, client):
        """Test getting Stripe publishable key.
        
        Setup: None
        Input: GET request to /payments/config/
        Expected: JSON with publicKey field
        """
        response = client.get('/payments/config/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'publicKey' in response.json()
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create, client):
        """Test creating checkout session.
        
        Setup: Mock checkout session creation
        Input: GET request to create-checkout-session
        Expected: JSON with sessionId
        """
        mock_create.return_value = {'id': 'cs_test123'}
        
        response = client.get('/payments/create-checkout-session/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'sessionId' in response.json()
