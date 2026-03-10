"""Tests for the omega logging framework."""

import logging

from omega.logging import (
    OmegaFormatter,
    OmegaLogger,
    get_logger,
    log_context,
    setup_logging,
    trace,
)


class CaptureHandler(logging.Handler):
    """Test handler that captures formatted log records."""

    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.formatted: list[str] = []
        self.setFormatter(OmegaFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.formatted.append(self.format(record))


def _make_capture_logger(name: str, level: int = logging.DEBUG) -> tuple[OmegaLogger, CaptureHandler]:
    """Create an OmegaLogger backed by a CaptureHandler for testing."""
    stdlib_logger = logging.getLogger(name)
    stdlib_logger.setLevel(level)
    stdlib_logger.handlers.clear()
    stdlib_logger.propagate = False
    handler = CaptureHandler()
    stdlib_logger.addHandler(handler)
    return OmegaLogger(stdlib_logger), handler


class TestGetLogger:
    def test_returns_omega_logger(self):
        logger = get_logger("omega.test.get")
        assert isinstance(logger, OmegaLogger)

    def test_same_name_returns_same_instance(self):
        a = get_logger("omega.test.cache_a")
        b = get_logger("omega.test.cache_a")
        assert a is b

    def test_different_names_return_different_instances(self):
        a = get_logger("omega.test.cache_x")
        b = get_logger("omega.test.cache_y")
        assert a is not b

    def test_name_property(self):
        logger = get_logger("omega.test.name_prop")
        assert logger.name == "omega.test.name_prop"


class TestOmegaLogger:
    def test_debug_with_kwargs(self):
        logger, handler = _make_capture_logger("omega.test.debug_kw")
        logger.debug("hello", key="value")
        assert len(handler.records) == 1
        assert handler.records[0].omega_kwargs == {"key": "value"}

    def test_info_message(self):
        logger, handler = _make_capture_logger("omega.test.info")
        logger.info("test message")
        assert len(handler.records) == 1
        assert "test message" in handler.formatted[0]

    def test_warning_message(self):
        logger, handler = _make_capture_logger("omega.test.warn")
        logger.warning("caution")
        assert "WARNING" in handler.formatted[0]

    def test_error_message(self):
        logger, handler = _make_capture_logger("omega.test.err")
        logger.error("failure")
        assert "ERROR" in handler.formatted[0]

    def test_kwargs_appear_in_formatted_output(self):
        logger, handler = _make_capture_logger("omega.test.kw_fmt")
        logger.info("stub called", function="GetObjProperty", args=("weapon", "SlayType"))
        output = handler.formatted[0]
        assert "function='GetObjProperty'" in output
        assert "SlayType" in output

    def test_level_filtering(self):
        logger, handler = _make_capture_logger("omega.test.filter", level=logging.WARNING)
        logger.debug("should not appear")
        logger.info("should not appear")
        logger.warning("should appear")
        assert len(handler.records) == 1

    def test_is_enabled_for(self):
        logger, _ = _make_capture_logger("omega.test.enabled", level=logging.WARNING)
        assert not logger.is_enabled_for(logging.DEBUG)
        assert logger.is_enabled_for(logging.WARNING)


class TestLogContext:
    def test_context_appears_in_output(self):
        logger, handler = _make_capture_logger("omega.test.ctx")
        with log_context(hit=42, attacker="Warrior"):
            logger.info("damage calculated")
        output = handler.formatted[0]
        assert "hit=42" in output
        assert "attacker='Warrior'" in output

    def test_context_merges_with_kwargs(self):
        logger, handler = _make_capture_logger("omega.test.ctx_merge")
        with log_context(hit=1):
            logger.info("event", damage=15)
        output = handler.formatted[0]
        assert "hit=1" in output
        assert "damage=15" in output

    def test_nested_context(self):
        logger, handler = _make_capture_logger("omega.test.ctx_nest")
        with log_context(hit=1):
            with log_context(phase="physical"):
                logger.info("inner")
        output = handler.formatted[0]
        assert "hit=1" in output
        assert "phase='physical'" in output

    def test_context_does_not_leak(self):
        logger, handler = _make_capture_logger("omega.test.ctx_leak")
        with log_context(hit=99):
            pass
        logger.info("after context")
        output = handler.formatted[0]
        assert "hit=99" not in output

    def test_inner_context_overrides_outer(self):
        logger, handler = _make_capture_logger("omega.test.ctx_override")
        with log_context(hit=1):
            with log_context(hit=2):
                logger.info("check")
        output = handler.formatted[0]
        assert "hit=2" in output


class TestTrace:
    def test_trace_logs_entry_and_exit(self):
        logger, handler = _make_capture_logger("omega.test.trace_basic")

        @trace(logger_name="omega.test.trace_basic")
        def add(a, b):
            return a + b

        result = add(3, 4)
        assert result == 7
        assert len(handler.records) == 2
        assert "ENTER" in handler.formatted[0]
        assert "add(3, 4)" in handler.formatted[0]
        assert "EXIT" in handler.formatted[1]
        assert "7" in handler.formatted[1]

    def test_trace_logs_exception(self):
        logger, handler = _make_capture_logger("omega.test.trace_exc")

        @trace(logger_name="omega.test.trace_exc")
        def fail():
            raise ValueError("boom")

        try:
            fail()
        except ValueError:
            pass

        assert len(handler.records) == 2
        assert "ENTER" in handler.formatted[0]
        assert "raised ValueError" in handler.formatted[1]

    def test_trace_no_parens(self):
        """@trace without parentheses should work."""
        @trace
        def noop():
            return 42

        assert noop() == 42

    def test_trace_preserves_function_name(self):
        @trace(logger_name="omega.test.trace_name")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestSetupLogging:
    def test_setup_configures_omega_root(self):
        setup_logging(level=logging.DEBUG)
        root = logging.getLogger("omega")
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert not root.propagate

    def test_setup_subsystem_levels(self):
        setup_logging(
            level=logging.DEBUG,
            subsystem_levels={"omega.parser": logging.WARNING},
        )
        parser_logger = logging.getLogger("omega.parser")
        assert parser_logger.level == logging.WARNING

    def test_re_setup_clears_old_handlers(self):
        setup_logging(level=logging.INFO)
        setup_logging(level=logging.DEBUG)
        root = logging.getLogger("omega")
        assert len(root.handlers) == 1
