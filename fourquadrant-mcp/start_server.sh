#!/bin/bash

# 四象限MCP服务器启动脚本 (Linux/macOS)

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo -e "🚀 四象限MCP服务器启动脚本 (Linux/macOS)"
echo "========================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ 错误: 未检测到Python，请先安装Python 3.8+${NC}"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}✅ Python环境检测正常${NC}"

# 检查是否在正确目录
if [[ ! -f "mcp_server.py" ]]; then
    echo -e "${RED}❌ 错误: 未找到mcp_server.py文件${NC}"
    echo "请确保在fourquadrant-mcp目录中运行此脚本"
    exit 1
fi

echo -e "${GREEN}✅ 项目文件检测正常${NC}"

# 检查pip是否可用
if ! command -v pip3 &> /dev/null; then
    if ! command -v pip &> /dev/null; then
        echo -e "${YELLOW}⚠️  警告: 未检测到pip，跳过依赖检查${NC}"
        PIP_CMD=""
    else
        PIP_CMD="pip"
    fi
else
    PIP_CMD="pip3"
fi

# 检查并安装依赖
if [[ -n "$PIP_CMD" ]]; then
    echo "📦 检查依赖包..."
    $PIP_CMD install -r requirements.txt --quiet
    
    if [[ $? -ne 0 ]]; then
        echo -e "${YELLOW}⚠️  依赖安装可能有问题，继续尝试启动...${NC}"
    else
        echo -e "${GREEN}✅ 依赖包检查完成${NC}"
    fi
fi

# 检查配置文件
if [[ ! -f "config.json" ]]; then
    echo -e "${YELLOW}⚠️  警告: 未找到config.json配置文件，将使用默认配置${NC}"
    echo -e "${BLUE}💡 建议创建config.json文件并配置正确的Android设备IP地址${NC}"
fi

echo ""
echo "🔗 准备启动MCP服务器..."
echo -e "${BLUE}💡 提示:${NC}"
echo "   - 确保Android设备已启动HTTP服务器（端口8080）"
echo "   - 确保PC和Android设备在同一WiFi网络中"
echo "   - 可以通过Ctrl+C停止服务器"
echo ""

# 创建陷阱以处理Ctrl+C
trap 'echo -e "\n${YELLOW}👋 正在停止MCP服务器...${NC}"; exit 0' INT

# 启动MCP服务器
echo "🍅 启动四象限MCP服务器..."
$PYTHON_CMD mcp_server.py

# 检查退出状态
if [[ $? -ne 0 ]]; then
    echo ""
    echo -e "${RED}❌ 服务器启动失败${NC}"
    echo -e "${BLUE}🔧 故障排除建议:${NC}"
    echo "   1. 检查Python环境和依赖包"
    echo "   2. 检查config.json配置文件"
    echo "   3. 检查Android设备网络连接"
    echo "   4. 查看日志文件fourquadrant_mcp.log"
else
    echo ""
    echo -e "${GREEN}👋 MCP服务器已正常退出${NC}"
fi

echo ""
echo "按Enter键退出..."
read
