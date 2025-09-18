#!/usr/bin/env python3
"""
MCP 工具处理器
包含所有MCP工具的实现和管理
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from models import (
    ToolInfo, ToolCallRequest, ToolCallResponse, FileOperation,
    FileReadRequest, FileWriteRequest, FileListRequest
)
from config import config_manager

# 配置日志
logger = logging.getLogger("Tools")

class ToolExecutor:
    """工具执行器基类"""
    
    def __init__(self, name: str, description: str, schema: Dict[str, Any]):
        """
        初始化工具执行器
        
        Args:
            name: 工具名称
            description: 工具描述
            schema: 工具输入模式
        """
        self.name = name
        self.description = description
        self.schema = schema
        self.stats = {
            "call_count": 0,
            "success_count": 0,
            "error_count": 0,
            "last_used": None
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolCallResponse:
        """
        执行工具
        
        Args:
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        self.stats["call_count"] += 1
        self.stats["last_used"] = datetime.now().timestamp()
        
        try:
            result = await self._execute_impl(arguments)
            self.stats["success_count"] += 1
            return ToolCallResponse(success=True, result=result)
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"❌ 工具 {self.name} 执行失败: {str(e)}")
            return ToolCallResponse(success=False, error=str(e))
    
    async def _execute_impl(self, arguments: Dict[str, Any]) -> Any:
        """工具具体实现，子类需要重写"""
        raise NotImplementedError
    
    def get_info(self) -> ToolInfo:
        """获取工具信息"""
        return ToolInfo(
            name=self.name,
            description=self.description,
            inputSchema=self.schema
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        return self.stats.copy()


class FileReadTool(ToolExecutor):
    """文件读取工具"""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取文件内容",
            schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要读取的文件路径"
                    }
                },
                "required": ["file_path"]
            }
        )
    
    async def _execute_impl(self, arguments: Dict[str, Any]) -> str:
        """读取文件实现"""
        file_path = arguments.get("file_path")
        if not file_path:
            raise ValueError("缺少 file_path 参数")
        
        # 安全性检查
        file_path = self._validate_file_path(file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"路径不是文件: {file_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        max_size = config_manager.get("tools.file_operations.max_file_size", 10485760)
        if file_size > max_size:
            raise ValueError(f"文件过大: {file_size} 字节 (最大: {max_size} 字节)")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"✅ 成功读取文件: {file_path} ({file_size} 字节)")
            return f"文件 {file_path} 的内容:\n{content}"
        
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"✅ 成功读取文件 (编码: {encoding}): {file_path}")
                    return f"文件 {file_path} 的内容 (编码: {encoding}):\n{content}"
                except UnicodeDecodeError:
                    continue
            
            raise ValueError(f"无法解码文件: {file_path}")
    
    def _validate_file_path(self, file_path: str) -> str:
        """验证和标准化文件路径"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        
        # 获取基础目录
        base_dir = os.path.abspath(config_manager.get("tools.file_operations.base_directory", "."))
        
        # 确保文件在允许的目录内
        if not abs_path.startswith(base_dir):
            raise ValueError(f"文件路径超出允许范围: {file_path}")
        
        return abs_path


class FileWriteTool(ToolExecutor):
    """文件写入工具"""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            description="写入文件内容。参数：file_path（文件路径）、content（文件内容）",
            schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要写入的文件路径，例如：hello.txt"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容文本"
                    }
                },
                "required": ["file_path", "content"]
            }
        )
    
    async def _execute_impl(self, arguments: Dict[str, Any]) -> str:
        """写入文件实现"""
        file_path = arguments.get("file_path")
        content = arguments.get("content")
        
        if not file_path:
            raise ValueError("缺少 file_path 参数")
        
        if content is None:
            raise ValueError("缺少 content 参数")
        
        # 安全性检查
        file_path = self._validate_file_path(file_path)
        
        # 检查文件扩展名
        self._validate_file_extension(file_path)
        
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            if config_manager.get("tools.file_operations.create_directories", True):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"📁 创建目录: {dir_path}")
            else:
                raise ValueError(f"目录不存在: {dir_path}")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = len(content.encode('utf-8'))
            logger.info(f"✅ 成功写入文件: {file_path} ({file_size} 字节)")
            return f"成功写入文件: {file_path}"
        
        except Exception as e:
            raise ValueError(f"写入文件失败: {str(e)}")
    
    def _validate_file_path(self, file_path: str) -> str:
        """验证和标准化文件路径"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        
        # 获取基础目录
        base_dir = os.path.abspath(config_manager.get("tools.file_operations.base_directory", "."))
        
        # 确保文件在允许的目录内
        if not abs_path.startswith(base_dir):
            raise ValueError(f"文件路径超出允许范围: {file_path}")
        
        return abs_path
    
    def _validate_file_extension(self, file_path: str):
        """验证文件扩展名"""
        allowed_extensions = config_manager.get("tools.file_operations.allowed_extensions", [])
        
        if not allowed_extensions:
            return  # 如果没有限制，允许所有扩展名
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"不支持的文件扩展名: {file_ext}. 支持的扩展名: {allowed_extensions}")


