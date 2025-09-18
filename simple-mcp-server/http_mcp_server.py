#!/usr/bin/env python3
"""
HTTP-based MCP Server
基于HTTP的MCP服务器实现，使用FastAPI提供RESTful API接口
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import json as json_module

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MCP_Server")

# 设置控制台输出编码为UTF-8（Windows兼容）
import sys
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        else:
            # 如果没有buffer属性，设置环境变量
            import os
            os.environ['PYTHONIOENCODING'] = 'utf-8'
    except Exception:
        # 如果设置失败，忽略错误继续运行
        pass

# 导入LangChain处理模块
try:
    from langchain_handler import chat_with_langchain, LANGCHAIN_AVAILABLE
except ImportError:
    print("⚠️  LangChain处理模块导入失败")
    LANGCHAIN_AVAILABLE = False
    
    async def chat_with_langchain(message: str, api_key: str = None, deepseek_api_key: str = None, 
                                model: str = "gpt-3.5-turbo", temperature: float = 0.7, max_tokens: int = 1000) -> dict:
        return {
            "success": False,
            "error": "LangChain处理模块不可用",
            "result": None,
            "tool_calls": []
        }

# 请求和响应模型
class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class ToolCallResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None

class ToolInfo(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class ListToolsResponse(BaseModel):
    tools: List[ToolInfo]

class ServerInfoResponse(BaseModel):
    name: str
    version: str
    description: str
    capabilities: List[str]

# 聊天相关模型
class ChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    model: Optional[str] = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

# 从langchain_handler导入响应模型
try:
    from langchain_handler import ToolCall, ChatResponse
except ImportError:
    class ToolCall(BaseModel):
        tool_name: str
        arguments: Dict[str, Any]
        result: Optional[str] = None
        

    class ChatResponse(BaseModel):
        success: bool
        result: Optional[str] = None
        error: Optional[str] = None
        tool_calls: Optional[List[ToolCall]] = None
        model_used: Optional[str] = None

# WebSocket相关模型
class WebSocketMessage(BaseModel):
    type: str  # "chat", "config", "ping", "pong"
    data: Dict[str, Any]

class ConnectionManager:
    """WebSocket连接管理器"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📱 新的WebSocket连接，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"📱 WebSocket连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json_module.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"发送消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_module.dumps(message, ensure_ascii=False))
            except Exception as e:
                print(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

# 创建连接管理器实例
manager = ConnectionManager()

# 创建FastAPI应用
app = FastAPI(
    title="HTTP MCP Server",
    description="基于HTTP的Model Context Protocol服务器",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加静态文件服务
try:
    app.mount("/static", StaticFiles(directory="."), name="static")
except Exception as e:
    print(f"⚠️  静态文件服务配置失败: {e}")

# 工具定义
TOOLS = [
    {
        "name": "read_file",
        "description": "读取文件内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": "写入文件内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "列出目录中的文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "要列出文件的目录路径"
                }
            },
            "required": ["directory_path"]
        }
    }
]

