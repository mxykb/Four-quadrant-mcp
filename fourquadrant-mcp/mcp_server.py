#!/usr/bin/env python3
"""
四象限MCP服务器 - 主程序
为四象限Android时间管理应用提供AI功能接口
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, Tool, TextContent
from pydantic import BaseModel, Field, validator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fourquadrant_mcp.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
server = Server("fourquadrant-mcp")

# 加载配置
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    ANDROID_CONFIG = config.get('android', {
        "host": "192.168.1.100",
        "port": 8080,
        "timeout": 10
    })
except FileNotFoundError:
    logger.warning("config.json 未找到，使用默认配置")
    ANDROID_CONFIG = {
        "host": "192.168.1.100",
        "port": 8080,
        "timeout": 10
    }

# 数据模型定义
class PomodoroAction(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    STATUS = "status"

class BreakAction(str, Enum):
    START = "start"
    SKIP = "skip"

class TaskAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    COMPLETE = "complete"

class StatisticsType(str, Enum):
    GENERAL = "general"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    POMODORO = "pomodoro"
    TASKS = "tasks"

class TaskData(BaseModel):
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    importance: int = Field(..., ge=1, le=4, description="重要性等级(1-4)")
    urgency: int = Field(..., ge=1, le=4, description="紧急性等级(1-4)")
    due_date: Optional[str] = Field(None, description="截止日期")
    status: str = Field(default="pending", description="任务状态")
    estimated_pomodoros: Optional[int] = Field(None, description="预计番茄钟数量")

class AndroidBridge:
    """Android设备通信桥接类"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or ANDROID_CONFIG["host"]
        self.port = port or ANDROID_CONFIG["port"]
        self.base_url = f"http://{self.host}:{self.port}"
        self.timeout = ANDROID_CONFIG["timeout"]
        
    async def call_android_api(self, command: str, args: Dict = None) -> Dict:
        """调用Android API"""
        url = f"{self.base_url}/api/command/execute"
        
        payload = {
            "command": command,
            "args": args or {},
            "timestamp": int(time.time())
        }
        
        logger.info(f"🔗 调用Android API: {command}, 参数: {args}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=payload, 
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Android响应成功: {result.get('message', '')}")
                        return result
                    else:
                        error_msg = f"Android服务器响应错误: HTTP {response.status}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "message": f"❌ {error_msg}",
                            "timestamp": int(time.time())
                        }
                        
        except asyncio.TimeoutError:
            error_msg = f"连接Android设备超时 ({self.timeout}秒)"
            logger.error(error_msg)
            return {
                "success": False,
                "message": f"⏰ {error_msg}",
                "timestamp": int(time.time())
            }
            
        except aiohttp.ClientError as e:
            error_msg = f"网络连接错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": f"🌐 {error_msg}",
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": f"❗ {error_msg}",
                "timestamp": int(time.time())
            }

    async def check_connection(self) -> bool:
        """检查与Android设备的连接状态"""
        try:
            result = await self.call_android_api("ping")
            return result.get("success", False)
        except:
            return False

# 创建Android桥接实例
android_bridge = AndroidBridge()

