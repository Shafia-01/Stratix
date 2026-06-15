import logging
import logging.handlers
import os

def get_logger(name: str) -> logging.Logger:
    """
    Factory function to get a configured logger.
    Ensures idempotency to avoid duplicate handlers.
    """
    logger = logging.getLogger(name)

    # Configure the level from env var or default to INFO
    log_level_str = os.getenv("KEYLYTICS_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # If logger already has handlers, do not add more (idempotency guard)
    if logger.handlers:
        return logger

    # Ensure parent loggers don't duplicate logs if we add handlers here
    logger.propagate = False

    class RedactingFormatter(logging.Formatter):
        def format(self, record):
            formatted = super().format(record)
            from src.security_utils import redact_api_keys
            return redact_api_keys(formatted)

    formatter = RedactingFormatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # Optional Rotating File Handler
    log_file = os.getenv("KEYLYTICS_LOG_FILE")
    if log_file:
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback prints if log file setup fails
            print(f"Failed to setup file log handler at {log_file}: {e}")

    return logger
