#!/usr/bin/env python3
"""
AI-driven database table query script.

Author: Vance Chen
This script uses AI (Ollama) to understand user queries and retrieve database table information.
"""

import json
import asyncio
import subprocess
import requests
from typing import Dict, Any, List, Optional
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.database.operations import get_database_operations
from src.database.connection import get_connection_manager
from src.utils.logger import get_logger
from config.settings import AppSettings


class OllamaClient:
    """Simple Ollama API client."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.logger = get_logger(__name__)
        
    def check_connection(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama connection failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            self.logger.error(f"Failed to get models: {e}")
            return []
    
    def generate_response(self, prompt: str, model: str = "qwen3") -> Optional[str]:
        """Generate response using Ollama model."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 256,  # Reduce output length
                    "stop": ["\n\n", "问题:", "用户:"]  # Add stop words
                }
            }
            
            self.logger.info(f"Sending request to Ollama with model: {model}")
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload, 
                timeout=60  # Increase timeout to 60 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            return None


class AITableQueryManager:
    """AI-driven table query manager."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize settings and database connection
        self.settings = AppSettings()
        self.db_settings = self.settings.database
        
        # Initialize database connection manager with settings
        self.connection_manager = get_connection_manager(self.db_settings)
        
        # Now get database operations (which will use the initialized connection manager)
        self.db_ops = get_database_operations()
        self.ollama = OllamaClient()
        
    def get_database_tables(self) -> Dict[str, Any]:
        """Get all non-system tables from the database."""
        try:
            result = self.db_ops.list_tables()
            if result["success"]:
                self.logger.info(f"Retrieved {result['row_count']} tables from database")
                return result
            else:
                self.logger.error(f"Failed to get tables: {result['error']}")
                return {"success": False, "error": result["error"]}
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def query_table_data(self, table_name: str, schema: str = None, where_condition: str = None, limit: int = 10) -> Dict[str, Any]:
        """Query data from a specific table with optional WHERE condition."""
        try:
            # Build table reference
            if schema:
                full_table_name = f'"{schema}"."{table_name}"'
            else:
                full_table_name = f'"{table_name}"'
            
            # Build query
            query = f"SELECT * FROM {full_table_name}"
            
            # Add WHERE condition if provided
            if where_condition:
                query += f" WHERE {where_condition}"
            
            # Add LIMIT
            query += f" LIMIT {limit}"
            
            result = self.db_ops.execute_query(query, limit=limit)
            if result["success"]:
                self.logger.info(f"Retrieved {result['row_count']} rows from {full_table_name}")
                return result
            else:
                self.logger.error(f"Failed to query table {full_table_name}: {result['error']}")
                return {"success": False, "error": result["error"]}
        except Exception as e:
            self.logger.error(f"Table query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def describe_table_structure(self, table_name: str, schema: str = None) -> Dict[str, Any]:
        """Get table structure information."""
        try:
            result = self.db_ops.describe_table(table_name, schema)
            if result["success"]:
                self.logger.info(f"Retrieved structure for table {table_name}")
                return result
            else:
                self.logger.error(f"Failed to describe table {table_name}: {result['error']}")
                return {"success": False, "error": result["error"]}
        except Exception as e:
            self.logger.error(f"Table description failed: {e}")
            return {"success": False, "error": str(e)}
    
    def format_table_info(self, table_data: Dict[str, Any]) -> str:
        """Format table information for AI processing."""
        if not table_data.get("success") or not table_data.get("data"):
            return "No tables found or error occurred."
        
        tables_by_schema = {}
        for row in table_data["data"]:
            schema = row["schemaname"]
            table = row["tablename"]
            
            if schema not in tables_by_schema:
                tables_by_schema[schema] = []
            tables_by_schema[schema].append(table)
        
        formatted_info = []
        formatted_info.append(f"Database contains {len(table_data['data'])} tables across {len(tables_by_schema)} schemas:")
        
        for schema, tables in sorted(tables_by_schema.items()):
            formatted_info.append(f"\nSchema '{schema}' ({len(tables)} tables):")
            for table in sorted(tables):
                formatted_info.append(f"  - {table}")
        
        return "\n".join(formatted_info)
    
    def format_table_structure(self, structure_data: Dict[str, Any]) -> str:
        """Format table structure information for AI processing."""
        if not structure_data.get("success") or not structure_data.get("data"):
            return "无法获取表结构信息"
        
        formatted_info = []
        formatted_info.append("表结构信息:")
        
        for row in structure_data["data"]:
            column_name = row["column_name"]
            data_type = row["data_type"]
            is_nullable = row["is_nullable"]
            column_default = row.get("column_default", "")
            
            nullable_str = "可空" if is_nullable == "YES" else "非空"
            default_str = f", 默认值: {column_default}" if column_default else ""
            
            formatted_info.append(f"  - {column_name}: {data_type} ({nullable_str}{default_str})")
        
        return "\n".join(formatted_info)
    
    def format_table_data(self, table_data: Dict[str, Any]) -> str:
        """Format table data for AI processing."""
        if not table_data.get("success") or not table_data.get("data"):
            return "无数据或查询失败"
        
        data = table_data["data"]
        row_count = table_data["row_count"]
        
        formatted_info = []
        formatted_info.append(f"查询结果 ({row_count} 行):")
        
        if row_count == 0:
            formatted_info.append("  无数据")
            return "\n".join(formatted_info)
        
        # Get column names from first row
        if data:
            columns = list(data[0].keys())
            formatted_info.append(f"  列名: {', '.join(columns)}")
            
            # Show first few rows as examples
            max_rows = min(5, len(data))
            formatted_info.append(f"  数据样例 (前{max_rows}行):")
            
            for i, row in enumerate(data[:max_rows]):
                row_str = ", ".join([f"{k}={v}" for k, v in row.items()])
                formatted_info.append(f"    行{i+1}: {row_str}")
        
        return "\n".join(formatted_info)
    
    def create_table_list_prompt(self, user_query: str, table_info: str) -> str:
        """Create prompt for listing tables."""
        prompt = f"""数据库表查询助手。请简洁回答问题。

