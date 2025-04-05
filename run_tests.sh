#!/bin/bash
# Run tests locally with Python 3.13

# Ensure we have the latest dependencies
python3.13 -m pip install -r requirements-dev.txt

# Run tests with coverage
python3.13 -m pytest --cov=src tests/

# Show coverage report
python3.13 -m coverage report -m