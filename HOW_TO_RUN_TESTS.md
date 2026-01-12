# How to Run Tests

## ⚠️ CRITICAL: Use Virtual Environment Python

**DO NOT use:** `python -m pytest` (uses system Python - will hang!)

**USE ONE OF THESE:**

### Option 1: Helper Script (Easiest)
```bash
./run_tests.sh
```

### Option 2: Direct venv Python
```bash
venv/bin/python -m pytest tests/ -v
```

### Option 3: Activate venv first
```bash
source venv/bin/activate
pytest tests/ -v
```

## Why?

- Tests use **mocked API calls** to avoid real network requests
- System Python doesn't have the mocks configured correctly
- Using system Python causes tests to hang waiting for real API calls
- All tests should complete in **under 1 second** when using venv Python

## Quick Test

Run this to verify you're using the right Python:
```bash
venv/bin/python -m pytest tests/test_config.py -v
```

Expected: All tests pass in < 1 second ✅
