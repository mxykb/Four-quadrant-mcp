#!/usr/bin/env python3
"""
四象限MCP服务器 - 测试脚本
测试Android连接和各项功能
"""

import asyncio
import json
import time
from mcp_server import AndroidBridge, format_response

async def test_android_connection():
    """测试Android设备连接"""
    print("🔗 测试Android设备连接...")
    
    bridge = AndroidBridge()
    
    # 测试ping连接
    try:
        result = await bridge.call_android_api("ping")
        if result.get("success"):
            print("✅ Android设备连接正常")
            return True
        else:
            print("❌ Android设备连接失败:", result.get("message"))
            return False
    except Exception as e:
        print(f"❗ 连接测试异常: {str(e)}")
        return False

async def test_pomodoro_features():
    """测试番茄钟功能"""
    print("\n🍅 测试番茄钟功能...")
    
    bridge = AndroidBridge()
    
    # 测试启动番茄钟
    print("1. 测试启动番茄钟...")
    result = await bridge.call_android_api("start_pomodoro", {
        "task_name": "测试任务",
        "duration": 25,
        "task_id": "test_001"
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 测试控制番茄钟
    print("2. 测试查询番茄钟状态...")
    result = await bridge.call_android_api("control_pomodoro", {
        "action": "status"
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 测试暂停番茄钟
    print("3. 测试暂停番茄钟...")
    result = await bridge.call_android_api("control_pomodoro", {
        "action": "pause",
        "reason": "测试暂停"
    })
    print(f"   结果: {result.get('message', '未知')}")

async def test_task_management():
    """测试任务管理功能"""
    print("\n📋 测试任务管理功能...")
    
    bridge = AndroidBridge()
    
    # 测试创建任务
    print("1. 测试创建任务...")
    task_data = {
        "name": "学习Python编程",
        "description": "完成MCP服务器开发",
        "importance": 4,
        "urgency": 3,
        "due_date": "2024-01-15",
        "estimated_pomodoros": 3
    }
    result = await bridge.call_android_api("manage_tasks", {
        "action": "create",
        "task_data": task_data
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 获取任务ID（如果创建成功）
    task_id = None
    if result.get("success") and result.get("data"):
        task_id = result["data"].get("id")
    
    # 测试获取任务列表
    print("2. 测试获取任务列表...")
    result = await bridge.call_android_api("manage_tasks", {
        "action": "list"
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 测试完成任务（如果有task_id）
    if task_id:
        print("3. 测试完成任务...")
        result = await bridge.call_android_api("manage_tasks", {
            "action": "complete",
            "task_id": task_id
        })
        print(f"   结果: {result.get('message', '未知')}")

async def test_statistics():
    """测试统计功能"""
    print("\n📊 测试统计功能...")
    
    bridge = AndroidBridge()
    
    # 测试总体统计
    print("1. 测试总体统计...")
    result = await bridge.call_android_api("get_statistics", {
        "type": "general"
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 测试番茄钟统计
    print("2. 测试番茄钟统计...")
    result = await bridge.call_android_api("get_statistics", {
        "type": "pomodoro",
        "period": "weekly"
    })
    print(f"   结果: {result.get('message', '未知')}")

async def test_settings():
    """测试设置功能"""
    print("\n⚙️ 测试设置功能...")
    
    bridge = AndroidBridge()
    
    # 测试更新设置
    print("1. 测试更新设置...")
    settings = {
        "dark_mode": True,
        "tomato_duration": 30,
        "break_duration": 10,
        "notification_enabled": True
    }
    result = await bridge.call_android_api("update_settings", settings)
    print(f"   结果: {result.get('message', '未知')}")

async def test_break_management():
    """测试休息管理功能"""
    print("\n☕ 测试休息管理功能...")
    
    bridge = AndroidBridge()
    
    # 测试开始休息
    print("1. 测试开始休息...")
    result = await bridge.call_android_api("manage_break", {
        "action": "start"
    })
    print(f"   结果: {result.get('message', '未知')}")
    
    # 等待一秒
    await asyncio.sleep(1)
    
    # 测试跳过休息
    print("2. 测试跳过休息...")
    result = await bridge.call_android_api("manage_break", {
        "action": "skip"
    })
    print(f"   结果: {result.get('message', '未知')}")

async def test_status_check():
    """测试状态检查功能"""
    print("\n📱 测试状态检查功能...")
    
    bridge = AndroidBridge()
    
    result = await bridge.call_android_api("check_status")
    print(f"   结果: {result.get('message', '未知')}")
    
    if result.get("data"):
        print("   详细信息:")
        data = result["data"]
        for key, value in data.items():
            print(f"     {key}: {value}")

async def run_performance_test():
    """运行性能测试"""
    print("\n⚡ 运行性能测试...")
    
    bridge = AndroidBridge()
    
    # 测试并发请求
    start_time = time.time()
    tasks = []
    
    for i in range(5):
        task = bridge.call_android_api("ping")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    
    print(f"   并发请求测试: {success_count}/5 成功")
    print(f"   总耗时: {end_time - start_time:.2f}秒")
    print(f"   平均响应时间: {(end_time - start_time) / 5:.2f}秒")

async def main():
    """主测试函数"""
    print("🚀 四象限MCP服务器测试开始...")
    print("=" * 50)
    
    # 首先测试连接
    connection_ok = await test_android_connection()
    
    if not connection_ok:
        print("\n❌ Android设备连接失败，无法进行功能测试")
        print("请确保:")
        print("1. Android设备与PC在同一WiFi网络中")
        print("2. Android HTTP服务器已启动（端口8080）")
        print("3. config.json中的IP地址配置正确")
        return
    
    print("✅ 连接测试通过，开始功能测试...")
    
    # 运行各项功能测试
    try:
        await test_pomodoro_features()
        await test_task_management()
        await test_statistics()
        await test_settings()
        await test_break_management()
        await test_status_check()
        await run_performance_test()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试完成！")
        
    except Exception as e:
        print(f"\n❗ 测试过程中发生错误: {str(e)}")
        print("请检查Android服务器状态和网络连接")

async def interactive_test():
    """交互式测试模式"""
    print("🎮 进入交互式测试模式...")
    print("可用命令:")
    print("1. ping - 测试连接")
    print("2. pomodoro - 测试番茄钟")
    print("3. tasks - 测试任务管理")
    print("4. stats - 测试统计")
    print("5. settings - 测试设置")
    print("6. break - 测试休息")
    print("7. status - 测试状态")
    print("8. exit - 退出")
    
    bridge = AndroidBridge()
    
    while True:
        try:
            command = input("\n请输入命令: ").strip().lower()
            
            if command == "exit":
                print("👋 退出测试模式")
                break
            elif command == "ping":
                result = await bridge.call_android_api("ping")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "pomodoro":
                result = await bridge.call_android_api("start_pomodoro", {
                    "task_name": "交互测试任务",
                    "duration": 25
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "tasks":
                result = await bridge.call_android_api("manage_tasks", {
                    "action": "list"
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "stats":
                result = await bridge.call_android_api("get_statistics", {
                    "type": "general"
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "settings":
                result = await bridge.call_android_api("update_settings", {
                    "notification_enabled": True
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "break":
                result = await bridge.call_android_api("manage_break", {
                    "action": "start"
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif command == "status":
                result = await bridge.call_android_api("check_status")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("❌ 未知命令，请重新输入")
                
        except KeyboardInterrupt:
            print("\n👋 退出测试模式")
            break
        except Exception as e:
            print(f"❗ 执行命令时发生错误: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(main())
