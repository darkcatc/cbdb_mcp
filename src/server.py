"""Cloudberry MCP Server main entry point."""

import asyncio
import sys
from typing import Any, Dict

from mcp.server import Server
from mcp import stdio_server
from mcp.types import CallToolResult, ListToolsResult

from config.settings import AppSettings
from src.database.connection import get_connection_manager
from src.handlers.database import DatabaseHandlers
from src.utils.logger import setup_logging, get_logger


class CloudberryMCPServer:
    """Cloudberry MCP Server."""

    def __init__(self):
        """Initialize server."""
        # Load settings and setup logging
        self.settings = AppSettings()
        setup_logging(self.settings.logging.level, self.settings.logging.format)
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.mcp_server = Server(self.settings.mcp.server_name)
        self.db_handlers = DatabaseHandlers()
        
        self.logger.info("MCP Server initialized")

    def setup_handlers(self):
        """Setup MCP handlers."""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            tools = self.db_handlers.get_tools()
            return ListToolsResult(tools=tools)

        @self.mcp_server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            return await self.db_handlers.call_tool(name, arguments)

    async def run(self):
        """Run the server."""
        try:
            # Initialize database
            get_connection_manager(self.settings.database)
            self.logger.info("Database connected")
            
            # Setup handlers
            self.setup_handlers()
            
            # Run server
            self.logger.info("Starting MCP server")
            async with stdio_server() as (read_stream, write_stream):
                await self.mcp_server.run(read_stream, write_stream)
                
        except Exception as e:
            self.logger.error("Server error", error=str(e))
            raise


async def main():
    """Main entry point."""
    server = CloudberryMCPServer()
    await server.run()


def cli_main():
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main() 