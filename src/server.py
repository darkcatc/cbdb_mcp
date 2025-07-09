
from fastapi import FastAPI
from .mcp.router import router as mcp_router
from config.settings import AppSettings
from src.database.connection import get_connection_manager

app = FastAPI(
    title="CloudberryDB MCP Service",
    description="Exposes CloudberryDB resources and tools via the Model-Controller-Proxy (MCP) protocol.",
    version="1.0.0",
)

# Include the MCP router with a specific prefix
app.include_router(mcp_router, prefix="/mcp/v1")

@app.get("/", tags=["Health"])
async def health_check():
    """
    A simple health check endpoint to confirm the service is running.
    """
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    print("MCP Service is starting up...")
    # Initialize database connection manager with settings
    settings = AppSettings()
    get_connection_manager(settings.database)

@app.on_event("shutdown")
async def shutdown_event():
    print("MCP Service is shutting down...")

