# HTTP MCP Server - 重构版本

## 📋 项目概述

这是 HTTP MCP Server 的重构版本，采用模块化设计，代码结构更清晰，更易于维护和扩展。

## 🏗️ 项目结构

```
simple-mcp-server/
├── 📁 核心模块
│   ├── models.py                    # 数据模型定义
│   ├── config.py                    # 配置管理
│   ├── tools.py                     # 工具处理器
│   ├── websocket_manager.py         # WebSocket连接管理
│   ├── langchain_handler_new.py     # LangChain处理器（重构版）
│   └── http_mcp_server_new.py       # 主服务器（重构版）
│
├── 📁 配置文件
│   └── config.json                  # 服务器配置
│
├── 📁 原始文件（向后兼容）
│   ├── http_mcp_server.py           # 原始服务器
│   ├── langchain_handler.py         # 原始LangChain处理器
│   └── http_mcp_client.py           # HTTP客户端
│
├── 📁 前端界面
│   ├── chat_interface.html          # 聊天界面
│   └── chat_interface.js            # 前端脚本
│
└── 📁 依赖文件
    ├── http_requirements.txt        # HTTP服务依赖
    └── langchain_requirements.txt   # LangChain依赖
```

## 🔧 核心模块说明

### 1. models.py - 数据模型
- 📦 **功能**: 定义所有数据模型和类型
- 🎯 **职责**: 
  - MCP工具相关模型
  - 聊天请求/响应模型
  - WebSocket消息模型
  - 配置模型
  - 错误处理模型

### 2. config.py - 配置管理
- 📦 **功能**: 统一的配置管理系统
- 🎯 **职责**:
  - 配置文件读取和验证
  - 环境变量处理
  - 默认配置提供
  - 配置热重载

### 3. tools.py - 工具处理器
- 📦 **功能**: MCP工具的实现和管理
- 🎯 **职责**:
  - 工具执行器基类
  - 文件操作工具实现
  - 工具注册和管理
  - 安全性检查

### 4. websocket_manager.py - WebSocket管理
- 📦 **功能**: WebSocket连接的统一管理
- 🎯 **职责**:
  - 连接生命周期管理
  - 消息广播和单播
  - 心跳检测
  - 连接统计

### 5. langchain_handler_new.py - LangChain处理器
- 📦 **功能**: LangChain集成和AI模型调用
- 🎯 **职责**:
  - 模型客户端管理
  - 工具绑定
  - 聊天处理逻辑
  - 错误处理

### 6. http_mcp_server_new.py - 主服务器
- 📦 **功能**: FastAPI服务器主程序
- 🎯 **职责**:
  - 路由定义
  - 中间件配置
  - 生命周期管理
  - 错误处理

## 🚀 快速开始

### 1. 安装依赖
```bash
# 基础HTTP服务依赖
pip install -r http_requirements.txt

# LangChain依赖（聊天功能）
pip install -r langchain_requirements.txt
```

### 2. 配置设置
编辑 `config.json` 文件，或设置环境变量：
```bash
# OpenAI API密钥
export OPENAI_API_KEY="your_openai_key"

# DeepSeek API密钥  
export DEEPSEEK_API_KEY="your_deepseek_key"
```

### 3. 启动服务器
```bash
# 使用重构版本
python http_mcp_server_new.py

# 或使用原版本（向后兼容）
python http_mcp_server.py
```

### 4. 访问服务
- 🌐 **服务器**: http://localhost:8000
- 📚 **API文档**: http://localhost:8000/docs
- 💬 **聊天界面**: http://localhost:8000/static/chat_interface.html
- 🔌 **WebSocket**: ws://localhost:8000/ws

## 📖 API文档

### 基础API
- `GET /` - 服务器信息
- `GET /health` - 健康检查

### 工具API
- `GET /tools` - 列出可用工具
- `POST /tools/call` - 调用工具
- `GET /tools/stats` - 工具统计

### 聊天API
- `POST /chat` - HTTP聊天接口
- `WebSocket /ws` - WebSocket聊天

### 管理API
- `GET /admin/connections` - WebSocket连接信息
- `GET /admin/config` - 当前配置
- `POST /admin/config/reload` - 重载配置

## ⚙️ 配置说明

### 服务器配置
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false,
    "log_level": "INFO",
    "cors_origins": ["*"]
  }
}
```

### 模型配置
```json
{
  "models": {
    "openai": {
      "model_name": "gpt-3.5-turbo",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "deepseek": {
      "model_name": "deepseek-chat",
      "temperature": 0.7,
      "max_tokens": 1000,
      "base_url": "https://api.deepseek.com"
    }
  }
}
```

### 工具配置
```json
{
  "tools": {
    "enabled": ["read_file", "write_file", "list_files"],
    "file_operations": {
      "max_file_size": 10485760,
      "allowed_extensions": [".txt", ".json", ".md"],
      "base_directory": ".",
      "create_directories": true
    }
  }
}
```

## 🔄 从原版本迁移

### 1. 使用重构版本
```python
# 启动重构版服务器
python http_mcp_server_new.py
```

### 2. 配置迁移
重构版本使用 `config.json` 统一配置，原版本的硬编码配置需要迁移到配置文件。

### 3. API兼容性
重构版本保持与原版本的API兼容性，现有客户端代码无需修改。

## 🎯 重构优势

### 1. **模块化设计**
- 单一职责原则
- 低耦合高内聚
- 易于测试和维护

### 2. **配置统一管理**
- 集中配置文件
- 环境变量支持
- 配置验证和热重载

### 3. **更好的错误处理**
- 统一错误模型
- 详细错误信息
- 优雅的错误恢复

### 4. **增强的监控**
- 连接状态监控
- 工具使用统计
- 性能指标收集

### 5. **代码可维护性**
- 清晰的模块边界
- 完善的类型注解
- 详细的文档注释

## 🧪 开发和测试

### 1. 开发模式
```bash
# 启用调试模式
python http_mcp_server_new.py --debug
```

### 2. 测试工具
```python
# 测试工具调用
from tools import execute_tool
result = await execute_tool("read_file", {"file_path": "test.txt"})

# 测试配置
from config import get_config
server_config = get_config("server")
```

### 3. 日志调试
日志文件: `mcp_server.log`
```bash
# 实时查看日志
tail -f mcp_server.log
```

## 🤝 贡献指南

1. **代码风格**: 遵循PEP 8
2. **类型注解**: 使用完整的类型注解
3. **文档**: 添加详细的docstring
4. **测试**: 编写单元测试
5. **日志**: 适当的日志记录

## 📝 更新日志

### v2.0.0 (重构版本)
- ✅ 模块化重构
- ✅ 统一配置管理
- ✅ 增强错误处理
- ✅ WebSocket连接管理
- ✅ 工具统计和监控
- ✅ 向后兼容性

### v1.0.0 (原始版本)
- ✅ 基础HTTP MCP服务器
- ✅ LangChain集成
- ✅ WebSocket支持
- ✅ 文件操作工具

---

🎉 **重构版本提供了更好的代码结构和更强大的功能，同时保持了与原版本的完全兼容！**
