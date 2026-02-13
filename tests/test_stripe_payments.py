"""
Tests for Stripe PaymentIntent creation and payment flows
Uses mocking to avoid real Stripe API calls
"""
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status


@pytest.mark.unit
@pytest.mark.stripe
class TestStripePaymentIntent:
    """Test Stripe PaymentIntent creation with mocked Stripe API"""

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.create')
    @patch('stripe.EphemeralKey.create')
    def test_create_payment_intent_nonprofit(
        self, mock_ephemeral, mock_customer, mock_payment_intent, 
        authenticated_client, test_user_with_profile, test_nonprofit
    ):
        """
        Test creating PaymentIntent for nonprofit donation.
        
        Setup: Mock Stripe Customer, PaymentIntent, and EphemeralKey
        Input: $10.00 donation amount (1000 cents)
        Expected: HTTP 200 with client_secret and payment intent ID
        """
        # Configure mocks
        mock_customer.return_value = MagicMock(id='cus_test123')
        mock_payment_intent.return_value = MagicMock(
            id='pi_test123',
            client_secret='pi_test123_secret_xyz'
        )
        mock_ephemeral.return_value = MagicMock(secret='eph_test_secret')
        
        url = reverse('userprofile-add-user-donation-to-non-profit', 
                     kwargs={'pk': test_user_with_profile.profile.pk})
        data = {
            'amount': 1000,  # $10.00 in cents
            'id': test_nonprofit.slug,
            'donation_type': 'S'  # Stripe payment
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'client_secret' in response.data
        assert response.data['client_secret'] == 'pi_test123_secret_xyz'
        
        # Verify Stripe API was called
        mock_customer.assert_called_once()
        mock_payment_intent.assert_called_once()

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.create')
    def test_stripe_error_handling(
        self, mock_customer, mock_payment_intent,
        authenticated_client, test_user_with_profile, test_nonprofit
    ):
        """
        Test graceful handling of Stripe errors.
        
        Setup: Mock Stripe to raise an error
        Expected: HTTP 400 with error message
        """
        import stripe
        mock_customer.return_value = MagicMock(id='cus_test')
        mock_payment_intent.side_effect = stripe.error.StripeError(
            message='Card declined',
            code='card_declined'
        )
        
        url = reverse('userprofile-add-user-donation-to-non-profit',
                     kwargs={'pk': test_user_with_profile.profile.pk})
        data = {
            'amount': 1000,
            'id': test_nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_payment_intent_requires_auth(
        self, api_client, test_user_with_profile, test_nonprofit
    ):
        """
        Test that unauthenticated users cannot create PaymentIntents.
        
        Expected: HTTP 401 Unauthorized
        """
        url = reverse('userprofile-add-user-donation-to-non-profit',
                     kwargs={'pk': test_user_with_profile.profile.pk})
        data = {
            'amount': 1000,
            'id': test_nonprofit.slug,
            'donation_type': 'S'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
class TestStripeConfig:
    """Test Stripe configuration endpoint"""

    def test_get_stripe_publishable_key(self, api_client):
        """
        Test that Stripe public key is accessible without auth.
        
        Expected: HTTP 200 with publicKey
        """
        url = '/stripe/config/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'publicKey' in response.data
