# 📝 四象限 MCP 服务器代码模板提示词

## 🐍 Python MCP服务器模板

### 主要导入和配置
```python
#!/usr/bin/env python3
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, Tool, TextContent
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("fourquadrant-mcp")

# Android设备配置
ANDROID_CONFIG = {
    "host": "192.168.1.100",  # 需要修改为实际IP
    "port": 8080,
    "timeout": 10
}
```

### AndroidBridge通信类
```python
class AndroidBridge:
    def __init__(self, host: str = None, port: int = None):
        self.host = host or ANDROID_CONFIG["host"]
        self.port = port or ANDROID_CONFIG["port"]
        self.base_url = f"http://{self.host}:{self.port}"
        self.timeout = ANDROID_CONFIG["timeout"]
        
    async def call_android_api(self, endpoint: str, method: str = "POST", data: Dict = None):
        async with aiohttp.ClientSession() as session:
            try:
                if method == "GET":
                    async with session.get(url, params=data, timeout=self.timeout) as response:
                        result = await response.json()
                else:
                    async with session.request(method, url, json=data, timeout=self.timeout) as response:
                        result = await response.json()
                logger.info(f"Android API调用成功: {method} {endpoint}")
                return result
            except Exception as e:
                logger.error(f"Android API调用失败: {str(e)}")
                raise Exception(f"Android应用通信失败: {str(e)}")

android_bridge = AndroidBridge()
```

### 数据模型定义
```python
# 番茄钟参数
class PomodoroArgs(BaseModel):
    task_name: str = Field(..., description="关联的任务名称")
    duration: Optional[int] = Field(25, description="持续时间（分钟）")
    task_id: Optional[str] = Field(None, description="任务ID")

# 控制参数
class ControlArgs(BaseModel):
    action: str = Field(..., description="控制操作类型：pause|resume|stop|status")
    reason: Optional[str] = Field(None, description="操作原因")

# 任务数据
class TaskData(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[int] = Field(None, ge=1, le=4)
    urgency: Optional[int] = Field(None, ge=1, le=4)
    due_date: Optional[str] = None
    status: Optional[str] = None

class TaskArgs(BaseModel):
    action: str = Field(..., description="任务操作类型：create|update|delete|list|complete")
    task_data: Optional[TaskData] = None
    task_id: Optional[str] = None
```

### 工具列表定义
```python
@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="start_pomodoro",
                description="启动番茄钟计时器，开始专注工作时间",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_name": {"type": "string", "description": "关联的任务名称"},
                        "duration": {"type": "number", "description": "持续时间（分钟）", "minimum": 1, "maximum": 120, "default": 25},
                        "task_id": {"type": "string", "description": "任务ID（可选）"}
                    },
                    "required": ["task_name"]
                }
            ),
            # ... 其他工具定义
        ]
    )
```

### 工具处理函数模板
```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        logger.info(f"处理工具调用: {name}")
        
        if name == "start_pomodoro":
            return await start_pomodoro_tool(arguments)
        # ... 其他工具路由
        else:
            raise ValueError(f"未知的工具: {name}")
            
    except Exception as e:
        logger.error(f"工具调用失败 {name}: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ 工具调用失败: {str(e)}")]
        )

async def start_pomodoro_tool(arguments: dict) -> CallToolResult:
    try:
        args = PomodoroArgs(**arguments)
        
        android_data = {
            "command": "start_pomodoro",
            "args": {
                "task_name": args.task_name,
                "duration": args.duration,
                "task_id": args.task_id
            }
        }
        
        result = await android_bridge.call_android_api("/api/command/execute", "POST", android_data)
        
        response_text = f"""🍅 番茄钟启动成功！
        
📝 任务名称: {args.task_name}
⏰ 时长: {args.duration} 分钟
📱 Android响应: {result.get('message', '执行成功')}
🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

专注工作，保持高效！"""

        return CallToolResult(
            content=[TextContent(type="text", text=response_text)]
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ 启动番茄钟失败: {str(e)}")]
        )
```

### 主函数
```python
async def main():
    logger.info("🍅 四象限 MCP 服务器启动中...")
    logger.info(f"📱 Android设备配置: {ANDROID_CONFIG['host']}:{ANDROID_CONFIG['port']}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fourquadrant-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {str(e)}")
```

## ☕ Android HTTP服务器模板

### 主类结构
```java
package com.example.fourquadrant.server;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;
import android.content.Context;
import android.util.Log;
import org.json.JSONObject;

public class AndroidHttpServer {
    private static final String TAG = "AndroidHttpServer";
    private HttpServer server;
    private Context context;
    private boolean isRunning = false;
    
    public AndroidHttpServer(Context context) {
        this.context = context;
    }
    
    public void startServer(int port) throws IOException {
        server = HttpServer.create(new InetSocketAddress(port), 0);
        
        // 注册API端点
        server.createContext("/api/command/execute", new CommandExecuteHandler());
        server.createContext("/api/status", new StatusHandler());
        server.createContext("/api/health", new HealthHandler());
        
        server.start();
        isRunning = true;
        Log.i(TAG, "HTTP服务器已启动，端口：" + port);
    }
}
```

### 命令处理器
```java
class CommandExecuteHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
        // 设置CORS头
        exchange.getResponseHeaders().add("Access-Control-Allow-Origin", "*");
        
        if (!"POST".equals(exchange.getRequestMethod())) {
            sendErrorResponse(exchange, 405, "Method Not Allowed");
            return;
        }
        
        try {
            String requestBody = readRequestBody(exchange);
            JSONObject request = new JSONObject(requestBody);
            String command = request.getString("command");
            JSONObject args = request.optJSONObject("args");
            
            // 调用CommandRouter执行命令
            // CommandRouter.ExecutionResult result = CommandRouter.executeCommand(command, argsMap);
            
            JSONObject response = new JSONObject();
            response.put("success", true);
            response.put("message", "功能执行成功");
            response.put("timestamp", System.currentTimeMillis());
            
            sendJsonResponse(exchange, 200, response.toString());
            
        } catch (Exception e) {
            sendErrorResponse(exchange, 500, "Internal server error: " + e.getMessage());
        }
    }
}
```

## 📋 requirements.txt
```
mcp>=1.0.0
aiohttp>=3.9.0
pydantic>=2.5.0
asyncio
typing-extensions>=4.0.0
```

## 🎯 使用说明

1. **复制上述模板代码**创建主要文件
2. **修改ANDROID_CONFIG**中的IP地址
3. **实现所有7个工具函数**
4. **完善Android端HTTP服务器**
5. **添加测试和启动脚本**

这些模板提供了完整的结构框架，只需要根据具体需求填充实现细节即可。
