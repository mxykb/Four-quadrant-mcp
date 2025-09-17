#!/usr/bin/env python3
"""
HTTP-based MCP Client
基于HTTP的MCP客户端实现，使用HTTP请求与MCP服务器通信
"""

import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    result: Any
    error: Optional[str] = None

class HTTPMCPClient:
    """基于HTTP的MCP客户端"""
    
    def __init__(self, server_url: str = "http://localhost:8000", timeout: int = 30):
        """
        初始化HTTP MCP客户端
        
        Args:
            server_url: MCP服务器的URL地址
            timeout: 请求超时时间（秒）
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self._tools_cache: Optional[List[ToolInfo]] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    async def connect(self):
        """连接到MCP服务器"""
        try:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            # 测试连接
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ 成功连接到MCP服务器: {self.server_url}")
                    logger.info(f"📡 服务器状态: {data.get('message', 'Unknown')}")
                else:
                    raise Exception(f"服务器响应错误: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ 连接MCP服务器失败: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            raise
    
    async def disconnect(self):
        """断开与MCP服务器的连接"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("🔌 已断开与MCP服务器的连接")
    
    async def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        if not self.session:
            raise Exception("客户端未连接，请先调用 connect()")
        
        try:
            async with self.session.get(f"{self.server_url}/") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"获取服务器信息失败: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ 获取服务器信息失败: {e}")
            raise
    
    async def list_tools(self, use_cache: bool = True) -> List[ToolInfo]:
        """列出所有可用工具"""
        if not self.session:
            raise Exception("客户端未连接，请先调用 connect()")
        
        # 使用缓存
        if use_cache and self._tools_cache:
            return self._tools_cache
        
        try:
            async with self.session.get(f"{self.server_url}/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    tools = [ToolInfo(**tool) for tool in data["tools"]]
                    self._tools_cache = tools
                    logger.info(f"📋 获取到 {len(tools)} 个可用工具")
                    return tools
                else:
                    raise Exception(f"获取工具列表失败: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ 获取工具列表失败: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """调用指定工具"""
        if not self.session:
            raise Exception("客户端未连接，请先调用 connect()")
        
        try:
            # 准备请求数据
            request_data = {
                "name": tool_name,
                "arguments": arguments
            }
            
            logger.info(f"🔧 调用工具: {tool_name}")
            logger.debug(f"📝 参数: {arguments}")
            
            # 发送POST请求
            async with self.session.post(
                f"{self.server_url}/tools/call",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    result = ToolCallResult(
                        success=data["success"],
                        result=data["result"],
                        error=data.get("error")
                    )
                    
                    if result.success:
                        logger.info(f"✅ 工具调用成功: {tool_name}")
                    else:
                        logger.warning(f"⚠️ 工具调用失败: {result.error}")
                    
                    return result
                
                elif response.status == 404:
                    error_data = await response.json()
                    return ToolCallResult(
                        success=False,
                        result=None,
                        error=error_data.get("detail", "工具不存在")
                    )
                
                else:
                    raise Exception(f"HTTP请求失败: {response.status}")
        
        except Exception as e:
            logger.error(f"❌ 调用工具失败: {e}")
            return ToolCallResult(
                success=False,
                result=None,
                error=str(e)
            )
    
    async def read_file(self, file_path: str) -> str:
        """读取文件内容的便捷方法"""
        result = await self.call_tool("read_file", {"file_path": file_path})
        if result.success:
            return result.result
        else:
            raise Exception(f"读取文件失败: {result.error}")
    
    async def write_file(self, file_path: str, content: str) -> str:
        """写入文件内容的便捷方法"""
        result = await self.call_tool("write_file", {
            "file_path": file_path,
            "content": content
        })
        if result.success:
            return result.result
        else:
            raise Exception(f"写入文件失败: {result.error}")
    
    async def list_files(self, directory_path: str) -> str:
        """列出目录文件的便捷方法"""
        result = await self.call_tool("list_files", {"directory_path": directory_path})
        if result.success:
            return result.result
        else:
            raise Exception(f"列出文件失败: {result.error}")

# 同步包装器类
class HTTPMCPClientSync:
    """HTTP MCP客户端的同步包装器"""
    
    def __init__(self, server_url: str = "http://localhost:8000", timeout: int = 30):
        self.client = HTTPMCPClient(server_url, timeout)
        self.loop = None
    
    def _get_loop(self):
        """获取或创建事件循环"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def connect(self):
        """连接到服务器"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.connect())
    
    def disconnect(self):
        """断开连接"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.disconnect())
    
    def list_tools(self) -> List[ToolInfo]:
        """列出工具"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.list_tools())
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """调用工具"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.call_tool(tool_name, arguments))
    
    def read_file(self, file_path: str) -> str:
        """读取文件"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.read_file(file_path))
    
    def write_file(self, file_path: str, content: str) -> str:
        """写入文件"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.write_file(file_path, content))
    
    def list_files(self, directory_path: str) -> str:
        """列出文件"""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.list_files(directory_path))

# 示例使用
async def main():
    """示例：如何使用HTTP MCP客户端"""
    print("🚀 HTTP MCP客户端示例")
    
    # 使用异步上下文管理器
    async with HTTPMCPClient("http://localhost:8000") as client:
        # 获取服务器信息
        server_info = await client.get_server_info()
        print(f"📡 服务器信息: {server_info['name']} v{server_info['version']}")
        
        # 列出可用工具
        tools = await client.list_tools()
        print(f"\n🔧 可用工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # 测试文件操作
        print("\n📝 测试文件操作:")
        
        # 写入文件
        write_result = await client.write_file(
            "test_http_mcp.txt", 
            "这是通过HTTP MCP客户端写入的测试内容\n时间: " + str(asyncio.get_event_loop().time())
        )
        print(f"✍️ 写入结果: {write_result}")
        
        # 读取文件
        read_result = await client.read_file("test_http_mcp.txt")
        print(f"📖 读取结果: {read_result}")
        
        # 列出当前目录文件
        list_result = await client.list_files(".")
        print(f"📂 目录内容: {list_result}")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())