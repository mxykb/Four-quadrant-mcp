#!/usr/bin/env python3
"""
MCP 服务器数据模型定义
包含所有请求、响应、配置等数据模型
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass


# ================================
# 基础枚举定义
# ================================

class MessageType(str, Enum):
    """WebSocket消息类型"""
    CHAT = "chat"
    CONFIG = "config"
    PING = "ping"
    PONG = "pong"
    PROCESSING = "processing"
    CHAT_RESPONSE = "chat_response"
    ERROR = "error"
    SYSTEM = "system"


class ModelProvider(str, Enum):
    """模型提供商"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


# ================================
# MCP 工具相关模型
# ================================

class ToolInfo(BaseModel):
    """MCP工具信息"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    inputSchema: Dict[str, Any] = Field(..., description="工具输入模式")


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")


class ToolCall(BaseModel):
    """工具调用记录"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")
    result: Optional[str] = Field(None, description="执行结果")


# ================================
# 聊天相关模型
# ================================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    api_key: Optional[str] = Field(None, description="OpenAI API密钥")
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API密钥")
    model: Optional[str] = Field("gpt-3.5-turbo", description="使用的模型")
    temperature: Optional[float] = Field(0.7, description="温度参数")
    max_tokens: Optional[int] = Field(1000, description="最大令牌数")


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool = Field(..., description="是否成功")
    result: Optional[str] = Field(None, description="AI回复内容")
    error: Optional[str] = Field(None, description="错误信息")
    tool_calls: Optional[List[ToolCall]] = Field([], description="工具调用列表")
    model_used: Optional[str] = Field(None, description="使用的模型")


# ================================
# WebSocket相关模型
# ================================

class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: MessageType = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")


class WebSocketChatData(BaseModel):
    """WebSocket聊天数据"""
    message: str = Field(..., description="用户消息")
    api_key: Optional[str] = Field(None, description="OpenAI API密钥")
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API密钥")
    model: Optional[str] = Field("gpt-3.5-turbo", description="使用的模型")
    temperature: Optional[float] = Field(0.7, description="温度参数")
    max_tokens: Optional[int] = Field(1000, description="最大令牌数")


class WebSocketResponse(BaseModel):
    """WebSocket响应"""
    type: MessageType = Field(..., description="响应类型")
    data: Dict[str, Any] = Field(..., description="响应数据")


# ================================
# 服务器信息模型
# ================================

class ServerCapabilities(BaseModel):
    """服务器能力"""
    tools: bool = Field(True, description="支持工具调用")
    file_operations: bool = Field(True, description="支持文件操作")
    langchain: bool = Field(False, description="支持LangChain")
    websocket: bool = Field(True, description="支持WebSocket")


class ServerInfo(BaseModel):
    """服务器信息"""
    name: str = Field("HTTP MCP Server", description="服务器名称")
    version: str = Field("1.0.0", description="版本号")
    description: str = Field("基于HTTP的Model Context Protocol服务器", description="描述")
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities, description="服务器能力")


class HealthStatus(BaseModel):
    """健康状态"""
    status: str = Field("healthy", description="状态")
    timestamp: float = Field(..., description="时间戳")
    langchain_available: bool = Field(False, description="LangChain是否可用")
    websocket_connections: int = Field(0, description="WebSocket连接数")


# ================================
# 工具执行相关模型
# ================================

@dataclass
class FileOperation:
    """文件操作记录"""
    operation: str  # read, write, list
    file_path: str
    content: Optional[str] = None
    timestamp: float = 0.0
    success: bool = False
    error: Optional[str] = None


class FileReadRequest(BaseModel):
    """文件读取请求"""
    file_path: str = Field(..., description="文件路径")


class FileWriteRequest(BaseModel):
    """文件写入请求"""
    file_path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")


class FileListRequest(BaseModel):
    """文件列表请求"""
    directory_path: str = Field(..., description="目录路径")


# ================================
# 错误处理模型
# ================================

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="总是False")
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")


class ValidationError(BaseModel):
    """验证错误"""
    field: str = Field(..., description="字段名")
    message: str = Field(..., description="错误信息")
    value: Any = Field(None, description="错误值")


# ================================
# 配置相关模型
# ================================

class ModelConfig(BaseModel):
    """模型配置"""
    provider: ModelProvider = Field(..., description="模型提供商")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    temperature: float = Field(0.7, description="温度参数")
    max_tokens: int = Field(1000, description="最大令牌数")


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field("0.0.0.0", description="服务器主机")
    port: int = Field(8000, description="服务器端口")
    debug: bool = Field(False, description="调试模式")
    log_level: str = Field("INFO", description="日志级别")
    cors_origins: List[str] = Field(["*"], description="CORS允许的源")


# ================================
# 统计和监控模型
# ================================

class ToolUsageStats(BaseModel):
    """工具使用统计"""
    tool_name: str = Field(..., description="工具名称")
    call_count: int = Field(0, description="调用次数")
    success_count: int = Field(0, description="成功次数")
    error_count: int = Field(0, description="错误次数")
    last_used: Optional[float] = Field(None, description="最后使用时间")


class ServerStats(BaseModel):
    """服务器统计"""
    uptime: float = Field(..., description="运行时间")
    total_requests: int = Field(0, description="总请求数")
    websocket_connections: int = Field(0, description="WebSocket连接数")
    tool_stats: List[ToolUsageStats] = Field([], description="工具使用统计")


# ================================
# 导出所有模型
# ================================

__all__ = [
    # 枚举
    "MessageType", "ModelProvider",
    
    # MCP工具相关
    "ToolInfo", "ToolCallRequest", "ToolCallResponse", "ToolCall",
    
    # 聊天相关
    "ChatRequest", "ChatResponse",
    
    # WebSocket相关
    "WebSocketMessage", "WebSocketChatData", "WebSocketResponse",
    
    # 服务器信息
    "ServerCapabilities", "ServerInfo", "HealthStatus",
    
    # 文件操作
    "FileOperation", "FileReadRequest", "FileWriteRequest", "FileListRequest",
    
    # 错误处理
    "ErrorResponse", "ValidationError",
    
    # 配置
    "ModelConfig", "ServerConfig",
    
    # 统计监控
    "ToolUsageStats", "ServerStats"
]
