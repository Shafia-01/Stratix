import os
import logging
from src.logger_config import get_logger

def test_logger_get_instance():
    logger = get_logger("test_instance")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_instance"

def test_logger_idempotency():
    logger1 = get_logger("test_idempotent")
    handlers_count_1 = len(logger1.handlers)
    
    logger2 = get_logger("test_idempotent")
    handlers_count_2 = len(logger2.handlers)
    
    assert handlers_count_1 == handlers_count_2
    assert logger1 is logger2

def test_logger_level_env(monkeypatch):
    monkeypatch.setenv("KEYLYTICS_LOG_LEVEL", "DEBUG")
    # Using a unique logger name to avoid using a cached/pre-configured logger instance
    logger = get_logger("test_env_debug")
    assert logger.level == logging.DEBUG
