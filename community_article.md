# 构建 AI 与数据的通用桥梁：基于 MCP 开放协议的 Cloudberry 数据库连接器实践

---

### 引言：AI 时代，我们需要一个“数据 USB-C”

各位开发者朋友，大家好！

在大语言模型（LLM）引领的 AI 新浪潮中，我们正见证着一个新时代的到来。LLM 如同强大的“计算大脑”，但它天生被隔离在自己的世界里。要释放其全部潜能，我们必须解决一个核心问题：**如何让这个“大脑”安全、高效、标准化地连接到我们庞杂多样的外部数据世界？**

> 我们需要的，不仅仅是临时的、定制化的数据管道，而是一个像 **USB-C** 那样通用的、标准化的连接协议。

今天，我将向大家介绍一个旨在成为“AI 的 USB-C”的开放协议——**模型上下文协议（Model Context Protocol, MCP）**，并分享我们基于该协议为 Cloudberry 数据库构建的一个开源连接器实践：**Cloudberry MCP 服务**。本文将带您深入了解 MCP 的设计哲学，以及我们如何通过它，为 LLM 与高性能数据库之间架起一座坚实、通用的桥梁。

---

### 解构 MCP：为 AI 定义标准的交互原语

根据其官方定义，MCP 是一个开放协议，它标准化了应用程序向 LLM 提供上下文的方式。它的核心使命是 **“连接，而非限制”**。

想象一下，如果没有 USB-C 标准，每台设备都需要一个特制的充电器。这正是当前许多 AI 应用的现状——为每个特定的数据源和 LLM 组合开发一套专用的“连接器”。MCP 的出现，正是为了终结这种混乱，它借鉴了语言服务器协议（LSP）的成功经验，旨在标准化 AI 应用与外部工具和数据的集成方式。

MCP 并非一个模糊的概念，它是一个基于 **JSON-RPC 2.0** 的严谨协议，通过三个清晰、可扩展的核心“原语”（Primitives），构建了一个强大的框架：

| 原语 (Primitive) | 控制方 (Control) | 描述 | 我们的项目中的例子 |
| :--- | :--- | :--- | :--- |
| **工具 (Tools)** | 模型控制 (Model-controlled) | 定义了 LLM 可以自主调用以执行具体操作的功能。 | `run_readonly_sql`：执行一条安全的、只读的 SQL 查询。 |
| **资源 (Resources)** | 应用控制 (Application-controlled) | 定义了客户端可以读取以获取上下文信息的数据。 | `table_schema_public_store_sales`：获取 store_sales 表的结构定义。 |
| **提示 (Prompts)** | 用户控制 (User-controlled) | 定义了可由用户显式触发的、可复用的模板化工作流。 | `show_top_10_products`：一个预设的、用于查询十大畅销商品的快捷指令。 |

通过这套标准，任何兼容 MCP 的客户端（如 AI Agent 或 Claude Desktop）都可以通过标准化的请求（如 `tools/list`）来发现服务的能力，并利用其提供的工具和资源来完成复杂任务。

---

### Cloudberry MCP 服务：一个高质量的“数据库连接器”

我们的开源项目，正是 MCP 生态中的一个具体实现。您可以把它看作一个专门为 Cloudberry 数据库量身定制的、高质量的 **MCP 服务器（MCP Server）**。

它的价值在于，任何遵循 MCP 协议的 AI 应用，都可以通过我们的服务，即时获得与 Cloudberry 数据库“对话”的能力，而无需关心底层的数据库方言、驱动或安全细节。

我们的服务基于 FastAPI 构建，其架构严格遵循 MCP 的理念，并在此基础上增加了企业级的健壮性。

#### **架构核心：忠实于协议的实现**

项目的核心在于精确地实现了 MCP 协议的关键方法，而非自定义 RESTful 端点。

*   **动态能力发现**：当客户端发起 `tools/list` 和 `resources/list` 请求时，我们的服务会：
    *   动态扫描数据库，将所有可用的表和视图自动注册为 MCP 资源。
    *   返回预定义的工具列表（如 `run_readonly_sql`）。
    *   这意味着，当数据库中新增或删除表时，服务无需任何代码改动，就能在下一次 `resources/list` 调用时将最新的数据蓝图提供给 LLM。

*   **工具与资源的调用处理**：我们为 `tools/call` 和 `resources/read` 请求实现了对应的处理器（Handler）。

```python
# 代码经过优化和简化，以贴合 mcp-sdk 的风格
from mcp.server.fastmcp import FastMCP
from . import db_ops # 我们的数据库操作模块

# 初始化 FastMCP 服务器
mcp = FastMCP("cloudberry-connector")

# 使用装饰器，清晰地将一个函数定义为 MCP 工具
@mcp.tool()
async def run_readonly_sql(sql_query: str) -> str:
    """
    Executes a read-only SQL query against the Cloudberry database.
    Args:
        sql_query: The SQL query string to be executed.
    """
    # 1. 安全检查（内部实现，对AI透明）
    if not db_ops.is_safe_query(sql_query):
        raise ValueError("Query is not safe. Only SELECT statements are allowed.")

    # 2. 执行查询并返回结果
    result = await db_ops.execute_query(sql_query)
    return result["data_as_json"]

# McpServer 内部会处理 list_tools, call_tool 等请求
# 我们只需定义好工具即可
```

#### **“桥梁”的基石：安全与性能**

虽然 MCP 的核心是连接，但一座可靠的桥梁必须保证安全与通行效率。我们在 `src/database/operations.py` 中为此构建了坚实的“桥墩”。

