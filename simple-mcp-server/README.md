# 简单MCP服务器示例

这是一个简单的MCP (Model Context Protocol) 服务器示例，提供基本的文件操作功能。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r simple_requirements.txt
```

### 2. 启动服务器

**Windows:**
```bash
# 双击运行
start_simple_server.bat

# 或命令行运行
python simple_mcp_server.py
```

**Linux/Mac:**
```bash
python3 simple_mcp_server.py
```

## 🛠️ 可用工具

### 1. read_file - 读取文件
- **功能**: 读取指定文本文件的内容
- **参数**: 
  - `file_path` (必需): 文件路径

### 2. write_file - 写入文件
- **功能**: 写入内容到文件（覆盖原内容）
- **参数**: 
  - `file_path` (必需): 文件路径
  - `content` (必需): 要写入的内容

### 3. append_file - 追加文件
- **功能**: 在文件末尾追加内容
- **参数**: 
  - `file_path` (必需): 文件路径
  - `content` (必需): 要追加的内容

### 4. list_files - 列出文件
- **功能**: 列出指定目录下的文件和文件夹
- **参数**: 
  - `directory_path` (可选): 目录路径，默认为当前目录

## 📝 使用示例

### 测试文件操作

1. **读取测试文件**:
   ```
   工具: read_file
   参数: {"file_path": "test_example.txt"}
   ```

2. **写入新内容**:
   ```
   工具: write_file
   参数: {
     "file_path": "my_note.txt",
     "content": "这是我的第一个笔记\n今天学习了MCP协议"
   }
   ```

3. **追加内容**:
   ```
   工具: append_file
   参数: {
     "file_path": "my_note.txt",
     "content": "\n\n补充：MCP很有趣！"
   }
   ```

4. **列出当前目录文件**:
   ```
   工具: list_files
   参数: {"directory_path": "."}
   ```

## 🔧 技术细节

### MCP协议组件
- **Server**: MCP服务器实例
- **@server.list_tools()**: 注册工具列表
- **@server.call_tool()**: 处理工具调用
- **stdio_server**: 通过标准输入输出通信

### 错误处理
- 文件不存在检查
- 目录自动创建
- 编码处理 (UTF-8)
- 异常捕获和友好错误信息

## 🎯 学习要点

1. **MCP基础架构**: 了解Server、Tool、CallToolResult等核心组件
2. **工具定义**: 学习如何定义工具的inputSchema
3. **异步编程**: 所有函数都是async/await模式
4. **错误处理**: 完善的异常处理和用户友好的错误信息
5. **标准化响应**: 统一的成功/失败响应格式

## 📁 文件结构
```
├── simple_mcp_server.py      # 主服务器文件
├── simple_requirements.txt   # 依赖包列表
├── start_simple_server.bat   # Windows启动脚本
├── test_example.txt          # 测试文件
└── SIMPLE_MCP_README.md      # 说明文档
```

## 🔄 扩展建议

你可以基于这个示例添加更多功能：
- 文件删除、重命名
- 目录操作
- 文件搜索
- JSON/CSV文件处理
- 图片文件信息获取
- 网络文件下载

开始你的MCP之旅吧！🎉