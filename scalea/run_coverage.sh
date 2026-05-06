#!/bin/bash
set -e
echo "Running tests with coverage reporting..."
pytest --cov=. --cov-report=xml --cov-report=term-missing