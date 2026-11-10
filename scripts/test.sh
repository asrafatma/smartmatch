#!/usr/bin/env bash
# SmartMatch Automated Test Runner
set -euo pipefail

echo "========================================="
echo "   SmartMatch Competition Test Suite     "
echo "========================================="

# Verify test environment variables
export FLASK_ENV=testing
export TESTING=true
export MONGODB_URI=mock
export SECRET_KEY=ci-test-secret-key-32-characters-minimum
export JWT_SECRET_KEY=ci-test-jwt-secret-key-32-characters-min
export UPLOAD_FOLDER=uploads

echo "[1/3] Checking dependencies..."
python -m pytest --version

echo "[2/3] Running Python lint & import checks..."
python -c "import app; print('App package imported successfully')"

echo "[3/3] Running test suite with pytest..."
python -m pytest tests/ -v --tb=short

echo "========================================="
echo "All SmartMatch tests passed successfully!"
echo "========================================="
exit 0
