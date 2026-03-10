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

---

## M2 — eScript Parser

**Date**: 2026-03-10

### Summary

Built a complete eScript parser using ANTLR4 with Python target, capable of parsing all 53 files in the shard's combat include chain with zero errors.

**Approach**: Used the existing ANTLR4 grammar from `submodules/escript-antlr4/`, generated Python lexer/parser, and patched 7 embedded JavaScript actions (`this.` → `self.`) plus 2 indentation fixes in the generated code.

**Files created**:
- `src/omega/parser/grammar/` — copied `.g4` files with Python-compatible patches
- `src/omega/parser/gen/` — generated ANTLR4 Python lexer, parser, visitor, listener
- `src/omega/parser/case_insensitive_stream.py` — `CaseInsensitiveInputStream` wrapping `antlr4.InputStream`, overrides `LA()` to lowercase for case-insensitive keyword matching while preserving original identifier text
- `src/omega/parser/include_resolver.py` — resolves `include "path"` (relative to `scripts/`) and `include ":pkg:file"` (via package map from `pkg.cfg`). Deduplicates includes, detects missing files
- `src/omega/parser/parser.py` — public API: `parse_text()`, `parse_file()`, `parse_with_includes()`. Collects errors via custom error listener, logs via `omega.parser` logger
- `scripts/generate_parser.sh` — regeneration script for when grammar changes

**Dependencies added**: `antlr4-python3-runtime>=4.13.2`

### Key decisions
- ANTLR4 over Lark: grammar exists and is tested, only minor patches needed
- Generated code checked into git: no ANTLR4 tooling required at runtime
- Parse tree walked directly by interpreter (no intermediate AST transformation)
- Include resolver uses `PackageMap` protocol: M3 will provide the real implementation, tests use `DictPackageMap`

### Test Criteria

- [ ] `uv run pytest -v` — all 109 tests pass (23 logging + 86 parser):
  - `TestVariables` (7 tests) — var/const declarations, array/struct/dict initializers
  - `TestControlFlow` (15 tests) — if/while/for/foreach/repeat/case/break/continue/return/exit
  - `TestFunctions` (7 tests) — function/program/exported/byref/default/unused params
  - `TestExpressions` (20 tests) — arithmetic, comparison, logical, member access, method calls, scoped calls, bitwise, .isa(), elvis, in, function references
  - `TestModules` (4 tests) — use/include declarations
  - `TestEnum` (1 test) — enum definition
  - `TestComposite` (3 tests) — real-world shard script patterns
  - `TestCaseInsensitiveKeywords` (8 tests) — IF/if/If, VAR/var, FUNCTION/function, etc.
  - `TestCasePreservation` (1 test) — identifier original case preserved in parse tree
  - `TestRelativePaths` (4 tests) — include resolution with .inc extension, missing file error
  - `TestPackagePaths` (3 tests) — `:combat:hitscriptinc` resolution, unknown package error
  - `TestDeduplication` (3 tests) — mark_included/is_included cycle detection
  - `TestSingleFileParse` (6 tests) — mainhit.src, hitscriptinc.inc, damages.inc, classes.inc, attributes.inc, client.inc
  - `TestParseWithIncludes` (4 tests) — full 53-file include chain, specific files present in results
- [ ] `parse_with_includes("mainhit.src")` parses 53 files with zero errors
- [ ] Case-insensitive: `IF`, `if`, `If` all parse identically
- [ ] `:combat:hitscriptinc` resolves to `pkg/systems/combat/include/hitscriptinc.inc`
