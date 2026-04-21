#!/bin/bash
set -e
echo "Running tests with coverage reporting..."
pytest
echo "------------------------------------------"
echo "Coverage report generated."
