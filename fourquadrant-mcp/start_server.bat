@echo off
chcp 65001 > nul
echo ========================================
echo 🚀 四象限MCP服务器启动脚本 (Windows)
echo ========================================

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python环境检测正常

REM 检查是否在正确目录
if not exist "mcp_server.py" (
    echo ❌ 错误: 未找到mcp_server.py文件
    echo 请确保在fourquadrant-mcp目录中运行此脚本
    pause
    exit /b 1
)

echo ✅ 项目文件检测正常

REM 检查并安装依赖
echo 📦 检查依赖包...
pip install -r requirements.txt --quiet

if %errorlevel% neq 0 (
    echo ⚠️  依赖安装可能有问题，继续尝试启动...
) else (
    echo ✅ 依赖包检查完成
)

REM 检查配置文件
if not exist "config.json" (
    echo ⚠️  警告: 未找到config.json配置文件，将使用默认配置
    echo 💡 建议创建config.json文件并配置正确的Android设备IP地址
)

echo.
echo 🔗 准备启动MCP服务器...
echo 💡 提示:
echo    - 确保Android设备已启动HTTP服务器（端口8080）
echo    - 确保PC和Android设备在同一WiFi网络中
echo    - 可以通过Ctrl+C停止服务器
echo.

REM 启动MCP服务器
echo 🍅 启动四象限MCP服务器...
python mcp_server.py

REM 如果程序意外退出
if %errorlevel% neq 0 (
    echo.
    echo ❌ 服务器启动失败，错误代码: %errorlevel%
    echo 🔧 故障排除建议:
    echo    1. 检查Python环境和依赖包
    echo    2. 检查config.json配置文件
    echo    3. 检查Android设备网络连接
    echo    4. 查看日志文件fourquadrant_mcp.log
) else (
    echo.
    echo 👋 MCP服务器已正常退出
)

echo.
echo 按任意键退出...
pause > nul
