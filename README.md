# 🚀 Cloudberry MCP Server

**Author: Vance Chen**

A Model Context Protocol (MCP) server for secure and efficient access to Cloudberry Database, designed for AI applications.

![alt text](arch01.png)

## 📁 Project Structure

```
cbdb_mcp/
├── pyproject.toml          # Project configuration and dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── config/
│   ├── __init__.py
│   └── settings.py        # Configuration management
├── src/
│   ├── __init__.py
│   ├── server.py          # Main FastAPI application entry point
│   ├── mcp/               # MCP Protocol Implementation
│   │   ├── __init__.py
│   │   ├── prompts.py     # LLM Prompts (English & Chinese)
│   │   └── router.py      # MCP API Endpoints (Manifest, Tools, Resources)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py  # Database connection management
│   │   └── operations.py  # Asynchronous database operations
│   └── utils/
│       ├── __init__.py
│       └── logger.py      # Logging utilities
└── tests/                 # Test suite
    └── __init__.py
```

## 🛠️ Installation & Setup

### 1. Install Dependencies with UV

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# If 'uv' command is not found after installation, you might need to add it to your PATH.
# For example, for bash/zsh users, add the following to your ~/.bashrc or ~/.zshrc:
# export PATH="$HOME/.local/bin:$PATH"
# Then, source your shell configuration file: source ~/.bashrc (or ~/.zshrc)

# Install project dependencies
uv sync
```

### 2. Configure Environment Variables

Copy the environment template and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your Cloudberry database credentials and other settings. Ensure `CBDB_PORT` matches your database configuration (e.g., `15432`):

```env
# Cloudberry Database Configuration
CBDB_HOST=your_cloudberry_host
CBDB_PORT=15432 # Example: Update to your actual port
CBDB_DATABASE=your_database_name
CBDB_USER=your_username
CBDB_PASSWORD=your_password
CBDB_POOL_SIZE=10
CBDB_TIMEOUT=30

# MCP Server Configuration
MCP_SERVER_NAME=cloudberry-mcp
MCP_VERSION=1.0.0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security Configuration
CONFIG_ENCRYPTION_KEY=your_encryption_key_here

# Optional: SSL Configuration
CBDB_SSL_MODE=prefer
CBDB_SSL_CERT_PATH=
CBDB_SSL_KEY_PATH=
CBDB_SSL_CA_PATH=
```

## 🎯 Core Features

### 1. Configuration Management
- Environment variables and configuration file support
- Secure credential management
- Type-safe settings with validation

### 2. Database Connection
- Asynchronous connection pool management
- Health check mechanism
- Automatic reconnection
- Connection lifecycle management

### 3. MCP Tools (Implemented)
- **`run_readonly_sql`**: Executes a safe, read-only SQL query against the database.
- **Table Schema Resources**: Exposes detailed schema information for each database table as an MCP resource.
- **Natural Language Query Prompts**: Provides LLM-guidance prompts (English and Chinese) for converting natural language questions into SQL queries.

### 4. Security Features
- Multi-layer SQL injection protection
- Configuration encryption
- Connection timeout management
- Sensitive data masking

## 🔧 Technology Stack

- **Web Framework**: FastAPI
- **Asynchronous HTTP Client**: httpx
- **Data Validation**: Pydantic
- **Database Driver**: psycopg2-binary (PostgreSQL protocol compatible)
- **Configuration**: pydantic-settings
- **Logging**: structlog
- **Security**: cryptography
- **Package Management**: UV (Modern Python packaging)

## 📊 Development Status

### ✅ Completed
- Project architecture
- Configuration system
- Asynchronous database connection management
- Asynchronous database operations layer
- MCP server core (FastAPI-based)
- MCP Tool and Resource handlers
- SQL query execution tool (`run_readonly_sql`)
- Table schema inspection resources
- Multi-language LLM prompts
- Structured logging system

### 📋 Planned
- Comprehensive test suite
- Advanced database monitoring tools

## 🚀 Usage

1. Ensure Cloudberry Database is running and accessible (e.g., on port `15432`).
2. Configure environment variables in `.env`.
3. Start the MCP server:

```bash
# Ensure you are in the project root directory
# Run uvicorn from the virtual environment
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8000
```

The server will start on `http://0.0.0.0:8000`.

Access the MCP Manifest at `http://0.0.0.0:8000/mcp/v1/manifest` to see available tools, resources, and prompts.

## 🔒 Security

- All SQL queries are parameterized
- Sensitive configuration is encrypted
- Read-only operations by default
- Multi-layer security validation

## 🎪 AI Integration

This MCP server is designed to be integrated with Large Language Models (LLMs) that support the Model Context Protocol (MCP).

### Supported Platforms
- Any LLM or agent framework that can consume a RESTful MCP Manifest.
- Custom Python applications (via HTTP requests).

### Integration Example
LLMs can discover and interact with this service by first fetching the MCP Manifest:

```http
GET http://0.0.0.0:8000/mcp/v1/manifest
```

Once the manifest is retrieved, the LLM can:
- Call the `run_readonly_sql` tool to execute SQL queries.
- Fetch `table_schema_{schema_name}_{table_name}` resources to understand database structure.
- Utilize `natural_language_query_prompt` or `natural_language_query_prompt_zh` to guide its SQL generation process.

Example of calling the `run_readonly_sql` tool (from an LLM agent):

```python
import httpx

async def call_mcp_tool(tool_path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://0.0.0.0:8000{tool_path}", json=payload)
        response.raise_for_status()
        return response.json()

# Example: LLM generates SQL and calls the tool
sql_query = "SELECT * FROM public.users LIMIT 5;"
result = await call_mcp_tool("/mcp/v1/tools/run_readonly_sql", {"sql": sql_query})
print(result)
```

## 📖 Documentation

- [Architecture Guide](ARCHITECTURE.md)
- [API Reference](docs/api.md) (Planned)
- [Security Guide](docs/security.md) (Planned)
- [Contributing Guide](CONTRIBUTING.md) (Planned)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

Apache License 2.0 