"""
Test Stripe PaymentIntent creation and related functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from tests.factories import UserFactory, UserProfileFactory, NonProfitFactory, AtrocityFactory, BalanceFactory


@pytest.mark.django_db
class TestStripePaymentIntent:
    """Test Stripe PaymentIntent creation"""
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.EphemeralKey.create')
    def test_create_payment_intent_nonprofit(self, mock_ephemeral, mock_intent, mock_customer, client):
        """Test creating PaymentIntent for nonprofit donation"""
        # Setup mocks
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_intent.return_value = MagicMock(
            id='pi_test123',
            client_secret='pi_test_secret_123'
        )
        mock_ephemeral.return_value = MagicMock(secret='eph_test_secret_123')
        
        # Create test data
        user = UserFactory()
        profile = user.profile
        nonprofit = NonProfitFactory()
        balance = BalanceFactory(account=profile)
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 500,  # $5.00 in cents
            'id': nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofiles/{profile.pk}/addUserDonationToNonProfit/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data
        assert 'client_secret' in response.data
        assert 'ephemeral_key' in response.data
        assert 'customer' in response.data
        
        # Verify Stripe calls
        mock_customer.assert_called_once()
        mock_intent.assert_called_once()
        mock_ephemeral.assert_called_once()
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.EphemeralKey.create')
    def test_create_payment_intent_atrocity(self, mock_ephemeral, mock_intent, mock_customer, client):
        """Test creating PaymentIntent for atrocity donation"""
        # Setup mocks
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_intent.return_value = MagicMock(
            id='pi_test123',
            client_secret='pi_test_secret_123'
        )
        mock_ephemeral.return_value = MagicMock(secret='eph_test_secret_123')
        
        # Create test data
        user = UserFactory()
        profile = user.profile
        atrocity = AtrocityFactory()
        balance = BalanceFactory(account=profile)
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 1000,  # $10.00 in cents
            'id': atrocity.pk,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofiles/{profile.pk}/addUserDonationToAtrocity/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data
        assert 'client_secret' in response.data
    
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_stripe_error(self, mock_intent, client):
        """Test handling Stripe errors"""
        import stripe
        mock_intent.side_effect = stripe.error.StripeError("Test error")
        
        user = UserFactory()
        profile = user.profile
        nonprofit = NonProfitFactory()
        token, _ = Token.objects.get_or_create(user=user)
        
        data = {
            'amount': 500,
            'id': nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = client.post(
            f'/api/userprofiles/{profile.pk}/addUserDonationToNonProfit/',
            data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_payment_intent_unauthorized(self, client):
        """Test creating PaymentIntent without authentication fails"""
        response = client.post('/api/userprofiles/1/addUserDonationToNonProfit/')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestStripeConfig:
    """Test Stripe configuration endpoints"""
    
    def test_get_stripe_config(self, client):
        """Test getting Stripe public key"""
        response = client.get('/stripe/config/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'publicKey' in response.data
    
    def test_stripe_checkout_session(self, client):
        """Test creating checkout session"""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.return_value = {'id': 'cs_test123'}
            
            response = client.get('/stripe/create-checkout-session/')
            
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStripeWebhooks:
    """Test Stripe webhook handling"""
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_checkout_completed(self, mock_construct, client):
        """Test handling checkout.session.completed webhook"""
        mock_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test123',
                    'amount_total': 1000
                }
            }
        }
        mock_construct.return_value = mock_event
        
        response = client.post(
            '/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_signature(self, mock_construct, client):
        """Test handling invalid webhook signature"""
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "test_sig"
        )
        
        response = client.post(
            '/stripe/webhook/',
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_sig'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_payload(self, mock_construct, client):
        """Test handling invalid webhook payload"""
        import stripe
        mock_construct.side_effect = ValueError("Invalid payload")
        
        response = client.post(
            '/stripe/webhook/',
            data='invalid json',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
