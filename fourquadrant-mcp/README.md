# 🍅 四象限MCP服务器

## 📖 项目简介

四象限MCP服务器是一个基于**Model Context Protocol (MCP)**协议的智能时间管理工具，采用桥接架构设计。它为四象限Android时间管理应用提供AI功能接口，让用户能够通过AI助手进行智能的时间管理和任务规划。

### 🎯 核心特性

- **🤖 AI集成**: 通过MCP协议与AI助手（如Cursor）无缝对接
- **📱 跨平台桥接**: PC端MCP服务器与Android设备HTTP通信
- **🍅 番茄钟管理**: 启动、控制、监控番茄钟计时器
- **📋 四象限任务**: 基于重要性×紧急性的科学任务分类
- **📊 智能统计**: 多维度数据分析和效率报告
- **⚙️ 个性化设置**: 灵活的系统配置和用户偏好
- **🔗 实时连接**: 稳定的网络通信和状态监控

## 🏗️ 系统架构

```
┌─────────────────┐    MCP协议    ┌──────────────────┐    HTTP JSON    ┌─────────────────┐
│   AI助手/Cursor  │ ◄────────────► │   MCP服务器(PC)   │ ◄─────────────► │  Android设备     │
│                 │               │                  │                │                 │
│ • 自然语言交互   │               │ • 7个MCP工具      │                │ • HTTP服务器     │
│ • 智能建议      │               │ • 数据验证       │                │ • 功能执行       │
│ • 任务规划      │               │ • 错误处理       │                │ • 状态管理       │
└─────────────────┘               └──────────────────┘                └─────────────────┘
```

## 🛠️ 技术栈

### PC端 (MCP服务器)
- **Python 3.8+**: 主要开发语言
- **MCP协议**: Model Context Protocol支持
- **aiohttp**: 异步HTTP客户端
- **pydantic**: 数据验证和序列化

### Android端 (HTTP服务器)
- **Java**: Android开发语言
- **JSON**: 数据交换格式
- **HTTP服务器**: 自定义实现，支持CORS

### 通信协议
- **网络**: WiFi局域网
- **协议**: HTTP/JSON
- **端口**: 8080 (可配置)

## 📦 安装指南

### 环境要求

- **PC端**: Python 3.8+, pip
- **Android端**: Android 5.0+ (API 21+)
- **网络**: PC和Android设备需在同一WiFi网络

### 快速安装

