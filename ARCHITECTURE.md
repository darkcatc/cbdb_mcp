# 🏗️ Cloudberry Database MCP Server Architecture

## 📚 MCP Protocol Layer Architecture

The Cloudberry Database MCP Server implements a layered architecture designed for security, maintainability, and high performance, adhering to the Model Context Protocol (MCP) specification via a RESTful API.

### Layer Structure

#### 1. Transport Layer
- **Protocol**: HTTP/1.1 (RESTful API)
- **Implementation**: FastAPI
- **Purpose**: Handles client-server communication over standard HTTP.
- **Key Features**:
  - Standard HTTP methods (GET, POST)
  - JSON-based request/response bodies
  - Asynchronous I/O operations handled by FastAPI/Uvicorn

#### 2. Protocol Layer (MCP API Routing)
- **Core File**: `src/mcp/router.py`
- **Purpose**: Implements the MCP protocol endpoints, handling manifest generation, tool calls, and resource retrieval.
- **Implementation Details**:
  - `/mcp/v1/manifest`: Dynamically generates and serves the MCP manifest (listing tools, resources, and prompts).
  - `/mcp/v1/tools/{tool_name}`: Handles calls to defined MCP tools.
  - `/mcp/v1/resources/{resource_name}`: Serves defined MCP resources (e.g., table schemas, prompts).
- **Async Architecture**: All endpoints are asynchronous (`async def`) to leverage FastAPI's non-blocking capabilities.

#### 3. Tool & Resource Definition Layer
- **Core Files**: 
  - `src/mcp/router.py` (for endpoint definitions)
  - `src/mcp/prompts.py` (for prompt content)
- **Purpose**: Defines the specific MCP Tools, Resources, and Prompts exposed by the service.
- **Key Components**:
  - Standard MCP tool format (name, description, path, parameters).
  - Standard MCP resource format (name, description, type, path, content for prompts).
  - Unified error handling for API calls.
- **Tool Definition Example (Manifest Entry)**:
  ```json
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
  ```
- **Resource Definition Example (Manifest Entry for Table Schema)**:
  ```json
  {
    "name": "table_schema_public_users",
    "description": "Schema for the public.users table.",
    "type": "text",
    "path": "/mcp/v1/resources/table_schema_public_users"
  }
  ```
- **Prompt Definition Example (Manifest Entry)**:
  ```json
  {
    "name": "natural_language_query_prompt",
    "description": "A prompt to guide an LLM in converting natural language to a SQL query.",
    "type": "prompt",
    "content": "You are an expert AI assistant..."
  }
  ```

#### 4. Business Logic Layer
- **Core File**: `src/database/operations.py`
- **Purpose**: Encapsulates secure and **asynchronous** database operations.
- **Security Features**:
  1. Multi-layer Protection:
     - Whitelist validation
     - Dangerous pattern detection
     - Multi-statement prevention
  2. Automatic LIMIT protection
  3. Standardized result format

#### 5. Infrastructure Layer
- **Core Files**: 
  - `src/database/connection.py` (Connection Pool Management)
  - `config/settings.py` (Configuration Management)
  - `src/utils/logger.py` (Logging System)
- **Components**:
  1. Asynchronous Connection Pool Management
  2. Type-safe Configuration Management
  3. Structured Logging System

## 🛠️ Detailed Implementation Analysis

### 1. Database Connection Layer
```python
# Asynchronous connection pool management
# Initialized in src/server.py startup event
# Used by src/database/operations.py
```

### 2. Configuration Management
```python
# Configuration loaded from .env and managed by Pydantic Settings
# Example:
# class DatabaseSettings(BaseSettings):
#     host: str = Field(default="localhost")
#     port: int = Field(default=5432)
#     ...
```

### 3. Logging System
```python
# Structured logging using structlog
# Example:
# def log_database_operation(operation, query=None, duration=None, error=None):
#     return {
#         "operation": operation,
#         "component": "database",
#         "query": query[:200] + "..." if query else None,
#         "duration_seconds": round(duration, 4) if duration else None,
#         "status": "failed" if error else "success",
#         "error": error
#     }
```

## 🏗️ Architecture Design Principles

### 1. Protocol Standardization
- Strict adherence to MCP 1.0 protocol via RESTful API
- Standard JSON-based communication
- Unified tool, resource, and prompt definition format

### 2. Security First
- Multi-layer security validation
  - Whitelist checking
  - Pattern detection
  - Statement analysis
- Read-only operations (SELECT queries only)
- Parameterized queries for SQL injection prevention

### 3. Modular Design
```
cbdb_mcp/
├── src/
│   ├── mcp/             # MCP Protocol Implementation
│   │   ├── __init__.py
│   │   ├── prompts.py   # LLM Prompts (English & Chinese)
│   │   └── router.py    # MCP API Endpoints (Manifest, Tools, Resources)
│   ├── database/        # Database Operations
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── operations.py
│   ├── utils/           # Utilities
│   │   ├── __init__.py
│   │   └── logger.py
│   └── server.py        # Main FastAPI Application Entry Point
└── ...
```

### 4. Extensibility
- Modular MCP endpoint design allows easy addition of new tools and resources.
- Database abstraction layer for potential future database support.
- Configuration-driven design for flexible deployment.

### 5. Observability
- Complete operation tracing with structured logging.
- Performance metrics collection (via logging).
- Security audit logging.

## 🎯 Core Advantages

### 🔒 Enterprise-Grade Security
- ✅ 100% SQL injection protection (verified for read-only queries)
- ✅ Dangerous operation prevention
- ✅ Multi-statement injection protection
- ✅ Sensitive information masking

### ⚡ High-Performance Design
- ✅ Asynchronous processing with `asyncio.run_in_executor` for blocking I/O
- ✅ Connection pool reuse
- ✅ Intelligent query limiting
- ✅ Resource optimization

### 🛠️ Developer-Friendly
- ✅ Type-safe configuration with Pydantic Settings
- ✅ Unified error handling via FastAPI's HTTPException
- ✅ Comprehensive structured logging
- ✅ Clear documentation

### 🎪 AI Integration Optimized
- ✅ Standard MCP protocol compatibility via RESTful API
- ✅ AI-friendly JSON response format
- ✅ Intelligent error messages
- ✅ Context-aware responses
- ✅ **Multi-language Prompts (English & Chinese) for LLM guidance**

## Author
Vance Chen

## Version
1.0.0rade Security
- ✅ 100% SQL injection protection (verified)
- ✅ Dangerous operation prevention
- ✅ Multi-statement injection protection
- ✅ Sensitive information masking

### ⚡ High-Performance Design
- ✅ Connection pool reuse
- ✅ Asynchronous processing
- ✅ Intelligent query limiting
- ✅ Resource optimization

### 🛠️ Developer-Friendly
- ✅ Type-safe configuration
- ✅ Unified error handling
- ✅ Comprehensive logging
- ✅ Clear documentation

### 🎪 AI Integration Optimized
- ✅ Standard MCP protocol compatibility
- ✅ AI-friendly JSON response format
- ✅ Intelligent error messages
- ✅ Context-aware responses

## Author
Vance Chen

## Version
1.0.0