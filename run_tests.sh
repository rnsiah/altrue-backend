#!/bin/bash

# Altrue Backend Test Runner
# Usage: ./run_tests.sh [options]
# Options:
#   --unit        Run only unit tests
#   --integration Run only integration tests
#   --coverage    Run with coverage report
#   --fast        Run with parallel execution

set -e

echo "🧪 Altrue Backend Test Suite"
echo "=============================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Default options
PYTEST_ARGS="-v"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            PYTEST_ARGS="$PYTEST_ARGS -m 'not integration'"
            shift
            ;;
        --integration)
            PYTEST_ARGS="$PYTEST_ARGS -m integration"
            shift
            ;;
        --coverage)
            PYTEST_ARGS="$PYTEST_ARGS --cov=api --cov=Alt --cov=StripeAPI --cov-report=term-missing --cov-report=html"
            shift
            ;;
        --fast)
            PYTEST_ARGS="$PYTEST_ARGS -n auto"
            shift
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Run tests
echo "Running tests with args: $PYTEST_ARGS"
pytest tests/ $PYTEST_ARGS

# Check coverage threshold
if [[ "$PYTEST_ARGS" == *"--coverage"* ]]; then
    echo ""
    echo "📊 Coverage Report Available:"
    echo "   - Terminal output above"
    echo "   - HTML report: htmlcov/index.html"
fi

echo ""
echo "✅ Tests completed!"
