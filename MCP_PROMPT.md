# 🍅 四象限 MCP 服务器创建提示词

## 📝 项目概述

请创建一个完整的MCP（Model Context Protocol）服务器，用于为四象限Android时间管理应用提供AI功能接口。这个MCP服务器采用桥接架构，运行在PC端，通过HTTP API与Android设备通信。

## 🏗️ 系统架构

```
MCP客户端(Cursor) ←→ MCP服务器(Python) ←→ Android HTTP服务器 ←→ Android AI功能模块
```

### 架构说明
- **MCP服务器**: 运行在PC端，使用Python实现，符合MCP协议标准
- **Android桥接**: Android设备运行简单的HTTP服务器，接收MCP服务器的API调用
- **通信方式**: PC和Android通过WiFi网络进行HTTP JSON通信

## 🎯 核心功能要求

### 1. 番茄钟管理功能
- `start_pomodoro`: 启动番茄钟计时器
  - 参数: task_name(必需), duration(可选,默认25分钟), task_id(可选)
  - 功能: 开始专注工作时间，支持自定义时长和任务关联
- `control_pomodoro`: 控制番茄钟状态
  - 参数: action(pause|resume|stop|status), reason(可选)
  - 功能: 暂停、恢复、停止、查询番茄钟状态
- `manage_break`: 管理休息时间
  - 参数: action(start|skip)
  - 功能: 开始休息或跳过休息时间

### 2. 任务管理功能
- `manage_tasks`: 四象限任务CRUD操作
  - 参数: action(create|update|delete|list|complete), task_data, task_id
  - 功能: 基于重要性(1-4)和紧急性(1-4)的四象限任务分类管理
  - 任务数据包括: name, description, importance, urgency, due_date, status

### 3. 统计分析功能
- `get_statistics`: 获取统计数据和分析报告
  - 参数: type(general|daily|weekly|monthly|pomodoro|tasks), period, filters
  - 功能: 多维度统计，包括番茄钟统计、任务分布统计等

### 4. 设置管理功能
- `update_settings`: 更新系统设置
  - 参数: dark_mode, tomato_duration, break_duration, notification_enabled, auto_start_break, sound_enabled
  - 功能: 界面设置、番茄钟配置、通知设置等

### 5. 系统监控功能
- `check_android_status`: 检查Android应用连接状态
  - 功能: 实时监控Android设备连接状态和功能可用性

## 💻 技术实现要求

### Python MCP服务器
```python
# 主要依赖
- mcp>=1.0.0
- aiohttp>=3.9.0
- pydantic>=2.5.0
- asyncio

# 核心类结构
- AndroidBridge: 负责与Android设备HTTP通信
- 各种Args数据模型: 使用Pydantic进行参数验证
- MCP工具处理函数: 每个功能对应一个异步处理函数
```

### Android HTTP服务器
```java
// 文件位置建议: com.example.fourquadrant.server.AndroidHttpServer
// 主要功能:
- HTTP服务器监听8080端口
- 处理/api/command/execute端点(POST)
- 处理/api/status端点(GET)  
- 处理/api/health端点(GET)
- CORS支持和错误处理
- 调用CommandRouter执行具体AI功能
```

### 配置要求
```json
// config.json配置文件
{
  "android_config": {
    "host": "192.168.1.100",  // Android设备IP，需要可配置
    "port": 8080,
    "timeout": 10
  },
  "features": {
    "pomodoro": {"enabled": true, "default_duration": 25},
    "tasks": {"enabled": true, "max_importance": 4},
    "statistics": {"enabled": true},
    "settings": {"enabled": true}
  }
}
```

## 📱 Android集成指南

### 1. 权限配置
```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
```

### 2. 网络安全配置
```xml
<!-- network_security_config.xml -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">192.168.1.0/24</domain>
        <domain includeSubdomains="true">10.0.0.0/8</domain>
    </domain-config>
</network-security-config>
```

### 3. MainActivity集成
```java
// 在MainActivity中启动HTTP服务器
private AndroidHttpServer httpServer;

private void startMcpServer() {
    httpServer = new AndroidHttpServer(this);
    new Thread(() -> {
        try {
            httpServer.startServer(8080);
            // 显示启动成功提示
        } catch (IOException e) {
            // 处理启动失败
        }
    }).start();
}
```

