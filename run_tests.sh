#!/bin/bash
# Run tests using the virtual environment's Python
# This ensures all dependencies and mocks work correctly

cd "$(dirname "$0")"
venv/bin/python -m pytest tests/ -v "$@"
