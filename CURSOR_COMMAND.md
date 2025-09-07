# 🎯 Cursor一键生成命令

## 📋 完整创建指令

```
请根据以下要求创建一个完整的四象限MCP服务器项目：

## 项目结构
创建以下文件夹和文件：
- fourquadrant-mcp/
  - mcp_server.py (主程序)
  - requirements.txt (依赖)
  - config.json (配置)
  - test_server.py (测试)
  - start_server.bat (Windows启动)
  - start_server.sh (Linux启动)
  - README.md (说明)
  - android/AndroidHttpServer.java (Android服务器)

## 技术要求
- Python 3.8+，使用mcp、aiohttp、pydantic库
- 实现7个MCP工具：start_pomodoro, control_pomodoro, manage_break, manage_tasks, get_statistics, update_settings, check_android_status
- Android HTTP服务器监听8080端口，处理/api/command/execute等端点
- 通过WiFi网络HTTP JSON通信，PC端MCP服务器调用Android设备API

## 核心功能
1. 番茄钟管理：启动(task_name*, duration=25, task_id)、控制(action*)、休息管理(action*)
2. 任务管理：CRUD操作，四象限分类(重要性1-4×紧急性1-4)
3. 统计分析：多维度数据统计和报告
4. 设置管理：界面、通知、时长配置
5. 状态监控：Android连接和功能状态检查

## 实现细节
- AndroidBridge类处理HTTP通信，配置host="192.168.1.100"
- Pydantic模型验证所有输入参数
- 友好的中文响应，使用emoji和时间戳
- 完善错误处理和日志记录
- Android端支持CORS，调用CommandRouter执行功能

## 通信协议
请求格式：{"command": "start_pomodoro", "args": {"task_name": "学习"}}
响应格式：{"success": true, "message": "执行成功", "timestamp": 123456789}

请创建所有文件，确保代码完整可运行，包含详细注释和使用说明。
```

## 🚀 快速执行版本

```
创建四象限MCP服务器：
- Python MCP服务器连接Android设备，提供7个AI工具
- start_pomodoro启动番茄钟，manage_tasks管理四象限任务，get_statistics获取统计数据等
- 通过HTTP JSON与Android通信，IP配置192.168.1.100:8080
- 包含完整的Android HttpServer、测试脚本、启动脚本
- 使用mcp+aiohttp+pydantic，友好的中文界面和错误处理
```

## 🎯 分步骤指令

### 第1步：创建基础结构
```
创建fourquadrant-mcp项目文件夹，包含：
- mcp_server.py：Python MCP服务器主程序
- requirements.txt：mcp>=1.0.0, aiohttp>=3.9.0, pydantic>=2.5.0
- config.json：Android设备IP配置
```

### 第2步：实现MCP工具
```
在mcp_server.py中实现7个MCP工具：
1. start_pomodoro(task_name*, duration=25, task_id)
2. control_pomodoro(action*, reason) - pause/resume/stop/status
3. manage_break(action*) - start/skip
4. manage_tasks(action*, task_data, task_id) - create/update/delete/list/complete
5. get_statistics(type*, period, filters) - general/daily/weekly/monthly/pomodoro/tasks
6. update_settings(dark_mode, tomato_duration, break_duration, notification_enabled)
7. check_android_status() - 检查Android连接状态

使用AndroidBridge类通过HTTP调用Android API，返回友好的中文响应。
```

### 第3步：创建Android服务器
```
创建android/AndroidHttpServer.java：
- HTTP服务器监听8080端口
- 处理POST /api/command/execute端点
- 支持CORS，解析JSON请求
- 调用CommandRouter.executeCommand执行功能
- 返回标准JSON响应格式
```

### 第4步：添加测试和启动脚本
```
创建：
- test_server.py：测试Android连接和命令执行
- start_server.bat：Windows启动脚本
- start_server.sh：Linux启动脚本  
- README.md：项目说明和使用指南
```

## 💡 关键提示

- **IP配置**：ANDROID_CONFIG = {"host": "192.168.1.100", "port": 8080}
- **响应格式**：使用emoji、中文描述、时间戳，例如"🍅 番茄钟启动成功！"
- **错误处理**：网络超时、连接失败、参数验证等
- **四象限分类**：重要性×紧急性自动判断象限（1-4级别）
- **Android集成**：需要网络权限、CORS配置、CommandRouter调用

使用任意一个指令都可以让Cursor理解并创建完整的四象限MCP服务器项目。
