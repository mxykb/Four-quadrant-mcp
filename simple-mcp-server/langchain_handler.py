#!/usr/bin/env python3
"""
LangChain处理器 - 重构版本
负责LangChain集成、模型调用、工具绑定等功能
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from models import (
    ChatRequest, ChatResponse, ToolCall, ModelConfig, ModelProvider
)
from config import get_model_config, get_config
from tools import tool_manager

# 设置日志
logger = logging.getLogger("LangChain_Handler")

# 检查LangChain是否可用
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.agents import create_openai_functions_agent, AgentExecutor
    from langchain.tools import BaseTool
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
    logger.info("✅ LangChain已加载")
except ImportError as e:
    logger.warning(f"⚠️ LangChain未安装: {e}")
    logger.info("💡 安装命令: pip install langchain langchain-openai")
    LANGCHAIN_AVAILABLE = False


class LangChainTool:
    """LangChain工具包装器"""

    def __init__(self, tool_name: str, tool_description: str, tool_function):
        """
        初始化LangChain工具
        
        Args:
            tool_name: 工具名称
            tool_description: 工具描述
            tool_function: 工具函数
        """
        self.name = tool_name
        self.description = tool_description
        self.function = tool_function

    def invoke(self, arguments: Dict[str, Any]) -> str:
        """
        同步调用工具
        
        Args:
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 运行异步函数
            if asyncio.iscoroutinefunction(self.function):
                result = loop.run_until_complete(self.function(**arguments))
            else:
                result = self.function(**arguments)

            return str(result)
        except Exception as e:
            logger.error(f"❌ LangChain工具调用失败 {self.name}: {e}")
            return f"工具调用失败: {str(e)}"


