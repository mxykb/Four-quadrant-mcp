# LangChain处理模块
# 包含所有LangChain相关的工具定义和聊天处理逻辑

import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import os
import json
from pathlib import Path

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
except ImportError:
    print("⚠️  LangChain未安装，聊天功能将不可用")
    print("💡 安装命令: pip install langchain langchain-openai")
    LANGCHAIN_AVAILABLE = False

# 响应模型定义
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

# LangChain工具定义（仅在LangChain可用时定义）
if LANGCHAIN_AVAILABLE:
    @tool
    def read_file_tool(file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取文件失败: {str(e)}"
    
    @tool
    def write_file_tool(file_path: str, content: str) -> str:
        """写入文件内容"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"文件写入成功: {file_path}"
        except Exception as e:
            return f"写入文件失败: {str(e)}"
    
    @tool
    def list_files_tool(directory_path: str) -> str:
        """列出目录中的文件"""
        try:
            files = os.listdir(directory_path)
            return json.dumps(files, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"列出文件失败: {str(e)}"
    
    # LangChain工具列表
    LANGCHAIN_TOOLS = [read_file_tool, write_file_tool, list_files_tool]
    
    async def chat_with_langchain(message: str, api_key: str = None, deepseek_api_key: str = None, 
                                model: str = "gpt-3.5-turbo", temperature: float = 0.7, max_tokens: int = 1000) -> dict:
        """使用LangChain处理聊天请求"""
        try:
            logger.info(f"🤖 开始LangChain聊天处理 - 模型: {model}")
            
            # 判断是否为DeepSeek模型
            is_deepseek = model.startswith('deepseek')
            
            if is_deepseek and deepseek_api_key:
                # DeepSeek模型处理
                logger.info("🔥 使用DeepSeek模型进行聊天")
                
                # 配置DeepSeek模型
                llm = ChatOpenAI(
                    model=model,
                    api_key=deepseek_api_key,
                    base_url="https://api.deepseek.com",
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # 创建消息
                messages = [
                    SystemMessage(content="你是一个有用的AI助手，可以使用工具来帮助用户完成任务。"),
                    HumanMessage(content=message)
                ]
                
                # 绑定工具到模型
                llm_with_tools = llm.bind_tools(LANGCHAIN_TOOLS)
                
                # 调用模型
                response = await llm_with_tools.ainvoke(messages)
                
                # 处理工具调用
                tool_calls = []
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"🔧 检测到 {len(response.tool_calls)} 个工具调用")
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']
                        
                        logger.info(f"🛠️  执行工具: {tool_name}")
                        
                        # 执行工具
                        if tool_name == 'read_file_tool':
                            tool_result = read_file_tool.invoke(tool_args)
                        elif tool_name == 'write_file_tool':
                            tool_result = write_file_tool.invoke(tool_args)
                        elif tool_name == 'list_files_tool':
                            tool_result = list_files_tool.invoke(tool_args)
                        else:
                            tool_result = f"未知工具: {tool_name}"
                        
                        tool_calls.append({
                            "tool_name": tool_name,
                            "arguments": tool_args,
                            "result": str(tool_result)
                        })
                        
                    # 构建工具消息列表
                    tool_messages = []
                    for i, tool_call in enumerate(response.tool_calls):
                        # 获取对应的工具执行结果
                        if i < len(tool_calls):
                            tool_result = tool_calls[i]["result"]
                            tool_messages.append(ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call['id']
                            ))
                    
                    # 如果有工具调用，再次调用模型获取最终响应
                    if tool_calls:
                        # 正确的消息序列：原始消息 + AI响应 + 工具消息
                        final_messages = messages + [response] + tool_messages
                        final_response = await llm.ainvoke(final_messages)
                        result = {
                            "success": True,
                            "error": None,
                            "result": final_response.content,
                            "tool_calls": tool_calls,
                            "model_used": model
                        }
                    else:
                        result = {
                            "success": True,
                            "error": None,
                            "result": response.content,
                            "tool_calls": [],
                            "model_used": model
                        }
                # 如果没有工具调用，直接返回响应
                else:
                    result = {
                        "success": True,
                        "error": None,
                        "result": response.content,
                        "tool_calls": [],
                        "model_used": model
                    }
                
                # 返回DeepSeek处理结果
                return result
                
            else:
                 # OpenAI模型使用Functions Agent
                 system_prompt = ChatPromptTemplate.from_messages([
                     ("system", "你是一个有用的AI助手，可以使用以下工具来帮助用户：\n"
                               "1. read_file: 读取文件内容\n"
                               "2. write_file: 写入文件内容\n"
                               "3. list_files: 列出目录中的文件\n\n"
                               "当用户需要文件操作时，请主动使用相应的工具。"
                               "例如，当用户要求创建文件时，使用write_file工具。"),
                     ("human", "{input}"),
                     ("placeholder", "{agent_scratchpad}")
                 ])
                 
                 # 配置OpenAI模型
                 llm = ChatOpenAI(
                     model=model,
                     api_key=api_key,
                     temperature=temperature,
                     max_tokens=max_tokens
                 )
                 
                 agent = create_openai_functions_agent(llm, LANGCHAIN_TOOLS, system_prompt)
                 agent_executor = AgentExecutor(agent=agent, tools=LANGCHAIN_TOOLS, verbose=True)
                 
                 # 执行Agent
                 result = await agent_executor.ainvoke({"input": message})
                 
                 # 提取工具调用信息
                 tool_calls = []
                 if 'intermediate_steps' in result:
                     for step in result['intermediate_steps']:
                         if len(step) >= 2:
                             action, observation = step[0], step[1]
                             tool_calls.append({
                                 "tool_name": action.tool,
                                 "arguments": action.tool_input,
                                 "result": str(observation)
                             })
                 
                 return {
                     "success": True,
                     "error": None,
                     "result": result['output'],
                     "tool_calls": tool_calls,
                     "model_used": model
                 }
            
        except Exception as e:
            logger.error(f"❌ LangChain处理错误: {str(e)}")
            return {
                "success": False,
                "error": f"LangChain处理错误: {str(e)}",
                "result": None,
                "tool_calls": []
            }
else:
    # LangChain不可用时的占位符函数
    async def chat_with_langchain(message: str, api_key: str, model: str = "gpt-3.5-turbo", 
                                temperature: float = 0.7, max_tokens: int = 1000) -> ChatResponse:
        return ChatResponse(
            success=False,
            error="LangChain未安装，请先安装: pip install langchain langchain-openai"
        )
    
    # 空的工具列表
    LANGCHAIN_TOOLS = []

# 导出的函数和变量
__all__ = ['chat_with_langchain', 'LANGCHAIN_TOOLS', 'LANGCHAIN_AVAILABLE', 'ChatResponse', 'ToolCall']