class FileListTool(ToolExecutor):
    """文件列表工具"""
    
    def __init__(self):
        super().__init__(
            name="list_files",
            description="列出目录中的文件",
            schema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "要列出文件的目录路径"
                    }
                },
                "required": ["directory_path"]
            }
        )
    
    async def _execute_impl(self, arguments: Dict[str, Any]) -> str:
        """列出文件实现"""
        directory_path = arguments.get("directory_path")
        if not directory_path:
            raise ValueError("缺少 directory_path 参数")
        
        # 安全性检查
        directory_path = self._validate_directory_path(directory_path)
        
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise ValueError(f"路径不是目录: {directory_path}")
        
        try:
            items = []
            total_files = 0
            total_dirs = 0
            
            for item in sorted(os.listdir(directory_path)):
                item_path = os.path.join(directory_path, item)
                
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    items.append(f"📄 {item} ({size} 字节)")
                    total_files += 1
                elif os.path.isdir(item_path):
                    items.append(f"📁 {item}/")
                    total_dirs += 1
                else:
                    items.append(f"❓ {item}")
            
            if not items:
                result = f"目录 {directory_path} 为空"
            else:
                result = f"目录 {directory_path} 的内容 (共 {total_files} 个文件, {total_dirs} 个目录):\n"
                result += "\n".join(items)
            
            logger.info(f"✅ 成功列出目录: {directory_path} ({total_files} 文件, {total_dirs} 目录)")
            return result
        
        except Exception as e:
            raise ValueError(f"列出目录失败: {str(e)}")
    
    def _validate_directory_path(self, directory_path: str) -> str:
        """验证和标准化目录路径"""
        # 转换为绝对路径
        abs_path = os.path.abspath(directory_path)
        
        # 获取基础目录
        base_dir = os.path.abspath(config_manager.get("tools.file_operations.base_directory", "."))
        
        # 确保目录在允许的范围内
        if not abs_path.startswith(base_dir):
            raise ValueError(f"目录路径超出允许范围: {directory_path}")
        
        return abs_path


class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, ToolExecutor] = {}
        self._register_default_tools()
        logger.info(f"🔧 工具管理器初始化完成，注册了 {len(self.tools)} 个工具")
    
    def _register_default_tools(self):
        """注册默认工具"""
        default_tools = [
            FileReadTool(),
            FileWriteTool(),
            FileListTool()
        ]
        
        for tool in default_tools:
            if config_manager.is_tool_enabled(tool.name):
                self.register_tool(tool)
            else:
                logger.info(f"⚠️ 工具 {tool.name} 被禁用")
    
    def register_tool(self, tool: ToolExecutor):
        """
        注册工具
        
        Args:
            tool: 工具执行器
        """
        self.tools[tool.name] = tool
        logger.info(f"✅ 注册工具: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """
        注销工具
        
        Args:
            tool_name: 工具名称
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"🗑️ 注销工具: {tool_name}")
        else:
            logger.warning(f"⚠️ 尝试注销不存在的工具: {tool_name}")
    
    def list_tools(self) -> List[ToolInfo]:
        """获取所有工具信息"""
        return [tool.get_info() for tool in self.tools.values()]
    
    def get_tool(self, tool_name: str) -> Optional[ToolExecutor]:
        """
        获取工具执行器
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具执行器，如果不存在则返回None
        """
        return self.tools.get(tool_name)
    
    async def execute_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """
        执行工具
        
        Args:
            request: 工具调用请求
            
        Returns:
            工具执行结果
        """
        tool_name = request.name
        arguments = request.arguments
        
        logger.info(f"🔧 执行工具: {tool_name}")
        logger.debug(f"📝 工具参数: {arguments}")
        
        # 检查工具是否存在
        tool = self.get_tool(tool_name)
        if not tool:
            logger.warning(f"⚠️ 工具不存在: {tool_name}")
            available_tools = list(self.tools.keys())
            return ToolCallResponse(
                success=False,
                error=f"工具 '{tool_name}' 不存在。可用工具: {available_tools}"
            )
        
        # 执行工具
        start_time = datetime.now()
        result = await tool.execute(arguments)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 记录执行结果
        if result.success:
            logger.info(f"✅ 工具执行成功: {tool_name} (耗时: {execution_time:.3f}秒)")
        else:
            logger.error(f"❌ 工具执行失败: {tool_name} - {result.error}")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有工具的统计信息"""
        stats = {}
        for tool_name, tool in self.tools.items():
            stats[tool_name] = tool.get_stats()
        return stats
    
    def reset_stats(self):
        """重置所有工具的统计信息"""
        for tool in self.tools.values():
            tool.stats = {
                "call_count": 0,
                "success_count": 0,
                "error_count": 0,
                "last_used": None
            }
        logger.info("🔄 已重置所有工具统计信息")


# 全局工具管理器实例
tool_manager = ToolManager()

# 便捷函数
async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> ToolCallResponse:
    """执行工具的便捷函数"""
    request = ToolCallRequest(name=tool_name, arguments=arguments)
    return await tool_manager.execute_tool(request)

def list_tools() -> List[ToolInfo]:
    """列出所有工具的便捷函数"""
    return tool_manager.list_tools()

def get_tool_stats() -> Dict[str, Any]:
    """获取工具统计的便捷函数"""
    return tool_manager.get_stats()

# 导出
__all__ = [
    "ToolExecutor", "FileReadTool", "FileWriteTool", "FileListTool",
    "ToolManager", "tool_manager",
    "execute_tool", "list_tools", "get_tool_stats"
]
