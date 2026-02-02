import logging
import sys

from app.core.config import settings


class AppLogger:
    """Simple application logger."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message)
    
    def exception(self, message: str, **kwargs):
        self.logger.exception(message)


def get_logger(name: str) -> AppLogger:
    """Get a logger instance."""
    return AppLogger(name)