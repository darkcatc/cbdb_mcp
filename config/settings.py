"""
Application settings management using Pydantic Settings.

Author: Vance Chen
"""

import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(..., description="Database name")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    pool_size: int = Field(default=10, description="Connection pool size")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    
    # SSL Configuration
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca_path: Optional[str] = Field(default=None, description="SSL CA path")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v):
        """Validate connection pool size."""
        if not 1 <= v <= 100:
            raise ValueError("Pool size must be between 1 and 100")
        return v

    class Config:
        env_prefix = "CBDB_"


class MCPSettings(BaseSettings):
    """MCP server configuration settings."""

    server_name: str = Field(default="cloudberry-mcp", description="MCP server name")
    version: str = Field(default="1.0.0", description="MCP server version")

    class Config:
        env_prefix = "MCP_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = {"json", "text"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}")
        return v.lower()

    class Config:
        env_prefix = "LOG_"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    encryption_key: Optional[str] = Field(default=None, description="Configuration encryption key")

    class Config:
        env_prefix = "CONFIG_"


class AppSettings(BaseSettings):
    """Main application settings."""

    def __init__(self, **kwargs):
        """Initialize settings with environment variables and config files."""
        # Load from .env file if it exists
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv is optional
        
        super().__init__(**kwargs)

    @property
    def database(self) -> DatabaseSettings:
        """Get database settings."""
        return DatabaseSettings()

    @property
    def mcp(self) -> MCPSettings:
        """Get MCP settings."""
        return MCPSettings()

    @property
    def logging(self) -> LoggingSettings:
        """Get logging settings."""
        return LoggingSettings()

    @property
    def security(self) -> SecuritySettings:
        """Get security settings."""
        return SecuritySettings()

    class Config:
        env_nested_delimiter = "__"


# Global settings instance
settings = AppSettings() 