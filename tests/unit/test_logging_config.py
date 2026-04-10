import logging
from pathlib import Path

from core.logging_config import LogLevel, UnifiedLoggingConfig


def test_logging_config_uses_env_log_dir(monkeypatch, tmp_path):
    custom_log_dir = tmp_path / "service-logs"
    monkeypatch.setenv("LOG_DIR", str(custom_log_dir))

    config = UnifiedLoggingConfig("billing_service")

    assert config.log_dir == custom_log_dir
    assert custom_log_dir.exists()


def test_setup_logging_keeps_console_when_file_handlers_fail(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    def fail_file_handler(*args, **kwargs):
        raise PermissionError("not writable")

    monkeypatch.setattr(logging.handlers, "RotatingFileHandler", fail_file_handler)
    monkeypatch.setattr(logging, "FileHandler", fail_file_handler)

    config = UnifiedLoggingConfig("billing_service")
    logger = config.setup_logging(level=LogLevel.INFO)

    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)
    assert {type(handler).__name__ for handler in logger.handlers} == {"StreamHandler"}