问题: {user_query}

表信息:
{table_info}

要求:
1. 用中文回答
2. 简洁明了，不要冗长解释
3. 按schema分组显示表名
4. 只列出表名，不需要其他详细信息

回答:"""

        return prompt
    
    def create_table_data_prompt(self, user_query: str, table_structure: str, table_data: str) -> str:
        """Create prompt for table data query."""
        prompt = f"""数据库查询助手。用户想查看表数据。

问题: {user_query}

表结构:
{table_structure}

表数据样例:
{table_data}

要求:
1. 用中文简洁回答
2. 解释查询结果
3. 如果有WHERE条件，说明过滤逻辑
4. 展示数据特点和统计信息

回答:"""

        return prompt
    
    def query_table_with_ai(self, table_name: str, schema: str = None, where_condition: str = None, limit: int = 10) -> Dict[str, Any]:
        """Query table data with AI assistance."""
        try:
            # Step 1: Check Ollama connection
            if not self.ollama.check_connection():
                return {
                    "success": False,
                    "error": "Ollama服务未运行或无法连接"
                }
            
            # Step 2: Get available models
            models = self.ollama.get_available_models()
            if not models:
                return {
                    "success": False,
                    "error": "没有可用的Ollama模型"
                }
            
            # Step 3: Get table structure
            table_structure = self.describe_table_structure(table_name, schema)
            if not table_structure["success"]:
                return {
                    "success": False,
                    "error": f"无法获取表结构: {table_structure['error']}"
                }
            
            # Step 4: Query table data
            table_data = self.query_table_data(table_name, schema, where_condition, limit)
            if not table_data["success"]:
                return {
                    "success": False,
                    "error": f"无法查询表数据: {table_data['error']}"
                }
            
            # Step 5: Format data for AI
            structure_info = self.format_table_structure(table_structure)
            data_info = self.format_table_data(table_data)
            
            # Step 6: Create query description
            full_table_name = f"{schema}.{table_name}" if schema else table_name
            query_desc = f"查询表 {full_table_name} 的数据"
            if where_condition:
                query_desc += f"，条件: {where_condition}"
            query_desc += f"，限制: {limit} 行"
            
            # Step 7: Create AI prompt
            prompt = self.create_table_data_prompt(query_desc, structure_info, data_info)
            
            # Step 8: Get AI response using the same model selection logic
            preferred_models = ["qwen3-4b", "qwen2:1.5b", "llama3.2:1b", "qwen3", "qwen2", "llama3.2"]
            selected_model = None
            
            for preferred in preferred_models:
                for available in models:
                    if preferred in available.lower():
                        selected_model = available
                        break
                if selected_model:
                    break
            
            if not selected_model:
                models_with_size = []
                for model in models:
                    try:
                        response = requests.get(f"http://localhost:11434/api/show", 
                                               json={"name": model}, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            size = data.get("size", float('inf'))
                            models_with_size.append((model, size))
                    except:
                        models_with_size.append((model, float('inf')))
                
                if models_with_size:
                    models_with_size.sort(key=lambda x: x[1])
                    selected_model = models_with_size[0][0]
                else:
                    selected_model = models[0]
            
            self.logger.info(f"Using model: {selected_model}")
            ai_response = self.ollama.generate_response(prompt, selected_model)
            
            if ai_response is None:
                return {
                    "success": False,
                    "error": "AI模型无法生成响应"
                }
            
            return {
                "success": True,
                "table_name": table_name,
                "schema": schema,
                "where_condition": where_condition,
                "ai_response": ai_response,
                "row_count": table_data["row_count"],
                "table_data": table_data["data"],
                "table_structure": table_structure["data"],
                "model_used": selected_model
            }
            
        except Exception as e:
            self.logger.error(f"Table query processing failed: {e}")
            return {
                "success": False,
                "error": f"处理查询时出错: {str(e)}"
            }

    def query_with_ai(self, user_query: str) -> Dict[str, Any]:
        """Process user query with AI assistance."""
        try:
            # Step 1: Check Ollama connection
            if not self.ollama.check_connection():
                return {
                    "success": False,
                    "error": "Ollama服务未运行或无法连接"
                }
            
            # Step 2: Get available models
            models = self.ollama.get_available_models()
            if not models:
                return {
                    "success": False,
                    "error": "没有可用的Ollama模型"
                }
            
            self.logger.info(f"Available models: {models}")
            
            # Step 3: Get database table information
            table_data = self.get_database_tables()
            if not table_data["success"]:
                return {
                    "success": False,
                    "error": f"无法获取数据库表信息: {table_data['error']}"
                }
            
            # Step 4: Format table information
            table_info = self.format_table_info(table_data)
            
            # Step 5: Create AI prompt
            prompt = self.create_table_list_prompt(user_query, table_info)
            
            # Step 6: Get AI response
            # Use the first available model, prefer smaller ones for faster response
            preferred_models = ["qwen3-4b", "qwen2:1.5b", "llama3.2:1b", "qwen3", "qwen2", "llama3.2"]
            selected_model = None
            
            for preferred in preferred_models:
                for available in models:
                    if preferred in available.lower():
                        selected_model = available
                        break
                if selected_model:
                    break
            
            if not selected_model:
                # Sort models by size (prefer smaller ones)
                models_with_size = []
                for model in models:
                    try:
                        response = requests.get(f"http://localhost:11434/api/show", 
                                               json={"name": model}, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            size = data.get("size", float('inf'))
                            models_with_size.append((model, size))
                    except:
                        models_with_size.append((model, float('inf')))
                
                # Sort by size and use the smallest
                if models_with_size:
                    models_with_size.sort(key=lambda x: x[1])
                    selected_model = models_with_size[0][0]
                else:
                    selected_model = models[0]  # Fallback
            
            self.logger.info(f"Using model: {selected_model}")
            ai_response = self.ollama.generate_response(prompt, selected_model)
            
            if ai_response is None:
                return {
                    "success": False,
                    "error": "AI模型无法生成响应"
                }
            
            return {
                "success": True,
                "user_query": user_query,
                "ai_response": ai_response,
                "table_count": table_data["row_count"],
                "raw_table_data": table_data["data"],
                "model_used": selected_model
            }
            
        except Exception as e:
            self.logger.error(f"AI query processing failed: {e}")
            return {
                "success": False,
                "error": f"处理查询时出错: {str(e)}"
            }


def show_table_list():
    """Show all tables in the database."""
    manager = AITableQueryManager()
    
    default_query = "数据库中有哪些表？请按schema分组显示所有非系统表。"
    
    print(f"执行查询: {default_query}")
    print("-" * 60)
    
    result = manager.query_with_ai(default_query)
    
    if result["success"]:
        print("✅ 查询成功完成")
        print(f"📊 找到 {result['table_count']} 个表")
        print(f"🤖 使用模型: {result['model_used']}")
        print()
        print("🎯 AI 回答:")
        print("-" * 40)
        print(result["ai_response"])
        print()
        print("📋 原始表数据:")
        print("-" * 40)
        for table in result["raw_table_data"]:
            print(f"  {table['schemaname']}.{table['tablename']}")
        return result["raw_table_data"]
    else:
        print("❌ 查询失败")
        print(f"错误: {result['error']}")
        return []

def query_table_data():
    """Query specific table data with AI assistance."""
    manager = AITableQueryManager()
    
    print("\n" + "=" * 60)
    print("📊 表数据查询")
    print("-" * 60)
    
    # Get user input
    table_input = input("请输入表名 (格式: schema.table 或 table): ").strip()
    if not table_input:
        print("❌ 表名不能为空")
        return
    
    # Parse schema and table name
    if "." in table_input:
        schema, table_name = table_input.split(".", 1)
    else:
        schema = None
        table_name = table_input
    
    # Get WHERE condition (optional)
    where_condition = input("请输入WHERE条件 (可选，直接回车跳过): ").strip()
    if not where_condition:
        where_condition = None
    
    # Get limit (optional)
    limit_input = input("请输入查询行数限制 (默认10行): ").strip()
    try:
        limit = int(limit_input) if limit_input else 10
    except ValueError:
        limit = 10
    
    print(f"\n🔍 查询表: {table_input}")
    if where_condition:
        print(f"📝 WHERE条件: {where_condition}")
    print(f"📊 限制行数: {limit}")
    print("-" * 40)
    
    # Execute the query
    result = manager.query_table_with_ai(table_name, schema, where_condition, limit)
    
    if result["success"]:
        print("✅ 查询成功完成")
        print(f"📊 找到 {result['row_count']} 行数据")
        print(f"🤖 使用模型: {result['model_used']}")
        print()
        print("🎯 AI 分析:")
        print("-" * 40)
        print(result["ai_response"])
        print()
        print("📋 原始数据:")
        print("-" * 40)
        for i, row in enumerate(result["table_data"], 1):
            row_str = ", ".join([f"{k}={v}" for k, v in row.items()])
            print(f"  行{i}: {row_str}")
    else:
        print("❌ 查询失败")
        print(f"错误: {result['error']}")

def main():
    """Main function to run the AI table query."""
    print("=== AI 数据库表查询工具 ===")
    print("Author: Vance Chen")
    print()
    
    while True:
        print("\n请选择操作:")
        print("1. 查看所有表")
        print("2. 查询表数据")
        print("3. 退出")
        
        choice = input("\n请输入选择 (1-3): ").strip()
        
        if choice == "1":
            show_table_list()
        elif choice == "2":
            query_table_data()
        elif choice == "3":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请输入 1-3")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main() 