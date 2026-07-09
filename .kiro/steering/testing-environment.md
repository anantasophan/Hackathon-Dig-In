# Testing Environment Notes

## Python Availability

**Python is NOT available on the system PATH.** Running `python` or `python3` in the terminal opens the Microsoft Store stub, not an actual Python interpreter.

### What This Means for Tasks

- `python -m py_compile <file>` will NOT work
- `python -m pytest ...` will NOT work
- `pip install` will NOT work from terminal

### How to Verify Code Instead

Use **`get_diagnostics`** on each Python file after writing it. This uses the language server (Pylance) to catch syntax errors, type errors, and import issues without needing a Python runtime.

```
get_diagnostics(paths=["c:\\Users\\robin\\OneDrive\\Documents\\Project Kiro\\backend\\shared\\my_module.py"])
```

If `get_diagnostics` returns no errors → the file is syntactically and semantically correct.

### Running Tests (When Needed)

To actually run pytest, the user must:
1. Install Python from python.org (not Microsoft Store)
2. `pip install -r backend/requirements-dev.txt`
3. `cd backend && python -m pytest tests/ -v`

Do not block task completion waiting for pytest to run. Verify with `get_diagnostics` and document that runtime testing requires Python to be installed.

## Project Structure

All backend code is under `c:\Users\robin\OneDrive\Documents\Project Kiro\backend\`.

Key paths:
- `backend/shared/` — shared modules (models, calculations, filters, pii_filter, athena_client, sorting)
- `backend/lambdas/<name>/handler.py` — Lambda function handlers
- `backend/tests/unit/` — unit tests
- `backend/tests/property/` — Hypothesis property tests
- `backend/tests/integration/` — integration tests
- `backend/glue_jobs/` — PySpark ETL jobs
- `backend/infrastructure/` — AWS CDK stacks

## Spec Files

- Spec path: `c:\Users\robin\OneDrive\Documents\Project Kiro\.kiro\specs\campaign-insight-generator\`
- `tasks.md` — task list and DAG
- `requirements.md` — full requirements in Bahasa Indonesia
- `design.md` — architecture and data models

## Import Convention for Shared Modules

Lambda handlers import shared modules as:
```python
from shared.models import CampaignOverviewRequest
from shared.calculations import calculate_take_up_rate
from shared.filters import apply_filters
from shared.pii_filter import strip_pii
from shared.athena_client import AthenaClient
from shared.sorting import sort_regional_performance
```

This assumes the `backend/` directory is on the Python path (configured via `pyproject.toml` and Lambda layer).
