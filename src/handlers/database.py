"""MCP Database tool handlers."""

import json
from typing import Any, Dict, List

from mcp.types import Tool, CallToolResult, TextContent

from src.database.operations import get_database_operations
from src.utils.logger import get_logger


class DatabaseHandlers:
    """MCP tool handlers for database operations."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_ops = get_database_operations()

    def get_tools(self) -> List[Tool]:
        """Get list of available MCP tools."""
        return [
            Tool(
                name="execute_query",
                description="Execute a safe SELECT query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query"},
                        "limit": {"type": "integer", "default": 1000}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="list_tables",
                description="List all tables",
                inputSchema={"type": "object", "properties": {}}
            )
        ]

    async def handle_execute_query(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle execute_query tool call."""
        try:
            query = arguments.get("query", "")
            limit = arguments.get("limit", 1000)
            
            result = self.db_ops.execute_query(query, limit=limit)
            
            if result["success"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Query failed: {result['error']}"
                    )],
                    isError=True
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )],
                isError=True
            )

    async def handle_list_tables(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle list_tables tool call."""
        try:
            result = self.db_ops.list_tables()
            
            if result["success"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Failed: {result['error']}"
                    )],
                    isError=True
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )],
                isError=True
            )

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Route tool calls."""
        if name == "execute_query":
            return await self.handle_execute_query(arguments)
        elif name == "list_tables":
            return await self.handle_list_tables(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            ) 