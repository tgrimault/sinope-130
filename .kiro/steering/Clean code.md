---
inclusion: always
---

# Clean Code Conventions

## Python Style

- Follow PEP 8. Line length is enforced by `black` — do not manually wrap lines to a different width.
- Use `isort` ordering: stdlib → third-party → local imports, each group separated by a blank line.
- Prefer explicit over implicit: avoid `*` imports, single-letter variable names (except loop indices), and magic numbers without a named constant.
- Use f-strings for interpolation. Avoid `%`-style formatting except inside `logger.*()` calls (the logging module defers interpolation, which is more efficient).

## Functions & Methods

- Keep functions focused on one thing. If a method needs a comment block to separate "phases", it should be split.
- Limit positional arguments to five or fewer. Use keyword-only arguments (`*`) for anything beyond that.
- Avoid mutable default arguments (`def f(x=[])`). Use `None` and assign inside the body.
- Return early to reduce nesting. Prefer guard clauses over deeply nested `if/else` trees.

## Async Patterns

- All HA entity callbacks (`async_update`, service handlers) must be `async def`. Never call blocking I/O directly from an async context — use `hass.async_add_executor_job()` if needed.
- Do not mix `asyncio.sleep` with synchronous `time.sleep`. Use `await asyncio.sleep()` in async code.
- Service handler coroutines registered via `hass.services.async_register()` receive `(call: ServiceCall)` — extract and validate parameters from `call.data` using the schema defined in `schema.py`.

## Defensive Coding

- Never assume an API response key exists. Use `.get()` with a safe default, or rely on `safe_get_device_attributes` from `helpers.py`.
- Do not let API error strings (`DVCATTRNSPTD`, `DVCACTNSPTD`, `DVCCOMMTO`, `DVCUNVLB`, `DVCBUSY`, `ACCDAYREQMAX`) propagate as unhandled exceptions. Catch, log, and return a safe value.
- HA entity properties (`current_temperature`, `hvac_mode`, etc.) must never raise. Return `None` or the HA-defined default when data is unavailable.
- Validate all service call inputs with a `voluptuous` schema in `schema.py` before any business logic runs.

## Logging

- Use the module-level logger obtained from `helpers.setup_logger()` — do not call `logging.getLogger()` directly in platform files.
- Use `logger.debug()` for per-poll data, `logger.warning()` for recoverable anomalies (unsupported attributes, reconnects), and `logger.error()` for unexpected failures.
- Pass arguments to the logger lazily: `logger.debug("value: %s", val)` — never `logger.debug(f"value: {val}")`.
- Do not log sensitive data (credentials, session tokens).

## Comments & Docstrings

- Write comments that explain *why*, not *what*. Code should be readable enough that the *what* is obvious.
- Public functions and classes should have a one-line docstring if their purpose is not immediately clear from the name and signature.
- Remove commented-out code before merging. Use version control for history.

## Readability

- Name booleans as questions: `is_connected`, `has_leak`, `supports_fan_mode`.
- Name collections in the plural: `devices`, `attributes`, `error_codes`.
- Avoid abbreviations unless they are domain-standard (e.g. `sku`, `ota`, `ha`).
- Group related constants, imports, and methods together. Within a class, order: `__init__` → properties → HA interface overrides → private helpers.