1. **克隆项目**
   ```bash
   git clone <项目地址>
   cd fourquadrant-mcp
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置设置**
   
   编辑 `config.json` 文件，设置Android设备IP地址：
   ```json
   {
     "android": {
       "host": "192.168.1.100",  // 修改为你的Android设备IP
       "port": 8080,
       "timeout": 10
     }
   }
   ```

4. **Android端部署**
   
   将 `android/AndroidHttpServer.java` 集成到你的Android应用中，并启动HTTP服务器。

5. **启动服务器**
   
   **Windows:**
   ```cmd
   start_server.bat
   ```
   
   **Linux/macOS:**
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

## 🎮 使用指南

### 1. MCP工具列表

#### 🍅 start_pomodoro - 启动番茄钟
```json
{
  "task_name": "学习Python编程",    // 必需：任务名称
  "duration": 25,                  // 可选：时长(分钟)，默认25
  "task_id": "task_001"           // 可选：关联任务ID
}
```

#### ⏯️ control_pomodoro - 控制番茄钟
```json
{
  "action": "pause",              // 必需：pause/resume/stop/status
  "reason": "临时中断处理邮件"     // 可选：操作原因
}
```

#### ☕ manage_break - 管理休息
```json
{
  "action": "start"               // 必需：start/skip
}
```

#### 📋 manage_tasks - 任务管理
```json
{
  "action": "create",             // 必需：create/update/delete/list/complete
  "task_data": {                  // 创建/更新时必需
    "name": "完成项目文档",
    "description": "编写用户手册和API文档",
    "importance": 4,              // 1-4级
    "urgency": 2,                // 1-4级
    "due_date": "2024-01-15",
    "estimated_pomodoros": 3
  },
  "task_id": "task_123"          // 更新/删除/完成时必需
}
```

#### 📊 get_statistics - 获取统计
```json
{
  "type": "weekly",              // 必需：general/daily/weekly/monthly/pomodoro/tasks
  "period": "2024-01",           // 可选：统计周期
  "filters": {}                  // 可选：过滤条件
}
```

#### ⚙️ update_settings - 更新设置
```json
{
  "dark_mode": true,             // 可选：深色模式
  "tomato_duration": 30,         // 可选：番茄钟时长
  "break_duration": 10,          // 可选：休息时长
  "notification_enabled": true,   // 可选：通知开关
  "auto_start_break": false,     // 可选：自动开始休息
  "sound_enabled": true          // 可选：声音提醒
}
```

#### 📱 check_android_status - 检查状态
```json
{}  // 无需参数
```

### 2. 四象限分类规则

基于任务的**重要性(1-4)**和**紧急性(1-4)**自动分类：

| 象限 | 重要性 | 紧急性 | 特征 | 策略 |
|------|--------|--------|------|------|
| **第一象限** | ≥3 | ≥3 | 重要且紧急 | 立即处理 |
| **第二象限** | ≥3 | <3 | 重要不紧急 | 计划安排 |
| **第三象限** | <3 | ≥3 | 不重要紧急 | 委托处理 |
| **第四象限** | <3 | <3 | 不重要不紧急 | 减少投入 |

### 3. 与AI助手交互示例

**启动番茄钟：**
```
用户: "开始一个25分钟的番茄钟，任务是学习Python"
AI: 调用 start_pomodoro("学习Python", 25)
响应: "🍅 番茄钟启动成功！📝 任务: 学习Python ⏰ 时长: 25分钟"
```

**创建任务：**
```
用户: "创建一个高优先级任务：完成季度报告，预计需要2个番茄钟"
AI: 调用 manage_tasks("create", task_data={...})
响应: "📝 任务创建成功 🎯 分类: 第二象限（重要不紧急）"
```

**查看统计：**
```
用户: "显示本周的工作统计"
AI: 调用 get_statistics("weekly")
响应: "📊 周统计获取成功" + 详细数据
```

## 🧪 测试指南

### 运行自动测试
```bash
python test_server.py
```

### 交互式测试
```bash
python test_server.py interactive
```

### 测试内容
- ✅ Android设备连接测试
- ✅ 所有MCP工具功能测试
- ✅ 网络性能和并发测试
- ✅ 错误处理和异常恢复测试

## 🔧 配置说明

### config.json 详细配置

```json
{
  "android": {
    "host": "192.168.1.100",      // Android设备IP地址
    "port": 8080,                 // HTTP服务器端口
    "timeout": 10,                // 请求超时时间(秒)
    "max_retries": 3,             // 最大重试次数
    "retry_delay": 2              // 重试延迟(秒)
  },
  "server": {
    "name": "fourquadrant-mcp",   // 服务器名称
    "version": "1.0.0",           // 版本号
    "description": "四象限MCP服务器 - 时间管理AI助手"
  },
  "logging": {
    "level": "INFO",              // 日志级别
    "file": "fourquadrant_mcp.log", // 日志文件
    "max_size_mb": 10,            // 日志文件最大大小
    "backup_count": 5             // 备份文件数量
  },
  "features": {
    "auto_retry": true,           // 自动重试
    "debug_mode": false,          // 调试模式
    "enable_statistics": true,    // 启用统计
    "enable_notifications": true  // 启用通知
  }
}
```

### 获取Android设备IP地址

**方法1 - Android设置:**
1. 打开"设置" → "网络和互联网" → "WiFi"
2. 点击已连接的WiFi网络
3. 查看"IP地址"

**方法2 - 开发者选项:**
1. 启用开发者选项
2. 连接adb：`adb shell ip addr show wlan0`

**方法3 - 命令行:**
```bash
# PC端扫描局域网设备
nmap -sn 192.168.1.0/24
```

## 🐛 故障排除

### 常见问题

#### 1. 连接失败
**症状**: `❌ Android设备连接失败`

**解决方案**:
- 检查PC和Android设备是否在同一WiFi网络
- 确认Android设备IP地址配置正确
- 检查Android HTTP服务器是否启动
- 验证防火墙设置（端口8080）

#### 2. 依赖安装失败
**症状**: `pip install` 报错

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 手动安装核心依赖
pip install mcp aiohttp pydantic
```

#### 3. MCP协议错误
**症状**: MCP工具调用失败

**解决方案**:
- 检查MCP客户端配置
- 验证JSON Schema格式
- 查看日志文件详细错误信息

#### 4. Android端集成问题
**症状**: Android HTTP服务器无响应

**解决方案**:
- 添加网络权限: `<uses-permission android:name="android.permission.INTERNET" />`
- 允许HTTP明文传输（Android 9+）
- 检查CommandRouter实现

### 日志分析

日志文件：`fourquadrant_mcp.log`

**关键日志标识**:
- `🔗 调用Android API`: API调用记录
- `✅ Android响应成功`: 成功响应
- `❌ Android服务器响应错误`: 服务器错误
- `⏰ 连接Android设备超时`: 超时错误
- `🌐 网络连接错误`: 网络问题

## 🚀 部署建议

### 开发环境
- 使用虚拟环境隔离依赖
- 启用调试模式获取详细日志
- 配置较短的超时时间快速发现问题

### 生产环境
- 配置适当的超时和重试参数
- 设置日志轮转避免磁盘满
- 监控网络连接状态
- 定期备份配置和日志

### 性能优化
- 调整线程池大小（Android端）
- 配置合适的超时时间
- 启用连接复用
- 监控内存和CPU使用

## 🤝 贡献指南

### 开发规范
- 遵循PEP 8代码规范
- 编写完整的中文注释
- 添加相应的单元测试
- 更新文档和示例

### 提交流程
1. Fork项目仓库
2. 创建功能分支
3. 编写和测试代码
4. 提交Pull Request

### 报告问题
- 使用Issue模板
- 提供详细的复现步骤
- 附上相关日志信息
- 说明环境配置

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)

## 📞 支持与反馈

- **问题报告**: GitHub Issues
- **功能建议**: GitHub Discussions
- **文档问题**: 提交PR修正

---

**🍅 让AI帮助你更好地管理时间，提高工作效率！**
