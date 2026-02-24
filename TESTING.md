# Altrue Testing Framework

This document outlines the comprehensive testing framework for the Altrue codebase.

## Backend Testing (Django/pytest)

### Quick Start

```bash
cd altbackend
source .venv/bin/activate
pip install -r requirements-test.txt
pytest
```

### Test Configuration

- **Test Settings**: `config/settings_test.py`
- **Test Configuration**: `pytest.ini`
- **Test Directory**: `tests/`

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── factories.py             # Model factories for testing
├── test_auth.py             # Authentication tests
├── test_stripe.py           # Stripe integration tests
├── test_donations.py        # Donation processing tests
├── test_points.py           # AltruePoints system tests
├── test_signals.py          # Django signals tests
└── test_api_integration.py  # API endpoint integration tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov=Alt --cov=StripeAPI

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::TestUserRegistration::test_user_registration_success

# Run with verbose output
pytest -v

# Run only fast tests (exclude slow/integration)
pytest -m "not slow and not integration"
```

### Coverage Report

Coverage reports are generated in multiple formats:
- Terminal output (default)
- HTML: `htmlcov/index.html`
- XML: `coverage.xml`

Target: 70%+ coverage on core modules (api, Alt, StripeAPI)

### Test Categories

- **unit**: Fast, isolated unit tests
- **integration**: Tests that interact with database/external services
- **slow**: Long-running tests
- **stripe**: Stripe-related tests (may require mocking)

### Environment Variables for Testing

Create a `.env.test` file:

```bash
SECRET_KEY=test-secret-key
DATABASE_URL=sqlite:///:memory:
REDIS_URL=redis://localhost:6379/0
STRIPE_TEST_SECRET_KEY=sk_test_...
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_...
STRIPE_TEST_ENDPOINT_SECRET=whsec_...
```

## Frontend Testing (Flutter)

### Quick Start

```bash
cd FRONTEND_FLUTTER/lovelovelove-master
flutter test
```

### Test Structure

```
test/
├── widget_test.dart                  # Main widget tests
├── widgets/
│   ├── login_form_test.dart          # Login form tests
│   ├── donation_flow_test.dart       # Donation flow tests
│   └── mission_control_test.dart     # Dashboard tests
└── integration/
    └── api_integration_test.dart     # API integration tests
```

### Running Tests

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# Run specific test file
flutter test test/widgets/login_form_test.dart

# Run integration tests
flutter test integration_test/
```

### Coverage Report

Generate coverage report:
```bash
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

## CI/CD

### GitHub Actions

#### Backend Workflow (`.github/workflows/test.yml`)

- Runs on: Push/PR to main, develop branches
- Services: PostgreSQL 15, Redis 7
- Jobs:
  1. **test**: Run pytest with coverage, upload to Codecov
  2. **lint**: Run flake8, black, isort

#### Frontend Workflow (`.github/workflows/test.yml`)

- Runs on: Push/PR to main, develop branches
- Jobs:
  1. **test**: Run flutter tests with coverage
  2. **build-android**: Build debug APK
  3. **build-ios**: Build iOS (no codesign)

### Required Secrets

Add these secrets in GitHub repository settings:

- `CODECOV_TOKEN`: Codecov upload token

## Critical Paths Tested

### Authentication
- User registration (dj-rest-auth)
- User login/logout
- Token authentication
- Profile creation signals

### Stripe Integration
- PaymentIntent creation
- Customer creation
- Ephemeral key generation
- Webhook handling
- Error handling

### Donations
- User donations (nonprofit, atrocity, project)
- External donor donations
- Company matching donations
- Balance updates
- Funding limit enforcement

### AltruePoints
- Point creation on profile
- Point transactions
- User action recording
- Level progression
- Promotion multipliers

### Signals
- UserProfile creation
- Balance creation
- NonProfitBalance creation
- AtrocityBalance creation
- CompanyBalance creation

## Test Data Requirements

### Factories (using factory_boy)

All test models can be created using factories:

```python
from tests.factories import UserFactory, NonProfitFactory, UserDonationFactory

# Create test user with profile, balance, points
user = UserFactory()

# Create test nonprofit with balance
nonprofit = NonProfitFactory()

# Create test donation
donation = UserDonationFactory(user=user.profile, nonprofit=nonprofit)
```

### Mocking External Services

Stripe calls are mocked in tests:

```python
from unittest.mock import patch, MagicMock

@patch('stripe.Customer.create')
@patch('stripe.PaymentIntent.create')
def test_payment(mock_intent, mock_customer):
    mock_customer.return_value = MagicMock(id='cus_test')
    mock_intent.return_value = MagicMock(id='pi_test', client_secret='secret')
    # Test code here
```

## Coverage Gaps

### Known Gaps (as of initial setup)

1. **WebSocket/Channels**: Real-time features need more testing
2. **Printful Integration**: Order fulfillment flow needs tests
3. **Email Notifications**: Email confirmation flows
4. **File Uploads**: Image/profile picture uploads
5. **QR Code Generation**: QR code generation and S3 upload
6. **Quiz System**: Quiz taking and scoring
7. **Social Features**: Following, posts, shares

### Priority for Phase 3

High priority:
1. Complete Stripe webhook handling tests
2. Add more donation edge cases
3. Test company matching limits thoroughly
4. Test user matching relationships

Medium priority:
1. Add tests for shirt ordering flow
2. Add tests for nonprofit/project management
3. Add tests for admin functionality

Low priority:
1. Quiz and social features
2. Notification system
3. Analytics/reporting

## Maintenance

### Adding New Tests

1. Create test file in `tests/` directory
2. Import factories from `tests.factories`
3. Use existing fixtures from `conftest.py`
4. Mark slow tests with `@pytest.mark.slow`
5. Mock external API calls

### Running Tests Before Commit

```bash
# Backend
cd altbackend
pytest --cov=api --cov=Alt --cov=StripeAPI --cov-fail-under=70

# Frontend
cd FRONTEND_FLUTTER/lovelovelove-master
flutter test
```

## Troubleshooting

### Backend Tests

**Issue**: Database errors
- Solution: Ensure test database is configured in `settings_test.py`

**Issue**: Stripe tests failing
- Solution: Check that `STRIPE_TEST_*` environment variables are set or mocks are properly configured

**Issue**: Import errors
- Solution: Ensure you're in the virtual environment and have installed test requirements

### Frontend Tests

**Issue**: Golden file tests failing
- Solution: Update golden files with `flutter test --update-goldens`

**Issue**: Integration tests timing out
- Solution: Increase timeout in `flutter_test_config.dart`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django documentation](https://pytest-django.readthedocs.io/)
- [factory_boy documentation](https://factoryboy.readthedocs.io/)
- [Flutter testing documentation](https://docs.flutter.dev/testing)