def format_response(success: bool, message: str, data: Dict = None) -> str:
    """格式化响应消息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    response = {
        "success": success,
        "message": message,
        "timestamp": timestamp
    }
    
    if data:
        response["data"] = data
        
    return json.dumps(response, ensure_ascii=False, indent=2)

# MCP工具定义
@server.list_tools()
async def list_tools() -> ListToolsResult:
    """列出所有可用的MCP工具"""
    return ListToolsResult(
        tools=[
            Tool(
                name="start_pomodoro",
                description="🍅 启动番茄钟计时器，开始专注工作时间",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "任务名称（必需）"
                        },
                        "duration": {
                            "type": "integer",
                            "description": "番茄钟时长（分钟，默认25）",
                            "default": 25,
                            "minimum": 5,
                            "maximum": 60
                        },
                        "task_id": {
                            "type": "string",
                            "description": "关联的任务ID（可选）"
                        }
                    },
                    "required": ["task_name"]
                }
            ),
            Tool(
                name="control_pomodoro",
                description="⏯️ 控制番茄钟状态（暂停/恢复/停止/查询）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["pause", "resume", "stop", "status"],
                            "description": "操作类型"
                        },
                        "reason": {
                            "type": "string",
                            "description": "操作原因（可选）"
                        }
                    },
                    "required": ["action"]
                }
            ),
            Tool(
                name="manage_break",
                description="☕ 管理休息时间（开始休息/跳过休息）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "skip"],
                            "description": "休息操作类型"
                        }
                    },
                    "required": ["action"]
                }
            ),
            Tool(
                name="manage_tasks",
                description="📋 四象限任务管理（创建/更新/删除/列表/完成）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "delete", "list", "complete"],
                            "description": "任务操作类型"
                        },
                        "task_data": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "任务名称"},
                                "description": {"type": "string", "description": "任务描述"},
                                "importance": {"type": "integer", "minimum": 1, "maximum": 4, "description": "重要性(1-4)"},
                                "urgency": {"type": "integer", "minimum": 1, "maximum": 4, "description": "紧急性(1-4)"},
                                "due_date": {"type": "string", "description": "截止日期"},
                                "estimated_pomodoros": {"type": "integer", "description": "预计番茄钟数"}
                            },
                            "description": "任务数据（创建/更新时必需）"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "任务ID（更新/删除/完成时必需）"
                        }
                    },
                    "required": ["action"]
                }
            ),
            Tool(
                name="get_statistics",
                description="📊 获取统计数据和分析报告",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["general", "daily", "weekly", "monthly", "pomodoro", "tasks"],
                            "description": "统计类型"
                        },
                        "period": {
                            "type": "string",
                            "description": "统计周期（可选）"
                        },
                        "filters": {
                            "type": "object",
                            "description": "过滤条件（可选）"
                        }
                    },
                    "required": ["type"]
                }
            ),
            Tool(
                name="update_settings",
                description="⚙️ 更新系统设置和用户偏好",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dark_mode": {"type": "boolean", "description": "深色模式"},
                        "tomato_duration": {"type": "integer", "description": "番茄钟时长（分钟）"},
                        "break_duration": {"type": "integer", "description": "休息时长（分钟）"},
                        "notification_enabled": {"type": "boolean", "description": "通知开关"},
                        "auto_start_break": {"type": "boolean", "description": "自动开始休息"},
                        "sound_enabled": {"type": "boolean", "description": "声音提醒"}
                    }
                }
            ),
            Tool(
                name="check_android_status",
                description="📱 检查Android设备连接状态和功能可用性",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    )

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """调用指定的MCP工具"""
    
    try:
        logger.info(f"🔧 调用工具: {name}, 参数: {arguments}")
        
        if name == "start_pomodoro":
            task_name = arguments.get("task_name")
            duration = arguments.get("duration", 25)
            task_id = arguments.get("task_id")
            
            if not task_name:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 任务名称不能为空")
                    )]
                )
            
            result = await android_bridge.call_android_api("start_pomodoro", {
                "task_name": task_name,
                "duration": duration,
                "task_id": task_id
            })
            
            if result.get("success"):
                message = f"🍅 番茄钟启动成功！\n📝 任务: {task_name}\n⏰ 时长: {duration}分钟"
            else:
                message = result.get("message", "❌ 启动番茄钟失败")
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "control_pomodoro":
            action = arguments.get("action")
            reason = arguments.get("reason")
            
            if action not in ["pause", "resume", "stop", "status"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 无效的操作类型，支持: pause, resume, stop, status")
                    )]
                )
            
            result = await android_bridge.call_android_api("control_pomodoro", {
                "action": action,
                "reason": reason
            })
            
            action_emoji = {
                "pause": "⏸️", "resume": "▶️", "stop": "⏹️", "status": "📊"
            }
            action_text = {
                "pause": "暂停", "resume": "恢复", "stop": "停止", "status": "查询状态"
            }
            
            if result.get("success"):
                message = f"{action_emoji[action]} 番茄钟{action_text[action]}成功"
                if reason:
                    message += f"\n📝 原因: {reason}"
            else:
                message = result.get("message", f"❌ {action_text[action]}失败")
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "manage_break":
            action = arguments.get("action")
            
            if action not in ["start", "skip"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 无效的休息操作，支持: start, skip")
                    )]
                )
            
            result = await android_bridge.call_android_api("manage_break", {
                "action": action
            })
            
            if action == "start":
                message = "☕ 休息时间开始，好好放松一下吧！" if result.get("success") else "❌ 开始休息失败"
            else:
                message = "⏭️ 跳过休息，继续加油工作！" if result.get("success") else "❌ 跳过休息失败"
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "manage_tasks":
            action = arguments.get("action")
            task_data = arguments.get("task_data")
            task_id = arguments.get("task_id")
            
            if action not in ["create", "update", "delete", "list", "complete"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 无效的任务操作，支持: create, update, delete, list, complete")
                    )]
                )
            
            # 验证参数
            if action in ["create", "update"] and not task_data:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 创建或更新任务时必须提供task_data")
                    )]
                )
                
            if action in ["update", "delete", "complete"] and not task_id:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 更新、删除或完成任务时必须提供task_id")
                    )]
                )
            
            # 验证任务数据
            if task_data:
                try:
                    TaskData(**task_data)
                except Exception as e:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=format_response(False, f"❌ 任务数据格式错误: {str(e)}")
                        )]
                    )
            
            result = await android_bridge.call_android_api("manage_tasks", {
                "action": action,
                "task_data": task_data,
                "task_id": task_id
            })
            
            action_messages = {
                "create": "📝 任务创建成功",
                "update": "✏️ 任务更新成功", 
                "delete": "🗑️ 任务删除成功",
                "list": "📋 任务列表获取成功",
                "complete": "✅ 任务完成"
            }
            
            if result.get("success"):
                message = action_messages.get(action, "操作成功")
                if action == "create" and task_data:
                    # 计算四象限分类
                    importance = task_data.get("importance", 1)
                    urgency = task_data.get("urgency", 1)
                    if importance >= 3 and urgency >= 3:
                        quadrant = "第一象限（重要且紧急）"
                    elif importance >= 3 and urgency < 3:
                        quadrant = "第二象限（重要不紧急）"
                    elif importance < 3 and urgency >= 3:
                        quadrant = "第三象限（不重要紧急）"
                    else:
                        quadrant = "第四象限（不重要不紧急）"
                    message += f"\n🎯 分类: {quadrant}"
            else:
                message = result.get("message", f"❌ {action}操作失败")
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "get_statistics":
            stat_type = arguments.get("type")
            period = arguments.get("period")
            filters = arguments.get("filters")
            
            if stat_type not in ["general", "daily", "weekly", "monthly", "pomodoro", "tasks"]:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 无效的统计类型")
                    )]
                )
            
            result = await android_bridge.call_android_api("get_statistics", {
                "type": stat_type,
                "period": period,
                "filters": filters
            })
            
            type_names = {
                "general": "总体统计",
                "daily": "日统计", 
                "weekly": "周统计",
                "monthly": "月统计",
                "pomodoro": "番茄钟统计",
                "tasks": "任务统计"
            }
            
            if result.get("success"):
                message = f"📊 {type_names[stat_type]}获取成功"
            else:
                message = result.get("message", "❌ 获取统计数据失败")
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "update_settings":
            settings = {k: v for k, v in arguments.items() if v is not None}
            
            if not settings:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=format_response(False, "❌ 请提供要更新的设置项")
                    )]
                )
            
            result = await android_bridge.call_android_api("update_settings", settings)
            
            if result.get("success"):
                setting_count = len(settings)
                message = f"⚙️ 成功更新{setting_count}项设置"
            else:
                message = result.get("message", "❌ 更新设置失败")
                
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, result.get("data"))
                )]
            )
            
        elif name == "check_android_status":
            result = await android_bridge.call_android_api("check_status")
            
            if result.get("success"):
                message = "📱 Android设备连接正常，所有功能可用"
            else:
                message = "❌ Android设备连接异常，请检查网络和设备状态"
                
            # 额外检查连接状态
            connection_ok = await android_bridge.check_connection()
            status_data = result.get("data", {})
            status_data["connection_test"] = connection_ok
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(result.get("success", False), message, status_data)
                )]
            )
            
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_response(False, f"❌ 未知的工具: {name}")
                )]
            )
            
    except Exception as e:
        logger.error(f"调用工具时发生错误: {str(e)}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=format_response(False, f"❗ 调用工具时发生错误: {str(e)}")
            )]
        )

async def main():
    """启动MCP服务器"""
    logger.info("🚀 启动四象限MCP服务器...")
    
    # 检查Android连接
    logger.info("🔗 检查Android设备连接...")
    is_connected = await android_bridge.check_connection()
    if is_connected:
        logger.info("✅ Android设备连接正常")
    else:
        logger.warning("⚠️ Android设备连接失败，服务器将继续运行但功能可能受限")
    
    # 启动stdio服务器
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
