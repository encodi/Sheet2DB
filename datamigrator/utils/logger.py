"""
Logger utility for DataMigrator

Provides configurable logging functionality for the entire library.
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "datamigrator", level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name. If None, returns the main datamigrator logger.
        
    Returns:
        Logger instance
    """
    if name is None:
        name = "datamigrator"
    
    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up with default configuration
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


def info(msg: str, logger_name: Optional[str] = None) -> None:
    """Log an info message."""
    get_logger(logger_name).info(msg)


def warning(msg: str, logger_name: Optional[str] = None) -> None:
    """Log a warning message."""
    get_logger(logger_name).warning(msg)


def error(msg: str, exc_info: bool = True, logger_name: Optional[str] = None) -> None:
    """Log an error message."""
    get_logger(logger_name).error(msg, exc_info=exc_info) 