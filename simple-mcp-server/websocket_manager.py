#!/usr/bin/env python3
"""
WebSocket 连接管理器
负责WebSocket连接的管理、消息广播、心跳检测等
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect

from models import (
    WebSocketMessage, WebSocketChatData, WebSocketResponse, 
    MessageType, ChatRequest, ChatResponse
)
from config import config_manager

# 配置日志
logger = logging.getLogger("WebSocket_Manager")


class WebSocketConnection:
    """WebSocket连接包装器"""
    
    def __init__(self, websocket: WebSocket, client_id: str = None):
        """
        初始化WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            client_id: 客户端ID
        """
        self.websocket = websocket
        self.client_id = client_id or self._generate_client_id()
        self.connected_at = datetime.now()
        self.last_ping = None
        self.last_pong = None
        self.message_count = 0
        self.metadata: Dict[str, Any] = {}
    
    def _generate_client_id(self) -> str:
        """生成客户端ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        host = self.websocket.client.host if self.websocket.client else "unknown"
        return f"{host}_{timestamp}"
    
    async def send_message(self, message: Dict[str, Any]):
        """
        发送消息到客户端
        
        Args:
            message: 消息内容
        """
        try:
            message_str = json.dumps(message, ensure_ascii=False)
            await self.websocket.send_text(message_str)
            self.message_count += 1
            logger.debug(f"📤 发送消息到 {self.client_id}: {len(message_str)} 字符")
        except Exception as e:
            logger.error(f"❌ 发送消息失败 {self.client_id}: {e}")
            raise
    
    async def send_response(self, response_type: MessageType, data: Dict[str, Any]):
        """
        发送标准响应
        
        Args:
            response_type: 响应类型
            data: 响应数据
        """
        response = WebSocketResponse(type=response_type, data=data)
        await self.send_message(response.dict())
    
    async def send_error(self, error_message: str, error_code: str = None):
        """
        发送错误消息
        
        Args:
            error_message: 错误信息
            error_code: 错误代码
        """
        error_data = {
            "message": error_message,
            "timestamp": datetime.now().timestamp()
        }
        if error_code:
            error_data["code"] = error_code
        
        await self.send_response(MessageType.ERROR, error_data)
    
    def is_alive(self) -> bool:
        """检查连接是否活跃"""
        if not self.last_ping:
            return True  # 如果没有ping记录，假设连接正常
        
        # 检查心跳超时
        heartbeat_timeout = config_manager.get("websocket.heartbeat_timeout", 60)
        time_since_ping = (datetime.now() - self.last_ping).total_seconds()
        return time_since_ping < heartbeat_timeout
    
    def get_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        uptime = (datetime.now() - self.connected_at).total_seconds()
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "uptime": uptime,
            "message_count": self.message_count,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "last_pong": self.last_pong.isoformat() if self.last_pong else None,
            "is_alive": self.is_alive(),
            "metadata": self.metadata
        }


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化WebSocket管理器"""
        self.connections: Dict[str, WebSocketConnection] = {}
        self.max_connections = config_manager.get("websocket.max_connections", 100)
        self.heartbeat_interval = config_manager.get("websocket.heartbeat_interval", 30)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._start_heartbeat()
        
        logger.info(f"🔌 WebSocket管理器初始化完成，最大连接数: {self.max_connections}")
    
    def _start_heartbeat(self):
        """启动心跳检测任务"""
        if config_manager.get("websocket.enabled", True):
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(f"💓 心跳检测已启动，间隔: {self.heartbeat_interval}秒")
    
    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_connections()
            except Exception as e:
                logger.error(f"❌ 心跳检测异常: {e}")
    
    async def _check_connections(self):
        """检查所有连接的健康状态"""
        dead_connections = []
        
        for client_id, connection in self.connections.items():
            if not connection.is_alive():
                logger.warning(f"💀 检测到死连接: {client_id}")
                dead_connections.append(client_id)
            else:
                # 发送ping
                try:
                    await connection.send_response(MessageType.PING, {
                        "timestamp": datetime.now().timestamp()
                    })
                    connection.last_ping = datetime.now()
                except Exception as e:
                    logger.error(f"❌ 发送ping失败 {client_id}: {e}")
                    dead_connections.append(client_id)
        
        # 清理死连接
        for client_id in dead_connections:
            await self.disconnect(client_id, reason="心跳超时")
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> WebSocketConnection:
        """
        接受新的WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            client_id: 可选的客户端ID
            
        Returns:
            WebSocket连接包装器
            
        Raises:
            Exception: 如果连接数超过限制
        """
        # 检查连接数限制
        if len(self.connections) >= self.max_connections:
            logger.warning(f"❌ 连接数超过限制 ({self.max_connections})")
            raise Exception(f"连接数超过限制: {self.max_connections}")
        
        # 接受连接
        await websocket.accept()
        
        # 创建连接包装器
        connection = WebSocketConnection(websocket, client_id)
        
        # 如果客户端ID已存在，断开旧连接
        if connection.client_id in self.connections:
            logger.warning(f"⚠️ 客户端ID已存在，断开旧连接: {connection.client_id}")
            await self.disconnect(connection.client_id, reason="新连接替代")
        
        # 添加到连接池
        self.connections[connection.client_id] = connection
        
        logger.info(f"✅ 新WebSocket连接: {connection.client_id}, 当前连接数: {len(self.connections)}")
        
        # 发送欢迎消息
        welcome_data = {
            "message": "🎉 WebSocket连接成功！现在可以进行实时聊天了。",
            "client_id": connection.client_id,
            "timestamp": datetime.now().timestamp(),
            "server_info": {
                "name": "HTTP MCP Server",
                "version": "1.0.0",
                "capabilities": ["tools", "chat", "websocket"]
            }
        }
        await connection.send_response(MessageType.SYSTEM, welcome_data)
        
        return connection
    
    async def disconnect(self, client_id: str, reason: str = "主动断开"):
        """
        断开WebSocket连接
        
        Args:
            client_id: 客户端ID
            reason: 断开原因
        """
        if client_id in self.connections:
            connection = self.connections[client_id]
            
            try:
                # 尝试发送断开消息
                await connection.send_response(MessageType.SYSTEM, {
                    "message": f"连接即将断开: {reason}",
                    "timestamp": datetime.now().timestamp()
                })
                
                # 关闭连接
                await connection.websocket.close()
            except Exception as e:
                logger.debug(f"🔌 关闭连接时出现异常 {client_id}: {e}")
            
            # 从连接池移除
            del self.connections[client_id]
            
            logger.info(f"🔌 WebSocket连接已断开: {client_id} ({reason}), 剩余连接数: {len(self.connections)}")
        else:
            logger.warning(f"⚠️ 尝试断开不存在的连接: {client_id}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """
        发送消息到特定客户端
        
        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        if client_id in self.connections:
            connection = self.connections[client_id]
            try:
                await connection.send_message(message)
            except Exception as e:
                logger.error(f"❌ 发送消息到客户端失败 {client_id}: {e}")
                await self.disconnect(client_id, reason="发送消息失败")
        else:
            logger.warning(f"⚠️ 尝试发送消息到不存在的客户端: {client_id}")
    
    async def send_response_to_client(self, client_id: str, response_type: MessageType, data: Dict[str, Any]):
        """
        发送标准响应到特定客户端
        
        Args:
            client_id: 客户端ID
            response_type: 响应类型
            data: 响应数据
        """
        if client_id in self.connections:
            connection = self.connections[client_id]
            try:
                await connection.send_response(response_type, data)
            except Exception as e:
                logger.error(f"❌ 发送响应到客户端失败 {client_id}: {e}")
                await self.disconnect(client_id, reason="发送响应失败")
        else:
            logger.warning(f"⚠️ 尝试发送响应到不存在的客户端: {client_id}")
    
    async def broadcast(self, message: Dict[str, Any], exclude_clients: Set[str] = None):
        """
        广播消息到所有连接的客户端
        
        Args:
            message: 消息内容
            exclude_clients: 排除的客户端ID集合
        """
        exclude_clients = exclude_clients or set()
        disconnected_clients = []
        
        logger.info(f"📢 广播消息到 {len(self.connections) - len(exclude_clients)} 个客户端")
        
        for client_id, connection in self.connections.items():
            if client_id in exclude_clients:
                continue
            
            try:
                await connection.send_message(message)
            except Exception as e:
                logger.error(f"❌ 广播消息失败 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理失败的连接
        for client_id in disconnected_clients:
            await self.disconnect(client_id, reason="广播失败")
    
    async def broadcast_response(self, response_type: MessageType, data: Dict[str, Any], exclude_clients: Set[str] = None):
        """
        广播标准响应到所有客户端
        
        Args:
            response_type: 响应类型
            data: 响应数据
            exclude_clients: 排除的客户端ID集合
        """
        response = WebSocketResponse(type=response_type, data=data)
        await self.broadcast(response.dict(), exclude_clients)
    
    def get_connection(self, client_id: str) -> Optional[WebSocketConnection]:
        """
        获取连接对象
        
        Args:
            client_id: 客户端ID
            
        Returns:
            连接对象，如果不存在则返回None
        """
        return self.connections.get(client_id)
    
    def get_all_connections(self) -> List[WebSocketConnection]:
        """获取所有连接"""
        return list(self.connections.values())
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.connections)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        total_messages = sum(conn.message_count for conn in self.connections.values())
        alive_connections = sum(1 for conn in self.connections.values() if conn.is_alive())
        
        return {
            "total_connections": len(self.connections),
            "alive_connections": alive_connections,
            "dead_connections": len(self.connections) - alive_connections,
            "max_connections": self.max_connections,
            "total_messages": total_messages,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    def get_connections_info(self) -> List[Dict[str, Any]]:
        """获取所有连接的详细信息"""
        return [conn.get_info() for conn in self.connections.values()]
    
    async def handle_ping(self, client_id: str, data: Dict[str, Any]):
        """
        处理ping消息
        
        Args:
            client_id: 客户端ID
            data: ping数据
        """
        connection = self.get_connection(client_id)
        if connection:
            connection.last_pong = datetime.now()
            await connection.send_response(MessageType.PONG, {
                "timestamp": datetime.now().timestamp(),
                "ping_timestamp": data.get("timestamp")
            })
            logger.debug(f"💓 处理ping: {client_id}")
    
    async def shutdown(self):
        """关闭WebSocket管理器"""
        logger.info("🛑 WebSocket管理器正在关闭...")
        
        # 停止心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 断开所有连接
        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            await self.disconnect(client_id, reason="服务器关闭")
        
        logger.info("✅ WebSocket管理器已关闭")


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()

# 导出
__all__ = [
    "WebSocketConnection", "WebSocketManager", "websocket_manager"
]