## 🛠️ 文件结构要求

```
fourquadrant-mcp/
├── README.md                          # 项目说明
├── INSTALL.md                         # 安装指南
├── fourquadrant-mcp-server.py        # MCP服务器主程序
├── requirements.txt                   # Python依赖
├── config.json                        # 配置文件
├── test_mcp_server.py                # 测试脚本
├── start_server.bat                  # Windows启动脚本
├── start_server.sh                   # Linux/Mac启动脚本
└── android/
    └── AndroidHttpServer.java        # Android HTTP服务器
```

## 🔧 MCP协议实现细节

### 工具定义规范
```python
# 每个工具需要包含:
- name: 工具名称（英文，下划线分隔）
- description: 中文描述，说明功能用途
- inputSchema: JSON Schema格式的参数定义
  - type: "object"
  - properties: 参数详细定义
  - required: 必需参数列表
```

### 响应格式规范
```python
# 成功响应格式:
CallToolResult(
    content=[
        TextContent(
            type="text",
            text="🍅 操作成功！\n\n详细信息...\n📱 Android响应: ..."
        )
    ]
)

# 错误响应格式:
CallToolResult(
    content=[
        TextContent(
            type="text", 
            text="❌ 操作失败: 错误详情"
        )
    ]
)
```

### 与Android通信协议
```json
// 发送到Android的请求格式:
{
  "command": "start_pomodoro",
  "args": {
    "task_name": "学习MCP协议",
    "duration": 25
  }
}

// Android返回的响应格式:
{
  "success": true,
  "message": "功能执行成功",
  "timestamp": 1673856000000,
  "command": "start_pomodoro",
  "data": {} // 可选的额外数据
}
```

## 🎨 用户体验要求

### 响应信息格式
- 使用emoji图标增强可读性
- 提供中文友好的反馈信息
- 包含操作时间戳
- 显示Android端的响应状态
- 对四象限任务自动显示所属象限

### 错误处理
- 详细的错误信息和解决建议
- 网络连接问题的诊断提示
- Android设备状态检查功能
- 超时和重试机制

## 🧪 测试要求

### 测试脚本功能
```python
# test_mcp_server.py应包含:
- Android连接测试
- 状态查询测试  
- 核心命令执行测试
- 错误情况处理测试
- 网络诊断功能
```

### 启动脚本功能
```bash
# 启动脚本应包含:
- Python环境检查
- 依赖安装检查
- 配置文件验证
- 自动启动服务器
- 错误提示和帮助信息
```

## 📚 文档要求

### README.md
- 项目概述和功能介绍
- 快速开始指南
- 文件结构说明
- 基本配置方法

### INSTALL.md  
- 详细的安装步骤
- Android集成指南
- 故障排除指南
- 网络配置说明

### API文档
- 每个MCP工具的详细说明
- 参数格式和示例
- 响应格式说明
- 使用场景说明

## 🔐 安全考虑

- HTTP通信限制在局域网内
- 支持CORS配置
- 输入参数验证
- 错误信息不泄露敏感信息
- 连接超时和重试限制

## 🎯 特色功能

### 四象限智能分类
- 基于重要性和紧急性自动判断任务象限
- 在任务创建/更新时显示象限信息
- 提供象限过滤和统计功能

### 实时状态监控
- Android设备连接状态实时检查
- 功能模块启用状态监控
- 番茄钟运行状态同步

### 智能响应格式
- 根据操作类型自动格式化响应
- 提供操作建议和下一步指引
- 时间格式化和用户友好显示

---

## 💡 实现提示

请按照以上要求创建一个完整的MCP服务器项目，确保：

1. **代码质量**: 使用类型注解、异常处理、日志记录
2. **用户体验**: 友好的中文界面、清晰的错误提示
3. **可维护性**: 模块化设计、配置驱动、完善文档
4. **可扩展性**: 支持新功能添加、配置灵活
5. **稳定性**: 网络重连、错误恢复、状态同步

这个MCP服务器将作为四象限Android应用的AI功能桥梁，为用户提供便捷的时间管理和任务管理服务。
