"""
Database connection management for Cloudberry Database.

Author: Vance Chen
"""

import asyncio
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.settings import DatabaseSettings
from src.utils.logger import get_logger, log_database_operation


class CloudberryConnection:
    """Cloudberry Database connection manager with connection pooling."""

    def __init__(self, settings: DatabaseSettings):
        """
        Initialize connection manager.

        Args:
            settings: Database configuration settings
        """
        self.settings = settings
        self.logger = get_logger(__name__, component="database")
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None

    def _build_connection_string(self) -> str:
        """Build database connection string."""
        conn_params = {
            "host": self.settings.host,
            "port": self.settings.port,
            "dbname": self.settings.database,  # PostgreSQL uses 'dbname' not 'database'
            "user": self.settings.user,
            "password": self.settings.password,
            "connect_timeout": self.settings.timeout,
        }

        # Add SSL configuration if provided
        if self.settings.ssl_mode:
            conn_params["sslmode"] = self.settings.ssl_mode

        if self.settings.ssl_cert_path:
            conn_params["sslcert"] = self.settings.ssl_cert_path

        if self.settings.ssl_key_path:
            conn_params["sslkey"] = self.settings.ssl_key_path

        if self.settings.ssl_ca_path:
            conn_params["sslrootcert"] = self.settings.ssl_ca_path

        return " ".join([f"{key}={value}" for key, value in conn_params.items()])

    def initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            start_time = time.time()
            connection_string = self._build_connection_string()

            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.settings.pool_size,
                dsn=connection_string,
                cursor_factory=RealDictCursor,
            )

            duration = time.time() - start_time
            log_data = log_database_operation(
                operation="initialize_pool",
                duration=duration,
            )
            self.logger.info("Database connection pool initialized", **log_data)

        except Exception as e:
            duration = time.time() - start_time
            log_data = log_database_operation(
                operation="initialize_pool",
                duration=duration,
                error=str(e),
            )
            self.logger.error("Failed to initialize connection pool", **log_data)
            raise

    def close_pool(self) -> None:
        """Close the connection pool."""
        if self._pool:
            try:
                start_time = time.time()
                self._pool.closeall()
                self._pool = None

                duration = time.time() - start_time
                log_data = log_database_operation(
                    operation="close_pool",
                    duration=duration,
                )
                self.logger.info("Database connection pool closed", **log_data)

            except Exception as e:
                duration = time.time() - start_time
                log_data = log_database_operation(
                    operation="close_pool",
                    duration=duration,
                    error=str(e),
                )
                self.logger.error("Failed to close connection pool", **log_data)

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """
        Get a database connection from the pool.

        Yields:
            Database connection instance

        Raises:
            RuntimeError: If connection pool is not initialized
            psycopg2.Error: If connection cannot be established
        """
        if not self._pool:
            raise RuntimeError("Connection pool not initialized")

        connection = None
        try:
            start_time = time.time()
            connection = self._pool.getconn()

            duration = time.time() - start_time
            log_data = log_database_operation(
                operation="get_connection",
                duration=duration,
            )
            self.logger.debug("Database connection acquired", **log_data)

            yield connection

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e) if e else "Unknown error"
            log_data = log_database_operation(
                operation="get_connection",
                duration=duration,
                error=error_msg,
            )
            self.logger.error("Failed to get database connection", **log_data)
            
            if connection:
                try:
                    connection.rollback()
                except:
                    pass  # Ignore rollback errors
            raise
        finally:
            if connection:
                try:
                    self._pool.putconn(connection)
                    self.logger.debug("Database connection returned to pool")
                except Exception as return_error:
                    error_msg = str(return_error) if return_error else "Unknown error"
                    self.logger.error("Failed to return connection to pool", error=error_msg)

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    start_time = time.time()
                    cursor.execute("SELECT 1 as test_value")
                    result = cursor.fetchone()
                    
                    duration = time.time() - start_time
                    log_data = log_database_operation(
                        operation="test_connection",
                        query="SELECT 1 as test_value",
                        duration=duration,
                    )
                    
                    if result and result.get('test_value') == 1:
                        self.logger.info("Database connection test successful", **log_data)
                        return True
                    else:
                        log_data["error"] = "Unexpected test query result"
                        self.logger.error("Database connection test failed", **log_data)
                        return False

        except Exception as e:
            log_data = log_database_operation(
                operation="test_connection",
                query="SELECT 1",
                error=str(e),
            )
            self.logger.error("Database connection test failed", **log_data)
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database server information.

        Returns:
            Dictionary containing database information
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    start_time = time.time()
                    
                    # Get version information
                    cursor.execute("SELECT version() as db_version")
                    version_result = cursor.fetchone()
                    version = version_result['db_version'] if version_result else "Unknown"
                    
                    # Get current database name
                    cursor.execute("SELECT current_database() as db_name")
                    db_result = cursor.fetchone()
                    current_db = db_result['db_name'] if db_result else "Unknown"
                    
                    # Get current user
                    cursor.execute("SELECT current_user as db_user")
                    user_result = cursor.fetchone()
                    current_user = user_result['db_user'] if user_result else "Unknown"
                    
                    # Get server encoding
                    cursor.execute("SHOW server_encoding")
                    encoding_result = cursor.fetchone()
                    encoding = encoding_result.get('server_encoding') or encoding_result.get('Server_Encoding') or "Unknown"
                    
                    duration = time.time() - start_time
                    log_data = log_database_operation(
                        operation="get_database_info",
                        duration=duration,
                    )
                    self.logger.debug("Database info retrieved", **log_data)
                    
                    return {
                        "version": version,
                        "database": current_db,
                        "user": current_user,
                        "encoding": encoding,
                        "host": self.settings.host,
                        "port": self.settings.port,
                    }

        except Exception as e:
            log_data = log_database_operation(
                operation="get_database_info",
                error=str(e),
            )
            self.logger.error("Failed to get database info", **log_data)
            raise


# Global connection manager instance
_connection_manager: Optional[CloudberryConnection] = None


def get_connection_manager(settings: Optional[DatabaseSettings] = None) -> CloudberryConnection:
    """
    Get the global connection manager instance.

    Args:
        settings: Database settings (required for first call)

    Returns:
        CloudberryConnection instance
    """
    global _connection_manager
    
    if _connection_manager is None:
        if settings is None:
            raise ValueError("Database settings required for first call")
        _connection_manager = CloudberryConnection(settings)
        _connection_manager.initialize_pool()
    
    return _connection_manager


def close_connection_manager() -> None:
    """Close the global connection manager."""
    global _connection_manager
    
    if _connection_manager:
        _connection_manager.close_pool()
        _connection_manager = None 