*   **安全即服务**：我们将复杂的数据库安全策略（如只读白名单、危险模式检测、防多语句注入等）封装在业务逻辑层。对于 MCP 的使用者（LLM）而言，它只需知道调用 `run_readonly_sql` 工本质上是安全的。这种设计将安全作为一种内建属性，而非外挂的补丁。

*   **性能优化**：通过异步处理和数据库连接池，我们确保了即使在高并发的 AI 请求下，这座“桥梁”也能保持高效畅通。

---

### 工作流：MCP 如何赋能一次智能数据查询

让我们想象一个 AI Agent 需要完成“查询2022年所有线上销售记录”的任务。

1.  **发现与理解**：Agent 首先向 Cloudberry MCP 服务发起 `tools/list` 和 `resources/list` 请求。通过阅读返回的结果，它知道了：
    *   有一个名为 `run_readonly_sql` 的工具可以用来查询数据。
    *   资源列表里有很多表资源，其中一个 URI `db://tpcds/public/web_sales` 看起来和“线上销售”相关。

2.  **上下文学习**：Agent 发起 `resources/read` 请求，参数为 `uri: "db://tpcds/public/web_sales"`。它获取到了 `web_sales` 表的详细结构（列名、数据类型等）。

3.  **构建与执行**：基于获取到的表结构，Agent 构建出一条精确的 SQL 查询语句。然后，它调用 `tools/call`，将工具名称 `run_readonly_sql` 和 SQL 查询作为参数提交。

4.  **获得结果**：我们的 MCP 服务在内部完成安全检查和数据库查询后，将结果以标准化的 JSON 格式返回给 Agent。

> 在这个过程中，Agent 无需任何关于 Cloudberry 的“先验知识”。它完全依赖 MCP 这套标准化的交互方式，就成功地与一个全新的数据源完成了交互。

---

### 展望未来：从“连接器”到“智能数据副驾”

我们当前构建的 Cloudberry MCP 服务，仅仅是这座“AI-数据”通用桥梁的 1.0 版本。它坚实地解决了“连接”的问题，但真正的未来在于让这座桥梁变得更加“智能”。我们的愿景，是将其从一个被动的“连接器”，升级为一个主动的、能够深度理解业务的“智能数据副驾”。

我们的演进方向将聚焦于以下激动人心的领域：

#### **1. 拓展工具集：从“查询”到“洞察与管理”**

LLM 的能力远不止于生成 `SELECT` 语句。我们将通过提供更丰富的 MCP 工具，将更多 CloudberryDB 的强大能力开放给 AI：

*   **性能诊断工具**：提供如 `explain_sql_query`（分析查询计划）、`get_active_queries`（获取活动查询）等工具，让 AI 能够帮助开发者和 DBA 分析并优化慢查询，诊断系统负载。
*   **深度元数据工具**：提供 `get_ddl_for_table`（获取表结构定义语句）等工具，让 AI 能更完整地理解数据库对象。

#### **2. 引入语义层：让 AI 真正“理解”你的业务**

这正是我们规划的核心亮点：**通过 MCP Resource 原语引入语义层**。

当前 Text-to-SQL 的核心困境在于，LLM 或许能写出语法正确的 SQL，但由于缺乏业务上下文，它常常无法写出业务逻辑正确的 SQL。比如，它不知道 `ws_ext_sales_price` 字段的业务含义是“最终销售额”，也不知道应该和哪个日期维度表关联。

我们的解决方案是，极大地丰富 `resources/read` 请求返回的内容。当 LLM 请求一个表资源时，它获取到的不再是干巴巴的列名和数据类型，而是一个包含了丰富业务知识的“数据说明书”：

*   **业务定义**：为每个字段提供清晰的业务解释（例如：`ws_sold_date_sk` -> “销售发生的日期维度外键，关联到date_dim表的d_date_sk”）。
*   **指标关联**：明确指出关键指标的计算逻辑（例如：“计算‘净销售额’时，应使用 `ws_net_paid_inc_tax` 字段”）。
*   **向量嵌入（Vector Embeddings）**：为每个字段的业务描述生成向量嵌入。这使得 AI 可以通过向量相似度搜索，根据自然语言的“意图”找到最相关的字段，而不仅仅是关键词匹配。

> 通过让 LLM 在生成 SQL 之前先“学习”这个富含语义的资源，它将不再是进行机械的文本到代码的翻译，而是**真正基于业务理解来进行逻辑推理**。这将是解决 Text-to-SQL 生产可用性问题的关键一步，让 AI 与数据的协作迈向一个全新的、高度准确可靠的阶段。

通过以上演进，Cloudberry MCP 服务将不仅仅是一座桥梁，它将成为一个嵌入了数据专家知识的、不知疲倦的智能数据副驾，赋能每一位用户，让他们都能安全、高效、精准地从海量数据中挖掘价值。

---

### 结论：加入这场构建连接的运动

MCP 协议为我们描绘了一个激动人心的未来：一个开放、互联的 AI 生态系统，在这里，数据和工具可以像即插即用的设备一样，轻松地接入任何 AI 应用。

我们的 **Cloudberry MCP 服务**项目，正是朝着这个未来迈出的一小步。它为广大的 Cloudberry 用户和 AI 开发者提供了一个开箱即用的高质量“连接器”。我们已将项目开源，并希望以此为起点，邀请社区的朋友们一同参与到这场“构建连接”的运动中来。

无论是为更多的数据库开发 MCP 连接器，还是在您的 AI 应用中集成 MCP 客户端，每一个贡献都将加速 AI 与数据融合的进程。

欢迎访问我们的项目，期待与您共同建设这个开放的生态！