# 工具实现函数
async def read_file_impl(file_path: str) -> str:
    """读取文件内容"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"文件 {file_path} 的内容:\n{content}"
    except Exception as e:
        raise Exception(f"读取文件失败: {str(e)}")

async def write_file_impl(file_path: str, content: str) -> str:
    """写入文件内容"""
    try:
        # 验证文件路径
        if not file_path or file_path.strip() == "":
            raise ValueError("文件路径不能为空")
        
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        
        # 确保目录存在
        dir_path = os.path.dirname(abs_path)
        if dir_path:  # 只有当目录路径不为空时才创建
            os.makedirs(dir_path, exist_ok=True)
        
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"成功写入文件: {abs_path}"
    except Exception as e:
        raise Exception(f"写入文件失败: {str(e)}")

async def list_files_impl(directory_path: str) -> str:
    """列出目录中的文件"""
    try:
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"路径不是目录: {directory_path}")
        
        files = []
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isfile(item_path):
                files.append(f"📄 {item}")
            elif os.path.isdir(item_path):
                files.append(f"📁 {item}/")
        
        if not files:
            return f"目录 {directory_path} 为空"
        
        return f"目录 {directory_path} 的内容:\n" + "\n".join(files)
    except Exception as e:
        raise Exception(f"列出文件失败: {str(e)}")

# 工具调用映射
TOOL_FUNCTIONS = {
    "read_file": read_file_impl,
    "write_file": write_file_impl,
    "list_files": list_files_impl
}



# API路由
@app.get("/", response_model=ServerInfoResponse)
async def get_server_info():
    """获取服务器信息"""
    return ServerInfoResponse(
        name="HTTP MCP Server",
        version="1.0.0",
        description="基于HTTP的Model Context Protocol服务器",
        capabilities=["tools", "file_operations"]
    )

@app.get("/tools", response_model=ListToolsResponse)
async def list_tools():
    """列出所有可用工具"""
    tools = [ToolInfo(**tool) for tool in TOOLS]
    return ListToolsResponse(tools=tools)

@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """调用指定工具"""
    logger.info(f"🔧 收到MCP工具调用请求 - 工具名称: {request.name}")
    logger.info(f"📝 工具参数: {request.arguments}")
    
    try:
        # 检查工具是否存在
        if request.name not in TOOL_FUNCTIONS:
            logger.warning(f"⚠️  工具不存在: {request.name}")
            logger.info(f"📋 可用工具列表: {list(TOOL_FUNCTIONS.keys())}")
            raise HTTPException(
                status_code=404, 
                detail=f"工具 '{request.name}' 不存在"
            )
        
        logger.info(f"✅ 工具验证通过，开始执行: {request.name}")
        
        # 获取工具函数
        tool_function = TOOL_FUNCTIONS[request.name]
        
        # 调用工具函数
        start_time = datetime.now()
        result = await tool_function(**request.arguments)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(f"🎉 工具执行成功 - 工具: {request.name}, 耗时: {execution_time:.3f}秒")
        logger.info(f"📤 工具返回结果长度: {len(str(result))} 字符")
        
        return ToolCallResponse(
            success=True,
            result=result
        )
    
    except HTTPException as e:
        logger.error(f"❌ HTTP异常 - 工具: {request.name}, 错误: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ 工具执行失败 - 工具: {request.name}, 错误: {str(e)}")
        return ToolCallResponse(
            success=False,
            result=None,
            error=str(e)
        )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """聊天API端点"""
    logger.info(f"📨 收到聊天请求 - 消息长度: {len(request.message)} 字符")
    logger.info(f"🤖 模型配置 - 模型: {request.model}, 温度: {request.temperature}, 最大令牌: {request.max_tokens}")
    
    # 记录API密钥状态（不记录实际密钥值）
    has_openai_key = bool(request.api_key)
    has_deepseek_key = bool(request.deepseek_api_key)
    logger.info(f"🔑 API密钥状态 - OpenAI: {'✅' if has_openai_key else '❌'}, DeepSeek: {'✅' if has_deepseek_key else '❌'}")
    
    # 检查是否提供了任一API密钥
    if not request.api_key and not request.deepseek_api_key:
        logger.warning("⚠️  请求被拒绝 - 未提供任何API密钥")
        raise HTTPException(status_code=400, detail="需要提供API密钥（OpenAI或DeepSeek）")
    
    # 判断是否为DeepSeek模型
    is_deepseek = request.model.startswith('deepseek')
    logger.info(f"🎯 模型类型判断 - 是否DeepSeek模型: {'是' if is_deepseek else '否'}")
    
    # 如果是DeepSeek模型但没有DeepSeek密钥，检查是否有OpenAI密钥作为备用
    if is_deepseek and not request.deepseek_api_key and not request.api_key:
        logger.warning("⚠️  请求被拒绝 - DeepSeek模型需要DeepSeek API密钥")
        raise HTTPException(status_code=400, detail="DeepSeek模型需要提供DeepSeek API密钥")
    # 如果不是DeepSeek模型但没有OpenAI密钥，检查是否有DeepSeek密钥作为备用
    elif not is_deepseek and not request.api_key and not request.deepseek_api_key:
        logger.warning("⚠️  请求被拒绝 - OpenAI模型需要OpenAI API密钥")
        raise HTTPException(status_code=400, detail="OpenAI模型需要提供OpenAI API密钥")
    
    if not LANGCHAIN_AVAILABLE:
        logger.error("❌ LangChain不可用 - 聊天功能被禁用")
        raise HTTPException(
            status_code=503, 
            detail="LangChain未安装，请先安装: pip install langchain langchain-openai"
        )
    
    logger.info("🚀 开始调用LangChain处理聊天请求")
    
    try:
        response_dict = await chat_with_langchain(
            message=request.message,
            api_key=request.api_key,
            deepseek_api_key=request.deepseek_api_key,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 记录响应状态
        success = response_dict.get("success", False)
        tool_calls_count = len(response_dict.get("tool_calls", []))
        logger.info(f"✅ LangChain处理完成 - 成功: {'是' if success else '否'}, MCP工具调用次数: {tool_calls_count}")
        
        if tool_calls_count > 0:
            logger.info("🔧 检测到MCP工具调用，记录工具使用情况:")
            for i, tc in enumerate(response_dict.get("tool_calls", [])):
                tool_name = tc.get("tool_name", "未知工具")
                logger.info(f"   {i+1}. 工具: {tool_name}")
        
        # 将dict转换为ChatResponse对象
        return ChatResponse(
            success=response_dict.get("success", False),
            result=response_dict.get("result"),
            error=response_dict.get("error"),
            tool_calls=[ToolCall(**tc) if isinstance(tc, dict) else tc for tc in response_dict.get("tool_calls", [])],
            model_used=response_dict.get("model_used")
        )
    except Exception as e:
        logger.error(f"❌ 聊天处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy", 
        "timestamp": asyncio.get_event_loop().time(),
        "langchain_available": LANGCHAIN_AVAILABLE,
        "websocket_connections": len(manager.active_connections)
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时聊天"""
    client_host = websocket.client.host if websocket.client else "未知"
    logger.info(f"🔌 新的WebSocket连接请求 - 客户端: {client_host}")
    
    await manager.connect(websocket)
    logger.info(f"✅ WebSocket连接已建立 - 当前连接数: {len(manager.active_connections)}")
    
    try:
        # 发送欢迎消息
        await manager.send_personal_message({
            "type": "system",
            "data": {
                "message": "🎉 WebSocket连接成功！现在可以进行实时聊天了。",
                "timestamp": asyncio.get_event_loop().time(),
                "langchain_available": LANGCHAIN_AVAILABLE
            }
        }, websocket)
        logger.info("📤 已发送WebSocket欢迎消息")
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            logger.info(f"📨 收到WebSocket消息 - 长度: {len(data)} 字符")
            
            try:
                message_data = json_module.loads(data)
                message_type = message_data.get("type", "unknown")
                logger.info(f"📋 消息类型: {message_type}")
                
                if message_type == "ping":
                    # 处理心跳
                    logger.debug("💓 处理心跳ping消息")
                    await manager.send_personal_message({
                        "type": "pong",
                        "data": {"timestamp": asyncio.get_event_loop().time()}
                    }, websocket)
                    
                elif message_type == "chat":
                    # 处理聊天消息
                    logger.info("💬 开始处理WebSocket聊天消息")
                    chat_data = message_data.get("data", {})
                    user_message = chat_data.get("message", "")
                    api_key = chat_data.get("api_key", "")
                    deepseek_api_key = chat_data.get("deepseek_api_key", "")
                    model = chat_data.get("model", "gpt-3.5-turbo")
                    temperature = chat_data.get("temperature", 0.7)
                    max_tokens = chat_data.get("max_tokens", 1000)
                    
                    logger.info(f"📝 用户消息: {user_message}")
                    logger.info(f"🤖 WebSocket模型配置 - 模型: {model}, 温度: {temperature}")
                    
                    # 记录API密钥状态
                    has_openai = bool(api_key)
                    has_deepseek = bool(deepseek_api_key)
                    logger.info(f"🔑 WebSocket API密钥状态 - OpenAI: {'✅' if has_openai else '❌'}, DeepSeek: {'✅' if has_deepseek else '❌'}")
                    
                    if not user_message:
                        logger.warning("⚠️  WebSocket消息为空")
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": "消息内容不能为空"}
                        }, websocket)
                        continue
                    
                    if not api_key and not deepseek_api_key:
                        logger.warning("⚠️  WebSocket请求缺少API密钥")
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": "需要提供API密钥（OpenAI或DeepSeek）"}
                        }, websocket)
                        continue
                    
                    if not LANGCHAIN_AVAILABLE:
                        logger.error("❌ WebSocket请求失败 - LangChain不可用")
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": "LangChain未安装，请先安装相关依赖"}
                        }, websocket)
                        continue
                    
                    logger.info("🚀 WebSocket开始调用LangChain")
                    
                    # 发送处理中状态
                    await manager.send_personal_message({
                        "type": "processing",
                        "data": {"message": "正在处理您的消息..."}
                    }, websocket)
                    
                    try:
                        # 调用LangChain聊天功能
                        start_time = datetime.now()
                        chat_response = await chat_with_langchain(
                            message=user_message,
                            api_key=api_key,
                            deepseek_api_key=deepseek_api_key,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds()
                        
                        # 记录处理结果
                        success = chat_response.get("success", False)
                        tool_calls_count = len(chat_response.get("tool_calls", []))
                        logger.info(f"✅ WebSocket LangChain处理完成 - 成功: {'是' if success else '否'}, 耗时: {processing_time:.3f}秒, MCP工具调用: {tool_calls_count}次")
                        
                        # 发送聊天响应
                        await manager.send_personal_message({
                            "type": "chat_response",
                            "data": {
                                "success": chat_response.get("success", False),
                                "result": chat_response.get("result"),
                                "error": chat_response.get("error"),
                                "tool_calls": chat_response.get("tool_calls", []),
                                "model_used": chat_response.get("model_used"),
                                "timestamp": asyncio.get_event_loop().time()
                            }
                        }, websocket)
                        logger.info("📤 WebSocket响应已发送")
                        
                    except Exception as e:
                        logger.error(f"❌ WebSocket聊天处理失败: {str(e)}")
                        await manager.send_personal_message({
                            "type": "error",
                            "data": {"message": f"聊天处理失败: {str(e)}"}
                        }, websocket)
                
                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "data": {"message": f"未知的消息类型: {message_type}"}
                    }, websocket)
                    
            except json_module.JSONDecodeError as e:
                logger.warning(f"⚠️  WebSocket收到无效JSON: {str(e)}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "无效的JSON格式"}
                }, websocket)
            except Exception as e:
                logger.error(f"❌ WebSocket消息处理异常: {str(e)}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": f"处理消息时发生错误: {str(e)}"}
                }, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket连接断开 - 剩余连接数: {len(manager.active_connections) - 1}")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket连接异常: {str(e)}")
        manager.disconnect(websocket)

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return {
        "success": False,
        "error": "API端点不存在",
        "detail": str(exc.detail)
    }

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return {
        "success": False,
        "error": "服务器内部错误",
        "detail": str(exc)
    }

if __name__ == "__main__":
    logger.info("🚀 启动HTTP MCP服务器...")
    logger.info("📡 服务器地址: http://localhost:8000")
    logger.info("📚 API文档: http://localhost:8000/docs")
    logger.info("🔧 可用工具: read_file, write_file, list_files")
    logger.info("📝 日志文件: mcp_server.log")
    
    if LANGCHAIN_AVAILABLE:
        logger.info("💬 聊天功能: 已启用 (需要OpenAI API密钥)")
        logger.info("🌐 前端界面: chat_interface.html")
    else:
        logger.warning("⚠️  聊天功能: 未启用 (LangChain未安装)")
    
    print("🚀 启动HTTP MCP服务器...")
    print("📡 服务器地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🔧 可用工具: read_file, write_file, list_files")
    print("📝 详细日志: mcp_server.log")
    if LANGCHAIN_AVAILABLE:
        print("💬 聊天功能: 已启用 (需要OpenAI API密钥)")
        print("🌐 前端界面: chat_interface.html")
    else:
        print("⚠️  聊天功能: 未启用 (LangChain未安装)")
    print("\n按 Ctrl+C 停止服务器")

    uvicorn.run(
        "http_mcp_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )