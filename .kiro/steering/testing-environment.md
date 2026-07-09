# Testing Environment Notes

## Python Availability

Python is NOT available on the system PATH.

### How to Verify Code

Use `get_diagnostics` on each Python file after writing it.

### Running Tests

To run pytest:
1. Install Python from python.org
2. `pip install -r backend/requirements-dev.txt`
3. `cd backend && python -m pytest tests/ -v`
