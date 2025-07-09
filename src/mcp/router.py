
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database.operations import get_database_operations
from .prompts import NL_QUERY_PROMPT, NL_QUERY_PROMPT_ZH

router = APIRouter()

class RunSqlRequest(BaseModel):
    sql: str

@router.get("/manifest", tags=["MCP"])
async def get_mcp_manifest():
    """
    Provides the MCP manifest, detailing available resources, tools, and prompts.
    """
    try:
        db_ops = get_database_operations()
        schema_result = await db_ops.list_tables()
        
        if not schema_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve database schema: {schema_result['error']}")

        resources = []
        for table in schema_result["data"]:
            schema_name = table.get("schemaname")
            table_name = table.get("tablename")
            if schema_name and table_name:
                resource_name = f"table_schema_{schema_name}_{table_name}"
                resources.append({
                    "name": resource_name,
                    "description": f"Schema for the {schema_name}.{table_name} table.",
                    "type": "text",
                    "path": f"/mcp/v1/resources/{resource_name}"
                })
        
        # Add the English Natural Language Query Prompt as a resource
        resources.append({
            "name": "natural_language_query_prompt",
            "description": "A prompt in English to guide an LLM in converting natural language to a SQL query.",
            "type": "prompt",
            "content": NL_QUERY_PROMPT
        })

        # Add the Chinese Natural Language Query Prompt as a resource
        resources.append({
            "name": "natural_language_query_prompt_zh",
            "description": "一个中文 prompt，用于指导 LLM 将自然语言转换为 SQL 查询。",
            "type": "prompt",
            "content": NL_QUERY_PROMPT_ZH
        })

        manifest = {
            "mcp_version": "1.0",
            "service_info": {
                "name": "cbdb_mcp_service",
                "description": "A service to interact with a CloudberryDB database.",
                "version": "1.0.0"
            },
            "resources": resources,
            "tools": [
                {
                    "name": "run_readonly_sql",
                    "description": "Executes a read-only SQL query against the database.",
                    "type": "api",
                    "path": "/mcp/v1/tools/run_readonly_sql",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "The SQL query to execute."}
                        },
                        "required": ["sql"]
                    }
                }
            ]
        }
        return manifest
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools/run_readonly_sql", tags=["MCP"])
async def execute_sql_tool(request: RunSqlRequest):
    """
    MCP Tool endpoint to execute a read-only SQL query.
    """
    try:
        # Basic validation to prevent non-SELECT queries
        if not request.sql.lstrip().upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Only read-only SELECT queries are allowed.")
        
        db_ops = get_database_operations()
        result = await db_ops.execute_query(request.sql)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"SQL query execution failed: {result['error']}")

        return {"result": result["data"]}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/{resource_name}", tags=["MCP"])
async def get_table_schema_resource(resource_name: str):
    """
    MCP Resource endpoint to retrieve the schema of a specific table.
    The resource_name is expected to be in the format 'table_schema_{schema_name}_{table_name}'.
    """
    try:
        if not resource_name.startswith("table_schema_"):
            raise HTTPException(status_code=404, detail=f"Resource '{resource_name}' not found or invalid.")

        parts = resource_name.split('_')
        if len(parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid table schema resource name format.")
        
        schema_name = parts[2]
        table_name = "_".join(parts[3:])

        db_ops = get_database_operations()
        table_schema_result = await db_ops.describe_table(table_name, schema_name)
        
        if not table_schema_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve table schema: {table_schema_result['error']}")

        if not table_schema_result["data"]:
            raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found.")

        return table_schema_result["data"]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
