# 🚀 四象限 MCP 服务器快速创建提示词

## 一句话需求
创建一个MCP服务器，为四象限Android时间管理应用提供AI功能接口，包含番茄钟管理、任务管理、统计分析等7个核心工具。

## 🏗️ 架构 
PC端Python MCP服务器 ←→ Android设备HTTP服务器 ←→ Android AI功能

## 📦 依赖包
```
mcp>=1.0.0
aiohttp>=3.9.0  
pydantic>=2.5.0
```

## 🛠️ 核心工具列表
1. `start_pomodoro` - 启动番茄钟(task_name*, duration=25, task_id)
2. `control_pomodoro` - 控制番茄钟(action*, reason) [pause|resume|stop|status]
3. `manage_break` - 管理休息(action*) [start|skip]
4. `manage_tasks` - 任务管理(action*, task_data, task_id) [create|update|delete|list|complete]
5. `get_statistics` - 获取统计(type*, period, filters) [general|daily|weekly|monthly|pomodoro|tasks]
6. `update_settings` - 更新设置(dark_mode, tomato_duration, break_duration, notification_enabled, auto_start_break, sound_enabled)
7. `check_android_status` - 检查Android状态()

## 💾 配置文件
```json
{
  "android_config": {
    "host": "192.168.1.100",
    "port": 8080,
    "timeout": 10
  }
}
```

## 📱 Android通信协议
```json
// 请求格式
{
  "command": "start_pomodoro",
  "args": {"task_name": "学习", "duration": 25}
}

// 响应格式  
{
  "success": true,
  "message": "执行成功",
  "timestamp": 1673856000000,
  "data": {}
}
```

## 🎨 响应格式要求
- 使用emoji和中文友好提示
- 包含Android响应状态
- 显示操作时间戳
- 四象限任务自动显示象限分类

## 📁 文件结构
```
项目名/
├── mcp_server.py          # 主程序
├── requirements.txt       # 依赖
├── config.json           # 配置
├── test_server.py        # 测试
├── start.bat/.sh         # 启动脚本
└── android/
    └── HttpServer.java   # Android服务器
```

## 💡 关键实现点
- AndroidBridge类处理HTTP通信
- Pydantic数据模型验证参数
- 异步处理所有网络请求
- 完善的错误处理和日志
- 支持CORS的Android HTTP服务器
- 四象限智能分类(重要性1-4 × 紧急性1-4)

## 🧪 测试要求
创建测试脚本验证Android连接、状态查询、命令执行功能

---
**目标**: 创建一个可直接运行的、功能完整的MCP服务器，让用户通过Cursor与四象限Android应用进行AI交互。