class ModelClient:
    """模型客户端"""

    def __init__(self, config: ModelConfig):
        """
        初始化模型客户端
        
        Args:
            config: 模型配置
        """
        self.config = config
        self.client: Optional[ChatOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化模型客户端"""
        if not LANGCHAIN_AVAILABLE:
            raise Exception("LangChain不可用")

        if not self.config.api_key:
            raise Exception(f"缺少 {self.config.provider} API密钥")

        client_params = {
            "model": self.config.model_name,
            "api_key": self.config.api_key,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }

        if self.config.base_url:
            client_params["base_url"] = self.config.base_url

        self.client = ChatOpenAI(**client_params)
        logger.info(f"✅ {self.config.provider} 客户端初始化完成: {self.config.model_name}")

    def bind_tools(self, tools: List[LangChainTool]):
        """
        绑定工具到模型
        
        Args:
            tools: LangChain工具列表
            
        Returns:
            绑定工具后的模型
        """
        if not self.client:
            raise Exception("模型客户端未初始化")

        # 转换为LangChain工具
        langchain_tools = self._create_langchain_tools(tools)
        return self.client.bind_tools(langchain_tools)

    def _create_langchain_tools(self, tool_wrappers: List[LangChainTool]):
        """
        将工具包装器转换为LangChain工具
        
        Args:
            tool_wrappers: LangChain工具包装器列表
            
        Returns:
            LangChain工具列表
        """
        langchain_tools = []
        for tool_wrapper in tool_wrappers:
            # 创建工具函数，使用闭包捕获tool_wrapper
            def create_tool_func(wrapper):
                def tool_func(**kwargs):
                    return wrapper.invoke(kwargs)
                # 设置函数名和描述
                tool_func.__name__ = wrapper.name
                tool_func.__doc__ = wrapper.description
                return tool_func

            # 创建函数实例
            func = create_tool_func(tool_wrapper)

            # 使用@tool装饰器，尝试不同的格式
            try:
                # 尝试新版本的装饰器格式（只有描述）
                decorated_func = tool(func, description=tool_wrapper.description)
            except TypeError:
                try:
                    # 尝试更简单的格式
                    decorated_func = tool(tool_wrapper.description)(func)
                except TypeError:
                    # 如果都不行，使用最基本的格式
                    decorated_func = tool(func)

            # 确保工具有正确的名称和描述
            decorated_func.name = tool_wrapper.name
            decorated_func.description = tool_wrapper.description
            langchain_tools.append(decorated_func)

        return langchain_tools

    async def ainvoke(self, messages: List[Union[HumanMessage, SystemMessage, AIMessage, ToolMessage]]):
        """
        异步调用模型
        
        Args:
            messages: 消息列表
            
        Returns:
            模型响应
        """
        if not self.client:
            raise Exception("模型客户端未初始化")

        return await self.client.ainvoke(messages)


class LangChainHandler:
    """LangChain处理器"""

    def __init__(self):
        """初始化LangChain处理器"""
        self.clients: Dict[str, ModelClient] = {}
        self.tools: List[LangChainTool] = []
        self._initialize_tools()
        logger.info("🤖 LangChain处理器初始化完成")

    def _initialize_tools(self):
        """初始化工具"""
        if not LANGCHAIN_AVAILABLE:
            return

        # 从工具管理器获取可用工具
        available_tools = tool_manager.list_tools()

        for tool_info in available_tools:
            # 创建工具包装器
            async def tool_func(**kwargs):
                from tools import execute_tool
                result = await execute_tool(tool_info.name, kwargs)
                if result.success:
                    return result.result
                else:
                    raise Exception(result.error)

            tool_wrapper = LangChainTool(
                tool_name=tool_info.name,
                tool_description=tool_info.description,
                tool_function=tool_func
            )

            self.tools.append(tool_wrapper)
            logger.info(f"🔧 注册LangChain工具: {tool_info.name}")

    def _adapt_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配工具参数，处理不同模型可能使用的参数名差异
        
        Args:
            tool_name: 工具名称
            arguments: 原始参数
            
        Returns:
            适配后的参数
        """
        # 首先检查是否参数被包装在 kwargs 中
        if isinstance(arguments, dict) and len(arguments) == 1 and 'kwargs' in arguments:
            logger.info(f"🔄 检测到 kwargs 包装，提取参数")
            adapted = arguments['kwargs'].copy()
        else:
            adapted = arguments.copy()

        # write_file 工具的参数适配
        if tool_name == "write_file":
            # 可能的参数名映射
            param_mappings = {
                "path": "file_path",
                "filepath": "file_path",
                "filename": "file_path",
                "file": "file_path",
                "text": "content",
                "data": "content",
                "body": "content"
            }

            for old_key, new_key in param_mappings.items():
                if old_key in adapted and new_key not in adapted:
                    adapted[new_key] = adapted.pop(old_key)
                    logger.info(f"🔄 参数映射: {old_key} -> {new_key}")

        # read_file 工具的参数适配
        elif tool_name == "read_file":
            param_mappings = {
                "path": "file_path",
                "filepath": "file_path",
                "filename": "file_path",
                "file": "file_path"
            }

            for old_key, new_key in param_mappings.items():
                if old_key in adapted and new_key not in adapted:
                    adapted[new_key] = adapted.pop(old_key)
                    logger.info(f"🔄 参数映射: {old_key} -> {new_key}")

        # list_files 工具的参数适配
        elif tool_name == "list_files":
            param_mappings = {
                "path": "directory_path",
                "dir": "directory_path",
                "directory": "directory_path",
                "folder": "directory_path"
            }

            for old_key, new_key in param_mappings.items():
                if old_key in adapted and new_key not in adapted:
                    adapted[new_key] = adapted.pop(old_key)
                    logger.info(f"🔄 参数映射: {old_key} -> {new_key}")

        return adapted

    def _get_or_create_client(self, provider: str, api_key: str = None) -> ModelClient:
        """
        获取或创建模型客户端
        
        Args:
            provider: 模型提供商
            api_key: API密钥（可选，覆盖配置）
            
        Returns:
            模型客户端
        """
        # 创建客户端键
        client_key = f"{provider}_{hash(api_key) if api_key else 'default'}"

        if client_key not in self.clients:
            # 获取模型配置
            config = get_model_config(provider)

            # 如果提供了API密钥，覆盖配置
            if api_key:
                config.api_key = api_key

            # 创建客户端
            self.clients[client_key] = ModelClient(config)

        return self.clients[client_key]

    async def _handle_deepseek_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理DeepSeek模型聊天
        
        Args:
            request: 聊天请求
            
        Returns:
            聊天响应
        """
        logger.info("🔥 使用DeepSeek模型进行聊天")

        # 获取客户端
        client = self._get_or_create_client("deepseek", request.deepseek_api_key)

        # 创建系统消息
        system_message = SystemMessage(content=get_config(
            "langchain.system_prompt",
            "你是一个有用的AI助手，可以使用工具来帮助用户完成任务。"
        ))

        # 创建用户消息
        user_message = HumanMessage(content=request.message)
        messages = [system_message, user_message]

        # 绑定工具
        llm_with_tools = client.bind_tools(self.tools)

        # 调用模型
        response = await llm_with_tools.ainvoke(messages)

        # 处理工具调用
        tool_calls = []
        tool_messages = []

        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"🔧 检测到 {len(response.tool_calls)} 个工具调用")

            for tool_call in response.tool_calls:
                try:
                    # 提取工具信息
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_call_id = tool_call['id']

                    logger.info(f"🛠️ 执行工具: {tool_name}")
                    logger.info(f"📝 工具参数: {tool_args}")

                    # 参数适配器 - 处理可能的参数名差异
                    adapted_args = self._adapt_tool_arguments(tool_name, tool_args)
                    if adapted_args != tool_args:
                        logger.info(f"🔄 参数适配: {tool_args} -> {adapted_args}")

                    # 执行工具
                    from tools import execute_tool
                    tool_result = await execute_tool(tool_name, adapted_args)

                    if tool_result.success:
                        result_text = str(tool_result.result)
                        logger.info(f"✅ 工具执行成功: {tool_name}")
                    else:
                        result_text = f"工具执行失败: {tool_result.error}"
                        logger.error(f"❌ 工具执行失败: {tool_name} - {tool_result.error}")

                    # 记录工具调用
                    tool_calls.append(ToolCall(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=result_text
                    ))

                    # 创建工具消息
                    tool_messages.append(ToolMessage(
                        content=result_text,
                        tool_call_id=tool_call_id
                    ))

                except Exception as e:
                    logger.error(f"❌ 工具调用异常: {e}")
                    error_message = f"工具调用异常: {str(e)}"

                    tool_calls.append(ToolCall(
                        tool_name=tool_call.get('name', 'unknown'),
                        arguments=tool_call.get('args', {}),
                        result=error_message
                    ))

                    tool_messages.append(ToolMessage(
                        content=error_message,
                        tool_call_id=tool_call.get('id', 'unknown')
                    ))

            # 如果有工具调用，获取最终回复
            if tool_messages:
                try:
                    final_messages = messages + [response] + tool_messages
                    final_response = await client.ainvoke(final_messages)
                    result_content = final_response.content
                except Exception as e:
                    logger.error(f"❌ 获取最终回复失败: {e}")
                    # 使用工具执行结果作为回复
                    if tool_calls:
                        result_content = f"工具执行完成。{tool_calls[0].result}"
                    else:
                        result_content = "工具执行完成，但无法获取详细结果。"
            else:
                # 没有工具调用，直接返回
                result_content = response.content

        return ChatResponse(
            success=True,
            result=result_content,
            tool_calls=tool_calls,
            model_used=request.model
        )

    async def _handle_openai_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理OpenAI模型聊天

        Args:
            request: 聊天请求

        Returns:
            聊天响应
        """
        logger.info("🔄 使用OpenAI模型进行聊天")

        # 获取客户端
        client = self._get_or_create_client("openai", request.api_key)

        # 创建系统提示
        system_prompt = ChatPromptTemplate.from_messages([
            ("system", get_config(
                "langchain.openai_system_prompt",
                """你是一个有用的AI助手，可以使用以下工具来帮助用户：
1. read_file: 读取文件内容
2. write_file: 写入文件内容
3. list_files: 列出目录中的文件

当用户需要文件操作时，请主动使用相应的工具。
例如，当用户要求创建文件时，使用write_file工具。"""
            )),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

        # 创建Agent（需要转换工具）
        langchain_tools = client._create_langchain_tools(self.tools)
        agent = create_openai_functions_agent(client.client, langchain_tools, system_prompt)
        agent_executor = AgentExecutor(agent=agent, tools=langchain_tools, verbose=True)

                 # 执行Agent
        result = await agent_executor.ainvoke({"input": request.message})

        # 提取工具调用信息
        tool_calls = []
        if 'intermediate_steps' in result:
            for step in result['intermediate_steps']:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
        tool_calls.append(ToolCall(
            tool_name=action.tool,
            arguments=action.tool_input,
            result=str(observation)
        ))

        return ChatResponse(
            success=True,
            result=result['output'],
            tool_calls=tool_calls,
            model_used=request.model
        )

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理聊天请求

        Args:
            request: 聊天请求

        Returns:
            聊天响应
        """
        if not LANGCHAIN_AVAILABLE:
            return ChatResponse(
                success=False,
                error="LangChain未安装，请先安装: pip install langchain langchain-openai"
            )

        try:
            logger.info(f"🤖 开始LangChain聊天处理 - 模型: {request.model}")
            start_time = datetime.now()

            # 判断模型类型
            is_deepseek = request.model.startswith('deepseek')

            if is_deepseek and request.deepseek_api_key:
                response = await self._handle_deepseek_chat(request)
            elif not is_deepseek and request.api_key:
                response = await self._handle_openai_chat(request)
            else:
                missing_key = "DeepSeek" if is_deepseek else "OpenAI"
                return ChatResponse(
                    success=False,
                    error=f"缺少 {missing_key} API密钥"
                )

            # 计算处理时间
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            logger.info(f"✅ LangChain处理完成 - 成功: {response.success}, 耗时: {processing_time:.3f}秒")
            if response.tool_calls:
                logger.info(f"🔧 工具调用次数: {len(response.tool_calls)}")

            return response

        except Exception as e:
            logger.error(f"❌ LangChain处理错误: {str(e)}")
            return ChatResponse(
                success=False,
                error=f"LangChain处理错误: {str(e)}"
            )

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tools]

    def get_tool_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        from tools import get_tool_stats
        return get_tool_stats()

    def reload_tools(self):
        """重新加载工具"""
        logger.info("🔄 重新加载LangChain工具...")
        self.tools.clear()
        self._initialize_tools()


# 全局LangChain处理器实例
if LANGCHAIN_AVAILABLE:
    langchain_handler = LangChainHandler()
else:
    langchain_handler = None

# 便捷函数
async def handle_chat(request: ChatRequest) -> ChatResponse:
    """处理聊天请求的便捷函数"""
    if langchain_handler:
        return await langchain_handler.handle_chat(request)
    else:
        return ChatResponse(
            success=False,
            error="LangChain不可用"
        )

# 兼容性函数（保持向后兼容）
async def chat_with_langchain(
    message: str,
    api_key: str = None,
    deepseek_api_key: str = None,
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> dict:
    """
    兼容性函数：使用LangChain处理聊天请求
    
    Args:
        message: 用户消息
        api_key: OpenAI API密钥
        deepseek_api_key: DeepSeek API密钥
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大令牌数
        
    Returns:
        聊天响应字典
    """
    request = ChatRequest(
        message=message,
        api_key=api_key,
        deepseek_api_key=deepseek_api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )

    response = await handle_chat(request)

    # 转换为字典格式（向后兼容）
    result = {
        "success": response.success,
        "result": response.result,
        "error": response.error,
        "tool_calls": [tc.dict() for tc in response.tool_calls] if response.tool_calls else [],
        "model_used": response.model_used
    }

    return result

# 导出
__all__ = [
    "LangChainHandler", "langchain_handler", "LANGCHAIN_AVAILABLE",
    "handle_chat", "chat_with_langchain"
]
