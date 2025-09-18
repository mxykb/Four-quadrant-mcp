#!/usr/bin/env python3
"""
MCP 服务器配置管理
负责配置文件读取、环境变量处理、默认配置等
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from models import ModelConfig, ServerConfig, ModelProvider

# 配置日志
logger = logging.getLogger("Config")

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"✅ 配置文件已加载: {self.config_file}")
            else:
                logger.warning(f"⚠️ 配置文件不存在，使用默认配置: {self.config_file}")
                self._config = self._get_default_config()
                self._save_config()
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "log_level": "INFO",
                "cors_origins": ["*"]
            },
            "models": {
                "default_provider": "openai",
                "openai": {
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "api_key": None,
                    "base_url": None
                },
                "deepseek": {
                    "model_name": "deepseek-chat",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "api_key": None,
                    "base_url": "https://api.deepseek.com"
                }
            },
            "tools": {
                "enabled": ["read_file", "write_file", "list_files"],
                "file_operations": {
                    "max_file_size": 10485760,  # 10MB
                    "allowed_extensions": [".txt", ".json", ".csv", ".md", ".py"],
                    "base_directory": ".",
                    "create_directories": True
                }
            },
            "websocket": {
                "enabled": True,
                "heartbeat_interval": 30,
                "max_connections": 100
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "mcp_server.log",
                "console": True
            }
        }
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套键）
        
        Args:
            key: 配置键，支持 "server.host" 格式
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any, save: bool = True):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            save: 是否立即保存到文件
        """
        keys = key.split('.')
        config = self._config
        
        # 导航到父级字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        
        if save:
            self._save_config()
    
    def get_server_config(self) -> ServerConfig:
        """获取服务器配置"""
        server_config = self.get("server", {})
        return ServerConfig(
            host=server_config.get("host", "0.0.0.0"),
            port=server_config.get("port", 8000),
            debug=server_config.get("debug", False),
            log_level=server_config.get("log_level", "INFO"),
            cors_origins=server_config.get("cors_origins", ["*"])
        )
    
    def get_model_config(self, provider: str) -> ModelConfig:
        """
        获取模型配置
        
        Args:
            provider: 模型提供商 (openai/deepseek)
            
        Returns:
            模型配置
        """
        model_config = self.get(f"models.{provider}", {})
        
        # 从环境变量获取API密钥
        api_key = self._get_api_key(provider)
        if api_key:
            model_config["api_key"] = api_key
        
        return ModelConfig(
            provider=ModelProvider(provider),
            model_name=model_config.get("model_name", "gpt-3.5-turbo"),
            api_key=model_config.get("api_key"),
            base_url=model_config.get("base_url"),
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 1000)
        )
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """
        从环境变量获取API密钥
        
        Args:
            provider: 模型提供商
            
        Returns:
            API密钥
        """
        env_keys = {
            "openai": ["OPENAI_API_KEY", "OPENAI_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY", "DEEPSEEK_KEY"]
        }
        
        for env_key in env_keys.get(provider, []):
            api_key = os.getenv(env_key)
            if api_key:
                return api_key
        
        return None
    
    def get_tool_config(self) -> Dict[str, Any]:
        """获取工具配置"""
        return self.get("tools", {})
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """获取WebSocket配置"""
        return self.get("websocket", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get("logging", {})
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用"""
        enabled_tools = self.get("tools.enabled", [])
        return tool_name in enabled_tools
    
    def get_file_operation_config(self) -> Dict[str, Any]:
        """获取文件操作配置"""
        return self.get("tools.file_operations", {})
    
    def update_config(self, updates: Dict[str, Any], save: bool = True):
        """
        批量更新配置
        
        Args:
            updates: 更新字典
            save: 是否保存到文件
        """
        def _update_nested(config: dict, updates: dict):
            for key, value in updates.items():
                if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                    _update_nested(config[key], value)
                else:
                    config[key] = value
        
        _update_nested(self._config, updates)
        
        if save:
            self._save_config()
    
    def validate_config(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
        """
        try:
            # 验证服务器配置
            server_config = self.get_server_config()
            if not (1 <= server_config.port <= 65535):
                logger.error("❌ 服务器端口配置无效")
                return False
            
            # 验证模型配置
            for provider in ["openai", "deepseek"]:
                model_config = self.get_model_config(provider)
                if model_config.temperature < 0 or model_config.temperature > 2:
                    logger.error(f"❌ {provider} 温度参数配置无效")
                    return False
                
                if model_config.max_tokens <= 0:
                    logger.error(f"❌ {provider} 最大令牌数配置无效")
                    return False
            
            logger.info("✅ 配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置验证失败: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def reload_config(self):
        """重新加载配置文件"""
        logger.info("🔄 重新加载配置文件...")
        self._load_config()


# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(key, default)

def get_server_config() -> ServerConfig:
    """获取服务器配置的便捷函数"""
    return config_manager.get_server_config()

def get_model_config(provider: str) -> ModelConfig:
    """获取模型配置的便捷函数"""
    return config_manager.get_model_config(provider)

def is_tool_enabled(tool_name: str) -> bool:
    """检查工具是否启用的便捷函数"""
    return config_manager.is_tool_enabled(tool_name)

# 导出
__all__ = [
    "ConfigManager",
    "config_manager", 
    "get_config",
    "get_server_config",
    "get_model_config", 
    "is_tool_enabled"
]
