"""
Structured logging utility for Cloudberry MCP server.

Author: Vance Chen
"""

import logging
import sys
from typing import Any, Dict, Optional, Union

import structlog


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """
    Setup structured logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('json' or 'text')
    """
    # Configure standard library logging
    # IMPORTANT: Use stderr for MCP compatibility (stdout is used for protocol communication)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level.upper()),
    )
    
    # Configure structlog
    if format_type == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **kwargs: Any) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        **kwargs: Additional context to bind to the logger
        
    Returns:
        Configured structlog BoundLogger instance
    """
    logger = structlog.get_logger(name)
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


def log_database_operation(
    operation: str,
    query: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized log entry for database operations.
    
    Args:
        operation: Database operation type (e.g., 'query', 'connect', 'disconnect')
        query: SQL query (will be truncated if too long)
        params: Query parameters (sensitive data will be masked)
        duration: Operation duration in seconds
        error: Error message if operation failed
        
    Returns:
        Dictionary with standardized log data
    """
    log_data = {
        "operation": operation,
        "component": "database",
    }
    
    if query:
        # Truncate long queries
        log_data["query"] = query[:500] + "..." if len(query) > 500 else query
    
    if params:
        # Mask sensitive parameters
        masked_params = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in ["password", "token", "key", "secret"]):
                masked_params[key] = "***MASKED***"
            else:
                masked_params[key] = value
        log_data["params"] = masked_params
    
    if duration is not None:
        log_data["duration_seconds"] = round(duration, 4)
    
    if error:
        log_data["error"] = error
        log_data["status"] = "failed"
    else:
        log_data["status"] = "success"
    
    return log_data


def log_mcp_operation(
    tool_name: str,
    operation: str,
    duration: Optional[float] = None,
    error: Optional[str] = None,
    **context: Any,
) -> Dict[str, Any]:
    """
    Create a standardized log entry for MCP operations.
    
    Args:
        tool_name: Name of the MCP tool
        operation: Operation type (e.g., 'call', 'list_tools')
        duration: Operation duration in seconds
        error: Error message if operation failed
        **context: Additional context data
        
    Returns:
        Dictionary with standardized log data
    """
    log_data = {
        "tool_name": tool_name,
        "operation": operation,
        "component": "mcp",
    }
    
    if duration is not None:
        log_data["duration_seconds"] = round(duration, 4)
    
    if error:
        log_data["error"] = error
        log_data["status"] = "failed"
    else:
        log_data["status"] = "success"
    
    # Add additional context
    log_data.update(context)
    
    return log_data 