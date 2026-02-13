#!/bin/bash
# Quick test runner for local development
# Usage: ./run_tests.sh [test_path]

echo "=== Altrue Django Test Runner ==="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run tests
if [ -z "$1" ]; then
    echo "Running all tests..."
    pytest -v --tb=short
else
    echo "Running tests: $1"
    pytest "$1" -v --tb=short
fi
