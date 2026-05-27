# FairPrice Watchdog - Integration Tests

## Overview
This directory contains integration tests for the FairPrice Watchdog API using pytest and httpx.

## Test Coverage
- **test_health_check**: Verifies the health endpoint returns 200
- **test_create_scan**: Tests creating a new scan with valid URL
- **test_get_scan**: Tests retrieving scan details by ID
- **test_get_scan_not_found**: Tests 404 response for non-existent scan
- **test_get_results**: Tests retrieving complete scan results with listings and fees
- **test_get_results_not_found**: Tests 404 response for non-existent results
- **test_generate_complaint**: Tests ZIP bundle generation endpoint
- **test_generate_complaint_not_found**: Tests 404 response for non-existent scan
- **test_generate_complaint_bundle_contents**: Validates ZIP file structure and contents

## Prerequisites
1. PostgreSQL database running (for integration tests)
2. Redis running (for queue operations)
3. Python dependencies installed: `pip install -r requirements.txt`

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with verbose output:
```bash
pytest -v
```

### Run specific test:
```bash
pytest tests/test_api.py::test_health_check
```

### Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Test Database Setup
The tests use a separate test database to avoid affecting production data. The database is created and torn down for each test function using fixtures.

## Environment Variables
Tests use the `.env` file in the root directory. For test-specific configuration, you can create a `.env.test` file.

## Notes
- Tests are async and use `pytest-asyncio`
- Each test gets a fresh database session via the `db_session` fixture
- The `sample_scan` fixture creates test data with listings, fees, and evidence snapshots
- Tests use httpx AsyncClient to make HTTP requests to the FastAPI app

## Made with Bob