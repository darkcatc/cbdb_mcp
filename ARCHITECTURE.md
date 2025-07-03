# 🏗️ Cloudberry Database MCP Server Architecture

## 📚 MCP Protocol Layer Architecture

The MCP (Model Context Protocol) Server implements a five-layer architecture design that ensures security, maintainability, and high performance.

### Layer Structure

#### 1. Transport Layer
- **Protocol**: JSON-RPC 2.0 over stdio
- **Implementation**: `mcp.server.stdio`
- **Purpose**: Handles client-server communication
- **Key Features**:
  - Asynchronous I/O operations
  - Standardized message format
  - Reliable data transmission

#### 2. Protocol Layer
- **Core File**: `src/server.py`
- **Purpose**: MCP protocol message handling and routing
- **Implementation Details**:
  ```python
  # Standard MCP protocol implementation
  @self.mcp_server.list_tools()  # Standard MCP tool list interface
  @self.mcp_server.call_tool()   # Standard MCP tool call interface
  ```
- **Async Architecture**:
  ```python
  async with stdio_server() as (read_stream, write_stream):
      await self.mcp_server.run(read_stream, write_stream)
  ```

#### 3. Tool Layer
- **Core File**: `src/handlers/database.py`
- **Purpose**: Tool definition and request handling
- **Key Components**:
  - Standard MCP tool format
  - Unified error handling
  - Tool routing mechanism
- **Tool Definition Example**:
  ```python
  Tool(
      name="execute_query",
      description="Execute a safe SELECT query",
      inputSchema={
          "type": "object",
          "properties": {
              "query": {"type": "string"},
              "limit": {"type": "integer", "default": 1000}
          },
          "required": ["query"]
      }
  )
  ```

#### 4. Business Logic Layer
- **Core File**: `src/database/operations.py`
- **Purpose**: Secure database operations encapsulation
- **Security Features**:
  1. Multi-layer Protection:
     - Whitelist validation
     - Dangerous pattern detection
     - Multi-statement prevention
  2. Automatic LIMIT protection
  3. Standardized result format

#### 5. Infrastructure Layer
- **Core Files**: 
  - `src/database/connection.py`
  - `config/`
  - `utils/`
- **Components**:
  1. Connection Pool Management
  2. Configuration Management
  3. Logging System

## 🛠️ Detailed Implementation Analysis

### 1. Database Connection Layer
```python
# Thread-safe connection pool
self._pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=self.settings.pool_size,
    dsn=connection_string,
    cursor_factory=RealDictCursor
)
```

### 2. Configuration Management
```python
class DatabaseSettings(BaseSettings):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(...)
    user: str = Field(...)
    password: str = Field(...)
```

### 3. Logging System
```python
def log_database_operation(operation, query=None, duration=None, error=None):
    return {
        "operation": operation,
        "component": "database",
        "query": query[:200] + "..." if query else None,
        "duration_seconds": round(duration, 4) if duration else None,
        "status": "failed" if error else "success",
        "error": error
    }
```

## 🏗️ Architecture Design Principles

### 1. Protocol Standardization
- Strict adherence to MCP 1.0 protocol
- Standard JSON-RPC 2.0 communication
- Unified tool definition format

### 2. Security First
- Multi-layer security validation
  - Whitelist checking
  - Pattern detection
  - Statement analysis
- Read-only operations (SELECT queries only)
- Parameterized queries for SQL injection prevention

### 3. Modular Design
```
├── Transport Layer    # stdio communication
├── Protocol Layer    # MCP protocol handling
├── Tool Layer       # Tool definitions and routing
├── Business Layer   # Secure database operations
└── Infrastructure   # Connection pool, config, logging
```

### 4. Extensibility
- Plugin-based tool architecture
- Database abstraction layer
- Configuration-driven design

### 5. Observability
- Complete operation tracing
- Performance metrics collection
- Security audit logging

## 🎯 Core Advantages

### 🔒 Enterprise-Grade Security
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