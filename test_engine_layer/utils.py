"""Utils - Logging and formatting utilities."""

import sys
import logging


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    @staticmethod
    def fail(text):
        """Format text as failure (red)."""
        return f"{Colors.RED}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text):
        """Format text as success (green)."""
        return f"{Colors.GREEN}{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def info(text):
        """Format text as info (blue)."""
        return f"{Colors.BLUE}{text}{Colors.RESET}"
    
    @staticmethod
    def warn(text):
        """Format text as warning (yellow)."""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"


def setup_logging():
    """Setup console logging while preserving any file handlers.
    
    Removes console handlers to avoid duplicates but preserves file handlers
    that may have been added by test fixtures.
    
    Returns the logger.
    """
    logger = logging.getLogger('sp_validation')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing console handlers to avoid duplicates, but preserve file handlers
    for handler in logger.handlers[:]:
        if not isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger
