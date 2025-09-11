#!/usr/bin/env python3
"""
简单的MCP服务器示例
提供基本的文件操作功能：读取、写入、追加文本文件
"""

import asyncio
import os
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, Tool, TextContent

# 创建MCP服务器实例
server = Server("simple-file-mcp")

# 工具列表定义
@server.list_tools()
async def list_tools() -> ListToolsResult:
    """列出所有可用的文件操作工具"""
    return ListToolsResult(
        tools=[
            Tool(
                name="read_file",
                description="📖 读取文本文件内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "要读取的文件路径"
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="write_file",
                description="✏️ 写入内容到文本文件（覆盖原内容）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "要写入的文件路径"
                        },
                        "content": {
                            "type": "string",
                            "description": "要写入的文本内容"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            ),
            Tool(
                name="append_file",
                description="➕ 追加内容到文本文件末尾",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "要追加内容的文件路径"
                        },
                        "content": {
                            "type": "string",
                            "description": "要追加的文本内容"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            ),
            Tool(
                name="list_files",
                description="📁 列出指定目录下的文件",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "要列出文件的目录路径",
                            "default": "."
                        }
                    }
                }
            )
        ]
    )

# 工具调用处理
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """处理工具调用请求"""
    
    try:
        if name == "read_file":
            file_path = arguments.get("file_path")
            
            if not file_path:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ 错误：文件路径不能为空"
                    )]
                )
            
            if not os.path.exists(file_path):
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 错误：文件不存在 - {file_path}"
                    )]
                )
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"✅ 成功读取文件 {file_path}:\n\n{content}"
                    )]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 读取文件失败：{str(e)}"
                    )]
                )
        
        elif name == "write_file":
            file_path = arguments.get("file_path")
            content = arguments.get("content")
            
            if not file_path:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ 错误：文件路径不能为空"
                    )]
                )
            
            if content is None:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ 错误：写入内容不能为空"
                    )]
                )
            
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"✅ 成功写入文件 {file_path}\n内容长度：{len(content)} 字符"
                    )]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 写入文件失败：{str(e)}"
                    )]
                )
        
        elif name == "append_file":
            file_path = arguments.get("file_path")
            content = arguments.get("content")
            
            if not file_path:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ 错误：文件路径不能为空"
                    )]
                )
            
            if content is None:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="❌ 错误：追加内容不能为空"
                    )]
                )
            
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(content)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"✅ 成功追加内容到文件 {file_path}\n追加内容长度：{len(content)} 字符"
                    )]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 追加文件失败：{str(e)}"
                    )]
                )
        
        elif name == "list_files":
            directory_path = arguments.get("directory_path", ".")
            
            if not os.path.exists(directory_path):
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 错误：目录不存在 - {directory_path}"
                    )]
                )
            
            if not os.path.isdir(directory_path):
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 错误：路径不是目录 - {directory_path}"
                    )]
                )
            
            try:
                files = os.listdir(directory_path)
                files.sort()
                
                if not files:
                    file_list = "目录为空"
                else:
                    file_list = "\n".join([f"📄 {f}" if os.path.isfile(os.path.join(directory_path, f)) 
                                         else f"📁 {f}/" for f in files])
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"📁 目录 {directory_path} 的文件列表：\n\n{file_list}"
                    )]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ 列出文件失败：{str(e)}"
                    )]
                )
        
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ 未知工具：{name}"
                )]
            )
    
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"❌ 工具调用异常：{str(e)}"
            )]
        )

async def main():
    """启动MCP服务器"""
    print("🚀 启动简单文件操作MCP服务器...")
    print("📋 可用工具：")
    print("  - read_file: 读取文件内容")
    print("  - write_file: 写入文件内容")
    print("  - append_file: 追加文件内容")
    print("  - list_files: 列出目录文件")
    print("\n等待客户端连接...")
    
    # 启动stdio服务器
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())