#!/usr/bin/env python3
"""
Natural Language Query Parser for Database Operations.

Author: Vance Chen
This module parses natural language queries and converts them to database operations.
"""

import re
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.database.operations import get_database_operations
from src.database.connection import get_connection_manager
from src.utils.logger import get_logger
from config.settings import AppSettings


@dataclass
class QueryIntent:
    """Represents parsed query intention."""
    action: str  # "list_tables", "query_table", "describe_table"
    table_name: Optional[str] = None
    schema: Optional[str] = None
    where_conditions: Optional[str] = None
    limit: int = 10
    columns: Optional[List[str]] = None
    confidence: float = 0.0


class NaturalQueryParser:
    """Natural language query parser for database operations."""
    
    def __init__(self):
        """Initialize the parser."""
        self.logger = get_logger(__name__)
        
        # Initialize database connection
        self.settings = AppSettings()
        self.db_settings = self.settings.database
        self.connection_manager = get_connection_manager(self.db_settings)
        self.db_ops = get_database_operations()
        
        # Load available tables for reference
        self._load_available_tables()
        
        # Define query patterns
        self._init_patterns()
    
    def _load_available_tables(self):
        """Load available tables for query validation."""
        try:
            result = self.db_ops.list_tables()
            if result["success"]:
                self.available_tables = {}
                for table_info in result["data"]:
                    schema = table_info["schemaname"]
                    table = table_info["tablename"]
                    if schema not in self.available_tables:
                        self.available_tables[schema] = []
                    self.available_tables[schema].append(table)
                self.logger.info(f"Loaded {len(result['data'])} available tables")
            else:
                self.available_tables = {}
                self.logger.error(f"Failed to load tables: {result['error']}")
        except Exception as e:
            self.available_tables = {}
            self.logger.error(f"Error loading tables: {e}")
    
    def _init_patterns(self):
        """Initialize regex patterns for query parsing."""
        self.patterns = {
            # Table listing patterns
            'list_tables': [
                r'(?:有哪些|显示|列出|查看)(?:所有的?)?表',
                r'(?:show|list|display).*tables?',
                r'数据库.*表',
                r'tables?.*database'
            ],
            
            # Table query patterns
            'query_table': [
                r'(?:查询|显示|展示|查看).*?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*).*?(?:表|数据)',
                r'(?:select|query|show).*?(?:from\s+)?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*)',
                r'(?:帮我|请).*?(?:查询|显示|展示).*?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*)',
                r'(?:给我|显示).*?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*).*?(?:的数据|中的)',
            ],
            
            # Table description patterns
            'describe_table': [
                r'(?:描述|查看|显示).*?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*).*?(?:结构|字段|列)',
                r'(?:describe|desc).*?([a-zA-Z_]\w*\.?[a-zA-Z_]\w*)',
                r'([a-zA-Z_]\w*\.?[a-zA-Z_]\w*).*?(?:有哪些|什么).*?(?:字段|列)',
            ],
            
            # WHERE condition patterns
            'where_conditions': [
                r'(?:where|条件|过滤).*?([^，。；;]+)',
                r'(?:满足|符合).*?([^，。；;]+)',
                r'([a-zA-Z_]\w*)\s*(?:=|>|<|>=|<=|!=|like)\s*([\'"]?[^，。；;\s]+[\'"]?)',
            ],
            
            # LIMIT patterns
            'limit': [
                r'(?:限制|最多|前).*?(\d+).*?(?:行|条|个)',
                r'(?:limit|top)\s*(\d+)',
                r'(\d+)\s*(?:行|条|rows?)',
            ],
            
            # Column patterns
            'columns': [
                r'(?:显示|查看|选择).*?([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)\s*(?:字段|列)',
                r'(?:select)\s+([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)\s+(?:from)',
            ]
        }
    
    def _extract_table_name(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract table name and schema from text."""
        # Try to find table references in available tables
        text_lower = text.lower()
        
        # First, try to find exact matches
        for schema, tables in self.available_tables.items():
            for table in tables:
                # Check for schema.table format
                full_name = f"{schema}.{table}"
                if full_name.lower() in text_lower:
                    return table, schema
                
                # Check for just table name
                if table.lower() in text_lower:
                    return table, schema
        
        # If no exact match, try regex patterns
        for pattern in self.patterns['query_table']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_ref = match.group(1)
                if '.' in table_ref:
                    schema, table = table_ref.split('.', 1)
                    return table, schema
                else:
                    return table_ref, None
        
        return None, None
    
    def _extract_where_conditions(self, text: str) -> Optional[str]:
        """Extract WHERE conditions from text."""
        for pattern in self.patterns['where_conditions']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                condition = match.group(1).strip()
                if condition:
                    return condition
        return None
    
    def _extract_limit(self, text: str) -> int:
        """Extract LIMIT value from text."""
        for pattern in self.patterns['limit']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    limit = int(match.group(1))
                    if 1 <= limit <= 1000:  # Reasonable bounds
                        return limit
                except ValueError:
                    continue
        return 10  # Default limit
    
    def _extract_columns(self, text: str) -> Optional[List[str]]:
        """Extract column names from text."""
        for pattern in self.patterns['columns']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                columns_str = match.group(1)
                columns = [col.strip() for col in columns_str.split(',')]
                return [col for col in columns if col]
        return None
    
    def _calculate_confidence(self, intent: QueryIntent, text: str) -> float:
        """Calculate confidence score for the parsed intent."""
        confidence = 0.0
        text_lower = text.lower()
        
        # Base confidence based on action detection
        if intent.action == "list_tables":
            for pattern in self.patterns['list_tables']:
                if re.search(pattern, text_lower):
                    confidence += 0.8
                    break
        elif intent.action == "query_table":
            if intent.table_name:
                confidence += 0.6
                # Bonus if table exists
                if self._table_exists(intent.table_name, intent.schema):
                    confidence += 0.3
        elif intent.action == "describe_table":
            if intent.table_name:
                confidence += 0.7
                if self._table_exists(intent.table_name, intent.schema):
                    confidence += 0.3
        
        # Additional factors
        if intent.where_conditions:
            confidence += 0.1
        if intent.limit != 10:  # Non-default limit
            confidence += 0.05
        if intent.columns:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _table_exists(self, table_name: str, schema: str = None) -> bool:
        """Check if table exists in available tables."""
        if schema:
            return schema in self.available_tables and table_name in self.available_tables[schema]
        else:
            # Check all schemas
            for schema_tables in self.available_tables.values():
                if table_name in schema_tables:
                    return True
        return False
    
    def parse_query(self, query: str) -> QueryIntent:
        """Parse natural language query into structured intent."""
        query = query.strip()
        
        # Determine action type
        action = "query_table"  # Default action
        
        # Check for table listing
        for pattern in self.patterns['list_tables']:
            if re.search(pattern, query, re.IGNORECASE):
                action = "list_tables"
                break
        
        # Check for table description
        if action != "list_tables":
            for pattern in self.patterns['describe_table']:
                if re.search(pattern, query, re.IGNORECASE):
                    action = "describe_table"
                    break
        
        # Extract components
        table_name, schema = self._extract_table_name(query)
        where_conditions = self._extract_where_conditions(query)
        limit = self._extract_limit(query)
        columns = self._extract_columns(query)
        
        # Create intent
        intent = QueryIntent(
            action=action,
            table_name=table_name,
            schema=schema,
            where_conditions=where_conditions,
            limit=limit,
            columns=columns
        )
        
        # Calculate confidence
        intent.confidence = self._calculate_confidence(intent, query)
        
        return intent
    
    def execute_query(self, intent: QueryIntent) -> Dict[str, Any]:
        """Execute the parsed query intent."""
        try:
            if intent.action == "list_tables":
                return self._execute_list_tables(intent)
            elif intent.action == "query_table":
                return self._execute_query_table(intent)
            elif intent.action == "describe_table":
                return self._execute_describe_table(intent)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作类型: {intent.action}"
                }
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": f"查询执行失败: {str(e)}"
            }
    
    def _execute_list_tables(self, intent: QueryIntent) -> Dict[str, Any]:
        """Execute table listing."""
        result = self.db_ops.list_tables(intent.schema)
        if result["success"]:
            return {
                "success": True,
                "action": "list_tables",
                "data": result["data"],
                "row_count": result["row_count"],
                "message": f"找到 {result['row_count']} 个表"
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    
    def _execute_query_table(self, intent: QueryIntent) -> Dict[str, Any]:
        """Execute table data query."""
        if not intent.table_name:
            return {
                "success": False,
                "error": "未指定表名"
            }
        
        # Build query
        columns = "*" if not intent.columns else ", ".join(intent.columns)
        full_table_name = f'"{intent.schema}"."{intent.table_name}"' if intent.schema else f'"{intent.table_name}"'
        
        query = f"SELECT {columns} FROM {full_table_name}"
        
        if intent.where_conditions:
            query += f" WHERE {intent.where_conditions}"
        
        query += f" LIMIT {intent.limit}"
        
        result = self.db_ops.execute_query(query, limit=intent.limit)
        
        if result["success"]:
            return {
                "success": True,
                "action": "query_table",
                "table_name": intent.table_name,
                "schema": intent.schema,
                "where_conditions": intent.where_conditions,
                "limit": intent.limit,
                "data": result["data"],
                "row_count": result["row_count"],
                "query": query,
                "message": f"查询到 {result['row_count']} 行数据"
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    
    def _execute_describe_table(self, intent: QueryIntent) -> Dict[str, Any]:
        """Execute table description."""
        if not intent.table_name:
            return {
                "success": False,
                "error": "未指定表名"
            }
        
        result = self.db_ops.describe_table(intent.table_name, intent.schema)
        
        if result["success"]:
            return {
                "success": True,
                "action": "describe_table",
                "table_name": intent.table_name,
                "schema": intent.schema,
                "data": result["data"],
                "row_count": result["row_count"],
                "message": f"表 {intent.table_name} 有 {result['row_count']} 个字段"
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    
    def process_natural_query(self, query: str) -> Dict[str, Any]:
        """Process a natural language query end-to-end."""
        # Parse the query
        intent = self.parse_query(query)
        
        self.logger.info(f"Parsed intent: {intent}")
        
        # Check confidence threshold
        if intent.confidence < 0.3:
            return {
                "success": False,
                "error": f"查询意图不明确 (置信度: {intent.confidence:.2f})",
                "suggestion": "请提供更明确的查询语句，例如：'显示所有表'、'查询tpcds.web_sales表的数据'"
            }
        
        # Execute the query
        result = self.execute_query(intent)
        
        # Add metadata
        result["intent"] = intent
        result["confidence"] = intent.confidence
        
        return result


def demo_natural_queries():
    """Demo function to test natural language queries."""
    parser = NaturalQueryParser()
    
    # Test queries
    test_queries = [
        "数据库中有哪些表？",
        "显示所有表",
        "查询tpcds.web_sales表的数据",
        "给我显示web_sales表中的前5行数据",
        "帮我查看customer表的结构",
        "展示store_sales表中ws_quantity大于50的数据，限制10行",
        "描述一下call_center表有哪些字段",
    ]
    
    print("=== 自然语言查询解析器演示 ===")
    print()
    
    for query in test_queries:
        print(f"🔍 查询: {query}")
        print("-" * 60)
        
        result = parser.process_natural_query(query)
        
        if result["success"]:
            print(f"✅ 成功 (置信度: {result['confidence']:.2f})")
            print(f"📊 {result.get('message', '')}")
            if result.get('data'):
                print(f"📋 数据行数: {len(result['data'])}")
        else:
            print(f"❌ 失败: {result['error']}")
            if result.get('suggestion'):
                print(f"💡 建议: {result['suggestion']}")
        
        print()


if __name__ == "__main__":
    demo_natural_queries() 