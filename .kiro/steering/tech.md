# Tech Stack

## Language & Runtime
- Python 3.8–3.11
- Home Assistant custom integration (legacy YAML setup, no config flow)

## Key Dependencies
- `homeassistant >= 2026.2.3` (test env; production minimum is 2025.1.1)
- `voluptuous` — config and service call schema validation (`schema.py`)
- `aiohttp` / `requests` — HTTP communication with Neviweb REST API
- `pytest`, `pytest-cov`, `pytest-mock` — test framework

## Build & Tooling
- `pyproject.toml` — pytest configuration (coverage, markers, paths)
- `pytest.ini` — canonical pytest config (overrides pyproject.toml if both present)
- `tox.ini` — multi-env test matrix (py38–py311) + lint/black envs
- `.pre-commit-config.yaml` — pre-commit hooks (flake8, isort, codespell, black)
- `uv` / `uv.lock` — dependency locking

## Virtual Environment

All code execution MUST happen inside the virtual environment. Never run Python or pytest outside of it.

```bash
# Create the venv (only needed once, uses Python 3.13)
python3.13 -m venv venv

# Activate the venv (required before any command below)
source ./venv/bin/activate
```

The venv is located at `./venv/`. Always activate it first.

## Common Commands

All commands below assume the venv is already activated.

```bash
# Run full test suite with coverage
pytest

# Run tests without coverage (faster)
pytest --no-cov

# Run a specific test file
pytest tests/test_ha_interface.py

# Run tests matching a marker
pytest -m unit
pytest -m api

# Run linting via pre-commit
pre-commit run --all-files

# Run tox (all environments)
tox

# Run tox for a specific env
tox -e lint
tox -e black
```

## Coverage
- Reports generated in `htmlcov/` (HTML) and terminal (`--cov-report=term-missing`)
- Source: `custom_components/neviweb130`
- Branch coverage enabled (`--cov-branch`)
