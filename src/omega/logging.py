"""Omega logging framework.

All other modules use the public API here. Sink/format changes happen only in
this file — call sites never need to change.

Public API
----------
- get_logger(name)        → named logger with structured kwarg support
- setup_logging(...)      → configure once at startup
- log_context(**kwargs)   → context manager that attaches metadata to all nested log calls
- trace                   → decorator that logs function entry/exit at DEBUG
"""

from __future__ import annotations

import contextvars
import functools
import logging
import sys
from contextlib import contextmanager
from typing import Any

# ---------------------------------------------------------------------------
# Context variable — carries structured metadata through the call stack
# ---------------------------------------------------------------------------

_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "omega_log_context", default={}
)


@contextmanager
def log_context(**kwargs: Any):
    """Attach metadata to all log calls within this block.

    Usage::

        with log_context(hit=42, attacker="Warrior"):
            logger.info("damage calculated", damage=15)
            # output includes hit=42 attacker=Warrior damage=15
    """
    current = _log_context.get()
    merged = {**current, **kwargs}
    token = _log_context.set(merged)
    try:
        yield
    finally:
        _log_context.reset(token)


# ---------------------------------------------------------------------------
# Formatter — the only place output format is defined
# ---------------------------------------------------------------------------

class OmegaFormatter(logging.Formatter):
    """Human-readable console formatter that includes structured context."""

    def format(self, record: logging.LogRecord) -> str:
        # Base message
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(7)
        name = record.name

        msg = record.getMessage()

        # Append structured kwargs attached by OmegaLogger
        extra_kw: dict[str, Any] = getattr(record, "omega_kwargs", {})

        # Merge in context vars
        ctx = _log_context.get()
        if ctx or extra_kw:
            combined = {**ctx, **extra_kw}
            kv_str = " ".join(f"{k}={v!r}" for k, v in combined.items())
            msg = f"{msg}  [{kv_str}]"

        formatted = f"{timestamp} [{name}] {level} {msg}"

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = f"{formatted}\n{record.exc_text}"

        return formatted


# ---------------------------------------------------------------------------
# Logger wrapper — thin layer that accepts **kwargs on log calls
# ---------------------------------------------------------------------------

class OmegaLogger:
    """Wraps a standard logger to support structured keyword arguments.

    Usage::

        logger = get_logger("omega.runtime")
        logger.info("stub called", function="GetObjProperty", args=("weapon", "SlayType"))
    """

    __slots__ = ("_logger",)

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @property
    def name(self) -> str:
        return self._logger.name

    def _log(self, level: int, msg: str, kwargs: dict[str, Any]) -> None:
        if not self._logger.isEnabledFor(level):
            return
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            # Caller info — we go up 3 frames: _log -> debug/info/etc -> actual caller
            "(unknown)",
            0,
            msg,
            args=(),
            exc_info=None,
        )
        record.omega_kwargs = kwargs  # type: ignore[attr-defined]
        self._logger.handle(record)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, kwargs)

    def is_enabled_for(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)


# ---------------------------------------------------------------------------
# Logger cache
# ---------------------------------------------------------------------------

_loggers: dict[str, OmegaLogger] = {}


def get_logger(name: str) -> OmegaLogger:
    """Get or create a named OmegaLogger.

    Convention: use dotted names under ``omega.`` namespace::

        get_logger("omega.parser")
        get_logger("omega.interpreter")
        get_logger("omega.runtime")
        get_logger("omega.config")
        get_logger("omega.simulation")
    """
    if name not in _loggers:
        _loggers[name] = OmegaLogger(logging.getLogger(name))
    return _loggers[name]


# ---------------------------------------------------------------------------
# Setup — called once at startup to configure handlers and levels
# ---------------------------------------------------------------------------

_setup_done = False


def setup_logging(
    level: int = logging.INFO,
    subsystem_levels: dict[str, int] | None = None,
) -> None:
    """Configure the omega logging subsystem.

    Parameters
    ----------
    level:
        Default log level for all ``omega.*`` loggers.
    subsystem_levels:
        Override levels per logger name, e.g.
        ``{"omega.parser": logging.WARNING}`` to silence parser noise.
    """
    global _setup_done

    root = logging.getLogger("omega")
    root.setLevel(level)

    # Remove existing handlers on re-setup (e.g. in tests)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(OmegaFormatter())
    root.addHandler(handler)

    # Don't propagate to the root logger
    root.propagate = False

    if subsystem_levels:
        for name, lvl in subsystem_levels.items():
            logging.getLogger(name).setLevel(lvl)

    _setup_done = True


# ---------------------------------------------------------------------------
# Trace decorator
# ---------------------------------------------------------------------------

def trace(fn=None, *, logger_name: str | None = None):
    """Decorator that logs function entry and exit at DEBUG level.

    Usage::

        @trace
        def calculate_damage(attacker, defender):
            ...

        @trace(logger_name="omega.runtime")
        def GetObjProperty(obj, name):
            ...
    """
    def decorator(func):
        _logger = get_logger(logger_name or f"omega.{func.__module__}")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            arg_str = ", ".join(
                [repr(a) for a in args] +
                [f"{k}={v!r}" for k, v in kwargs.items()]
            )
            _logger.debug(f"ENTER {func.__qualname__}({arg_str})")
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"EXIT  {func.__qualname__} -> {result!r}")
                return result
            except Exception as exc:
                _logger.debug(f"EXIT  {func.__qualname__} raised {type(exc).__name__}: {exc}")
                raise

        return wrapper

    if fn is not None:
        # Called as @trace without parens
        return decorator(fn)
    return decorator
