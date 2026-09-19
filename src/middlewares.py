import logging

logger = logging.getLogger(__name__)


def log_request(method: str, path: str) -> None:
    """Log an incoming request."""
    logger.info(f"{method} {path}")


def log_error(error: str, method: str, path: str) -> None:
    """Log a request error."""
    logger.error(f"Error in {method} {path}: {error}")
