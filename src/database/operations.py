"""
Database operations for Cloudberry Database.

Author: Vance Chen
Provides safe SQL execution and database query capabilities.
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from src.database.connection import get_connection_manager
from src.utils.logger import get_logger, log_database_operation

# SQL injection protection patterns
DANGEROUS_SQL_PATTERNS = [
    r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\s+',
    r';.*\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\s+',
    r'--.*$',
    r'/\*.*?\*/',
    r'\bUNION\s+SELECT\b',
    r'\bEXEC\s*\(',
    r'\bEVAL\s*\(',
]


class DatabaseOperations:
    """Safe database operations wrapper."""

    def __init__(self):
        """Initialize database operations."""
        self.logger = get_logger(__name__, component="database_operations")

    def _is_safe_query(self, query: str) -> Tuple[bool, str]:
        """
        Check if query is safe to execute.
        
        Args:
            query: SQL query to check
            
        Returns:
            Tuple of (is_safe, reason)
        """
        query_upper = query.upper().strip()
        
        # Allow only SELECT, SHOW, DESCRIBE, EXPLAIN queries
        if not re.match(r'^\s*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN|WITH)\s+', query_upper):
            return False, "Only SELECT, SHOW, DESCRIBE, EXPLAIN queries are allowed"
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_SQL_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE | re.MULTILINE):
                return False, f"Query contains potentially dangerous pattern: {pattern}"
        
        # Check for multiple statements
        if ';' in query.strip()[:-1]:  # Allow trailing semicolon
            return False, "Multiple statements not allowed"
        
        return True, "Query is safe"

    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = 1000
    ) -> Dict[str, Any]:
        """
        Execute a safe SELECT query.
        
        Args:
            query: SQL query to execute
            params: Query parameters (for parameterized queries)
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with query results and metadata
        """
        start_time = time.time()
        
        try:
            # Safety check
            is_safe, reason = self._is_safe_query(query)
            if not is_safe:
                raise ValueError(f"Unsafe query rejected: {reason}")
            
            # Add LIMIT if not present and limit is specified
            if limit and not re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            conn_manager = get_connection_manager()
            
            with conn_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Get column names
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    # Fetch results
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        if hasattr(row, 'keys'):  # RealDictRow
                            results.append(dict(row))
                        else:  # Regular tuple
                            results.append(dict(zip(columns, row)))
                    
                    duration = time.time() - start_time
                    
                    log_data = log_database_operation(
                        operation="execute_query",
                        query=query[:200] + "..." if len(query) > 200 else query,
                        params=params,
                        duration=duration,
                    )
                    self.logger.info("Query executed successfully", **log_data)
                    
                    return {
                        "success": True,
                        "data": results,
                        "columns": columns,
                        "row_count": len(results),
                        "duration": duration,
                        "query": query
                    }
                    
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            log_data = log_database_operation(
                operation="execute_query",
                query=query[:200] + "..." if len(query) > 200 else query,
                params=params,
                duration=duration,
                error=error_msg,
            )
            self.logger.error("Query execution failed", **log_data)
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "duration": duration,
                "query": query
            }

    def list_tables(self, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        List tables in the database.
        
        Args:
            schema: Schema name (optional)
            
        Returns:
            Dictionary with table list and metadata
        """
        try:
            if schema:
                query = """
                SELECT schemaname, tablename, tableowner, hasindexes, hasrules, hastriggers 
                FROM pg_tables 
                WHERE schemaname = %s
                ORDER BY tablename
                """
                params = {"schema": schema}
            else:
                query = """
                SELECT schemaname, tablename, tableowner, hasindexes, hasrules, hastriggers 
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'gp_toolkit')
                ORDER BY schemaname, tablename
                """
                params = None
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self.logger.error("Failed to list tables", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def describe_table(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Describe table structure.
        
        Args:
            table_name: Name of the table
            schema: Schema name (optional)
            
        Returns:
            Dictionary with table structure information
        """
        try:
            # Build table reference
            if schema:
                full_table_name = f'"{schema}"."{table_name}"'
                schema_condition = "AND table_schema = %s"
                params = {"table_name": table_name, "schema": schema}
            else:
                full_table_name = f'"{table_name}"'
                schema_condition = "AND table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'gp_toolkit')"
                params = {"table_name": table_name}
            
            query = f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                ordinal_position
            FROM information_schema.columns 
            WHERE table_name = %(table_name)s
            {schema_condition}
            ORDER BY ordinal_position
            """
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self.logger.error("Failed to describe table", error=str(e), table=table_name, schema=schema)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def list_schemas(self) -> Dict[str, Any]:
        """
        List available schemas.
        
        Returns:
            Dictionary with schema list
        """
        try:
            query = """
            SELECT schema_name, schema_owner 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'gp_toolkit')
            ORDER BY schema_name
            """
            
            return self.execute_query(query)
            
        except Exception as e:
            self.logger.error("Failed to list schemas", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            query = """
            SELECT 
                current_database() as database_name,
                current_user as current_user,
                version() as version,
                (SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'gp_toolkit')) as table_count,
                (SELECT count(*) FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'gp_toolkit')) as schema_count
            """
            
            return self.execute_query(query)
            
        except Exception as e:
            self.logger.error("Failed to get database stats", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def preview_table(
        self, 
        table_name: str, 
        schema: Optional[str] = None, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Preview table data.
        
        Args:
            table_name: Name of the table
            schema: Schema name (optional)
            limit: Number of rows to preview
            
        Returns:
            Dictionary with table preview data
        """
        try:
            # Build table reference safely
            if schema:
                full_table_name = f'"{schema}"."{table_name}"'
            else:
                full_table_name = f'"{table_name}"'
            
            query = f"SELECT * FROM {full_table_name} LIMIT {limit}"
            
            return self.execute_query(query, limit=limit)
            
        except Exception as e:
            self.logger.error("Failed to preview table", error=str(e), table=table_name, schema=schema)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


# Global database operations instance
_db_operations: Optional[DatabaseOperations] = None


def get_database_operations() -> DatabaseOperations:
    """Get the global database operations instance."""
    global _db_operations
    
    if _db_operations is None:
        _db_operations = DatabaseOperations()
    
    return _db_operations 