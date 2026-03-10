# Changelog to V1

## M0 + M1 — Project Scaffolding & Logging Framework

**Date**: 2026-03-10

### Summary

Established the project foundation: Python package structure, dependency management with `uv`, and a structured logging framework designed for sink-agnostic output.

**Project setup**:
- Installed `uv` 0.10.9 as the package manager
- Created `pyproject.toml` with hatchling build backend, pytest dev dependency, optional notebook dependencies (jupyterlab, matplotlib, numpy)
- Laid out `src/omega/` package with subpackages for each subsystem: parser, config, model, interpreter, runtime, simulation, reporting
- Created `tests/`, `notebooks/`, `.gitignore`
- Removed legacy `src/requirements.txt`

**Logging framework** (`src/omega/logging.py`):
- `get_logger(name)` — cached named loggers wrapping stdlib `logging.Logger`, with `**kwargs` on all log methods for structured key-value data
- `setup_logging(level, subsystem_levels)` — single entry point for configuring handlers and formatters; the only place sink/format changes are needed
- `log_context(**kw)` — context manager using `contextvars.ContextVar` to attach metadata (hit number, combatant names, etc.) to all nested log calls without threading through function signatures
- `@trace` — opt-in decorator logging ENTER/EXIT with args and return values at DEBUG level
- `OmegaFormatter` — human-readable console formatter; swappable for JSON or other formats by changing only `setup_logging()`, not call sites

### Test Criteria

- [ ] `uv sync --extra dev` completes without error
- [ ] `uv run python -c "import omega"` succeeds
- [ ] `uv run pytest -v` — all 23 tests pass:
  - `TestGetLogger` (4 tests) — logger creation, caching, naming
  - `TestOmegaLogger` (7 tests) — log levels, kwargs in output, level filtering
  - `TestLogContext` (5 tests) — context attachment, nesting, no leakage, override
  - `TestTrace` (4 tests) — entry/exit logging, exception logging, name preservation
  - `TestSetupLogging` (3 tests) — root config, subsystem levels, handler cleanup on re-setup
- [ ] Log output format matches: `YYYY-MM-DD HH:MM:SS [logger.name] LEVEL   message  [key=value ...]`
- [ ] Structured kwargs from `log_context()` and logger calls both appear in formatted output
