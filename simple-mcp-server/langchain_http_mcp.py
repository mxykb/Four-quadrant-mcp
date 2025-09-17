#!/usr/bin/env python3
"""
LangChain HTTP MCP Integration
基于HTTP的LangChain MCP集成，使用HTTP通信方式
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Type
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.schema import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
import logging

# 导入HTTP MCP客户端
from http_mcp_client import HTTPMCPClient, ToolInfo, ToolCallResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HTTPMCPToolInput(BaseModel):
    """HTTP MCP工具输入模型"""
    arguments: Dict[str, Any] = Field(description="工具调用参数")

class HTTPMCPTool(BaseTool):
    """基于HTTP MCP的LangChain工具包装器"""
    
    name: str
    description: str
    mcp_client: HTTPMCPClient
    tool_name: str
    args_schema: Type[BaseModel] = HTTPMCPToolInput
    
    def __init__(self, mcp_client: HTTPMCPClient, tool_info: ToolInfo, **kwargs):
        """
        初始化HTTP MCP工具
        
        Args:
            mcp_client: HTTP MCP客户端实例
            tool_info: MCP工具信息
        """
        super().__init__(
            name=tool_info.name,
            description=tool_info.description,
            mcp_client=mcp_client,
            tool_name=tool_info.name,
            **kwargs
        )
    
    def _run(self, arguments: Dict[str, Any]) -> str:
        """同步运行工具（通过异步包装）"""
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 运行异步方法
            result = loop.run_until_complete(self._arun(arguments))
            return result
        except Exception as e:
            logger.error(f"❌ 同步工具调用失败: {e}")
            return f"工具调用失败: {str(e)}"
    
    async def _arun(self, arguments: Dict[str, Any]) -> str:
        """异步运行工具"""
        try:
            logger.info(f"🔧 调用HTTP MCP工具: {self.tool_name}")
            logger.debug(f"📝 参数: {arguments}")
            
            # 调用MCP工具
            result = await self.mcp_client.call_tool(self.tool_name, arguments)
            
            if result.success:
                logger.info(f"✅ 工具调用成功: {self.tool_name}")
                return str(result.result)
            else:
                logger.warning(f"⚠️ 工具调用失败: {result.error}")
                return f"工具调用失败: {result.error}"
        
        except Exception as e:
            logger.error(f"❌ 异步工具调用失败: {e}")
            return f"工具调用异常: {str(e)}"

class HTTPMCPLangChainIntegration:
    """HTTP MCP与LangChain的集成类"""
    
    def __init__(self, server_url: str = "http://localhost:8000", timeout: int = 30):
        """
        初始化HTTP MCP LangChain集成
        
        Args:
            server_url: MCP服务器URL
            timeout: 请求超时时间
        """
        self.server_url = server_url
        self.timeout = timeout
        self.mcp_client = HTTPMCPClient(server_url, timeout)
        self.tools: List[HTTPMCPTool] = []
        self._connected = False
    
    async def connect(self):
        """连接到HTTP MCP服务器"""
        try:
            await self.mcp_client.connect()
            self._connected = True
            logger.info(f"✅ 成功连接到HTTP MCP服务器: {self.server_url}")
            
            # 获取并创建工具
            await self._load_tools()
            
        except Exception as e:
            logger.error(f"❌ 连接HTTP MCP服务器失败: {e}")
            raise
    
    async def disconnect(self):
        """断开连接"""
        if self._connected:
            await self.mcp_client.disconnect()
            self._connected = False
            self.tools.clear()
            logger.info("🔌 已断开HTTP MCP连接")
    
    async def _load_tools(self):
        """加载MCP工具并转换为LangChain工具"""
        try:
            # 获取MCP工具列表
            mcp_tools = await self.mcp_client.list_tools()
            
            # 转换为LangChain工具
            self.tools = []
            for tool_info in mcp_tools:
                langchain_tool = HTTPMCPTool(self.mcp_client, tool_info)
                self.tools.append(langchain_tool)
                logger.info(f"🔧 加载工具: {tool_info.name}")
            
            logger.info(f"📋 成功加载 {len(self.tools)} 个工具")
            
        except Exception as e:
            logger.error(f"❌ 加载工具失败: {e}")
            raise
    
    def get_tools(self) -> List[HTTPMCPTool]:
        """获取所有可用的LangChain工具"""
        if not self._connected:
            raise Exception("未连接到MCP服务器，请先调用 connect()")
        return self.tools
    
    def get_tool_by_name(self, name: str) -> Optional[HTTPMCPTool]:
        """根据名称获取工具"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    async def call_tool_directly(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """直接调用MCP工具（不通过LangChain）"""
        if not self._connected:
            raise Exception("未连接到MCP服务器，请先调用 connect()")
        
        return await self.mcp_client.call_tool(tool_name, arguments)
    
    def create_agent(self, llm, system_message: str = None) -> AgentExecutor:
        """创建使用HTTP MCP工具的LangChain代理"""
        if not self._connected:
            raise Exception("未连接到MCP服务器，请先调用 connect()")
        
        if not system_message:
            system_message = """
你是一个有用的AI助手，可以使用以下工具来帮助用户：

可用工具：
- read_file: 读取文件内容
- write_file: 写入文件内容  
- list_files: 列出目录中的文件

请根据用户的需求选择合适的工具来完成任务。
"""
        
        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # 创建代理
        agent = create_openai_functions_agent(
            llm=llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # 创建代理执行器
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )
        
        return agent_executor

# 异步上下文管理器
class AsyncHTTPMCPLangChainIntegration:
    """异步上下文管理器版本的HTTP MCP LangChain集成"""
    
    def __init__(self, server_url: str = "http://localhost:8000", timeout: int = 30):
        self.integration = HTTPMCPLangChainIntegration(server_url, timeout)
    
    async def __aenter__(self):
        await self.integration.connect()
        return self.integration
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.integration.disconnect()

# 便捷函数
async def create_http_mcp_tools(server_url: str = "http://localhost:8000") -> List[HTTPMCPTool]:
    """创建HTTP MCP工具的便捷函数"""
    async with AsyncHTTPMCPLangChainIntegration(server_url) as integration:
        return integration.get_tools()

# 示例使用
async def main():
    """示例：如何使用HTTP MCP LangChain集成"""
    print("🚀 HTTP MCP LangChain集成示例")
    
    # 使用异步上下文管理器
    async with AsyncHTTPMCPLangChainIntegration("http://localhost:8000") as integration:
        
        # 获取工具列表
        tools = integration.get_tools()
        print(f"\n🔧 可用工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # 直接调用工具测试
        print("\n📝 测试直接工具调用:")
        
        # 写入文件
        write_result = await integration.call_tool_directly(
            "write_file", 
            {
                "file_path": "test_http_langchain.txt",
                "content": "这是通过HTTP MCP LangChain集成写入的测试内容"
            }
        )
        print(f"✍️ 写入结果: {write_result.result if write_result.success else write_result.error}")
        
        # 读取文件
        read_result = await integration.call_tool_directly(
            "read_file", 
            {"file_path": "test_http_langchain.txt"}
        )
        print(f"📖 读取结果: {read_result.result if read_result.success else read_result.error}")
        
        # 测试LangChain工具调用
        print("\n🔗 测试LangChain工具调用:")
        read_tool = integration.get_tool_by_name("read_file")
        if read_tool:
            result = await read_tool._arun({"file_path": "test_http_langchain.txt"})
            print(f"📖 LangChain工具结果: {result}")
        
        print("\n✅ HTTP MCP LangChain集成测试完成")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())