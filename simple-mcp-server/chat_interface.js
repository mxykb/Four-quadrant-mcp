// MCP LangChain 交互式聊天前端JavaScript

class MCPChatInterface {
    constructor() {
        this.serverUrl = 'http://localhost:8000';
        this.apiKey = '';
        this.isConnected = false;
        this.isTyping = false;
        this.websocket = null;
        this.useWebSocket = true; // 优先使用WebSocket
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadConfig();
        
        // 初始化UI事件监听器
        this.initializeConfigListeners();
        
        this.loadChatHistory();
        this.connectWebSocket();
        this.updateWelcomeTime();
    }

    initializeConfigListeners() {
        // 温度滑块事件监听
        const temperatureSlider = document.getElementById('temperatureSlider');
        const temperatureValue = document.getElementById('temperatureValue');
        if (temperatureSlider && temperatureValue) {
            temperatureSlider.addEventListener('input', (e) => {
                temperatureValue.textContent = e.target.value;
                this.temperature = parseFloat(e.target.value);
            });
        }

        // 模型选择事件监听
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                this.model = e.target.value;
            });
        }

        // 最大令牌数事件监听
        const maxTokensInput = document.getElementById('maxTokensInput');
        if (maxTokensInput) {
            maxTokensInput.addEventListener('change', (e) => {
                this.maxTokens = parseInt(e.target.value) || 1000;
            });
        }

        // WebSocket开关事件监听
        const useWebSocketToggle = document.getElementById('useWebSocketToggle');
        if (useWebSocketToggle) {
            useWebSocketToggle.addEventListener('change', (e) => {
                this.useWebSocket = e.target.checked;
                // 如果关闭WebSocket，断开现有连接
                if (!this.useWebSocket && this.websocket) {
                    this.websocket.close();
                    this.websocket = null;
                }
                // 如果开启WebSocket，重新连接
                if (this.useWebSocket) {
                    this.connectWebSocket();
                }
            });
        }

        // DeepSeek API密钥事件监听
        const deepseekApiKeyInput = document.getElementById('deepseekApiKey');
        if (deepseekApiKeyInput) {
            deepseekApiKeyInput.addEventListener('input', (e) => {
                this.deepseekApiKey = e.target.value.trim();
            });
        }

        // API密钥事件监听
        if (this.apiKeyInput) {
            this.apiKeyInput.addEventListener('input', (e) => {
                this.apiKey = e.target.value.trim();
            });
        }
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.configPanel = document.getElementById('configPanel');
        this.serverUrlInput = document.getElementById('serverUrl');
        this.apiKeyInput = document.getElementById('apiKey');
    }

    setupEventListeners() {
        // 发送按钮点击事件
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // 输入框回车事件
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 输入框自动调整高度
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        // 定期检查连接状态
        setInterval(() => this.checkConnection(), 30000);
    }

    autoResizeTextarea() {
        const textarea = this.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    updateWelcomeTime() {
        const welcomeTime = document.getElementById('welcomeTime');
        if (welcomeTime) {
            welcomeTime.textContent = new Date().toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    connectWebSocket() {
        if (!this.useWebSocket) {
            this.checkConnection();
            return;
        }

        try {
            const wsUrl = this.serverUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                this.setConnectionStatus(true);
                this.reconnectAttempts = 0;
            };

            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event.data);
            };

            this.websocket.onclose = () => {
                console.log('WebSocket连接已关闭');
                this.setConnectionStatus(false);
                this.websocket = null;
                
                // 尝试重连
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connectWebSocket(), 3000 * this.reconnectAttempts);
                } else {
                    console.log('WebSocket重连失败，切换到HTTP模式');
                    this.useWebSocket = false;
                    this.checkConnection();
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.setConnectionStatus(false);
            };

            // 定期发送心跳
            setInterval(() => {
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.sendWebSocketMessage('ping', {});
                }
            }, 30000);

        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.useWebSocket = false;
            this.checkConnection();
        }
    }

    sendWebSocketMessage(type, data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type: type,
                data: data
            };
            // 如果是聊天消息，添加配置参数
            if (type === 'chat') {
                message.data = {
                    ...data,
                    api_key: this.apiKey || undefined,
                    deepseek_api_key: this.deepseekApiKey || undefined,
                    model: this.model || 'gpt-3.5-turbo',
                    temperature: this.temperature || 0.7,
                    max_tokens: this.maxTokens || 1000
                };
            }
            this.websocket.send(JSON.stringify(message));
            return true;
        }
        return false;
    }

    handleWebSocketMessage(messageStr) {
        try {
            const message = JSON.parse(messageStr);
            const { type, data } = message;

            switch (type) {
                case 'system':
                    this.addMessage('system', data.message);
                    break;
                    
                case 'chat_response':
                    this.showTyping(false);
                    if (data.success) {
                        this.addMessage('assistant', data.result, null, data.tool_calls);
                    } else {
                        this.showError(`助手回复失败: ${data.error}`);
                    }
                    break;
                    
                case 'processing':
                    this.showTyping(true);
                    break;
                    
                case 'error':
                    this.showTyping(false);
                    this.showError(data.message);
                    break;
                    
                case 'pong':
                    // 心跳响应，无需处理
                    break;
                    
                default:
                    console.log('未知的WebSocket消息类型:', type);
            }
        } catch (error) {
            console.error('解析WebSocket消息失败:', error);
        }
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.serverUrl}/health`, {
                method: 'GET',
                timeout: 5000
            });
            
            if (response.ok) {
                this.setConnectionStatus(true);
            } else {
                this.setConnectionStatus(false);
            }
        } catch (error) {
            console.error('连接检查失败:', error);
            this.setConnectionStatus(false);
        }
    }

    setConnectionStatus(connected) {
        this.isConnected = connected;
        const indicator = this.statusIndicator;
        
        if (connected) {
            indicator.style.background = '#4CAF50';
            indicator.title = '已连接到MCP服务器';
        } else {
            indicator.style.background = '#f44336';
            indicator.title = '无法连接到MCP服务器';
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        if (!this.isConnected) {
            this.showError('无法连接到服务器，请检查服务器状态');
            return;
        }

        if (!this.apiKey && !this.deepseekApiKey) {
            this.showError('请先配置API密钥');
            return;
        }

        // 添加用户消息到界面
        this.addMessage('user', message);
        
        // 清空输入框
        this.messageInput.value = '';
        this.autoResizeTextarea();
        
        try {
            // 优先使用WebSocket
            if (this.useWebSocket && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                const success = this.sendWebSocketMessage('chat', {
                    message: message,
                    api_key: this.apiKey,
                    model: 'gpt-3.5-turbo',
                    temperature: 0.7,
                    max_tokens: 1000
                });
                
                if (!success) {
                    throw new Error('WebSocket发送失败');
                }
            } else {
                // 回退到HTTP API
                this.showTyping(true);
                
                const response = await this.callChatAPI(message);
                
                this.showTyping(false);
                
                if (response.success) {
                    this.addMessage('assistant', response.result, null, response.tool_calls);
                } else {
                    this.showError(`助手回复失败: ${response.error}`);
                }
            }
        } catch (error) {
            this.showTyping(false);
            console.error('发送消息失败:', error);
            this.showError(`发送消息失败: ${error.message}`);
        }
    }

    async callChatAPI(message) {
        const requestData = {
            message: message,
            api_key: this.apiKey || undefined,
            deepseek_api_key: this.deepseekApiKey || undefined,
            model: this.model || 'gpt-3.5-turbo',
            temperature: this.temperature || 0.7,
            max_tokens: this.maxTokens || 1000
        };

        const response = await fetch(`${this.serverUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    addMessage(sender, content, timestamp = null, toolCalls = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const contentWrapper = document.createElement('div');
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // 处理消息内容格式化
        if (typeof content === 'string') {
            messageContent.innerHTML = this.formatMessage(content);
        } else {
            messageContent.textContent = JSON.stringify(content, null, 2);
        }
        
        // 如果有工具调用，添加工具调用可视化
        if (toolCalls && toolCalls.length > 0) {
            const toolCallsElement = this.renderToolCalls(toolCalls);
            contentWrapper.appendChild(toolCallsElement);
        }
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = timestamp || new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        contentWrapper.appendChild(messageContent);
        contentWrapper.appendChild(messageTime);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentWrapper);
        
        // 在打字指示器之前插入消息
        // Check if typingIndicator is a child of chatMessages before using insertBefore
        if (this.typingIndicator && this.chatMessages.contains(this.typingIndicator)) {
            this.chatMessages.insertBefore(messageDiv, this.typingIndicator);
        } else {
            this.chatMessages.appendChild(messageDiv);
        }
        
        // 保存聊天历史
        this.saveChatHistory();
        
        // 滚动到底部
        this.scrollToBottom();
    }

    formatMessage(content) {
        // 简单的消息格式化
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: #f0f0f0; padding: 2px 4px; border-radius: 3px;">$1</code>');
    }

    showTyping(show) {
        this.isTyping = show;
        this.typingIndicator.style.display = show ? 'flex' : 'none';
        this.sendButton.disabled = show;
        
        if (show) {
            this.scrollToBottom();
        }
    }

    renderToolCalls(toolCalls) {
        const toolCallsContainer = document.createElement('div');
        toolCallsContainer.className = 'tool-calls-container';
        toolCallsContainer.style.cssText = `
            margin-top: 10px;
            padding: 12px;
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 8px;
            font-size: 0.9em;
        `;
        
        const header = document.createElement('div');
        header.innerHTML = '<strong>🔧 工具调用详情:</strong>';
        header.style.cssText = 'margin-bottom: 8px; color: #1976d2;';
        toolCallsContainer.appendChild(header);
        
        toolCalls.forEach((call, index) => {
            const callDiv = document.createElement('div');
            callDiv.style.cssText = `
                margin: 8px 0;
                padding: 8px;
                background: rgba(255, 255, 255, 0.7);
                border-radius: 4px;
                border-left: 3px solid #2196f3;
            `;
            
            const toolName = document.createElement('div');
            toolName.innerHTML = `<strong>${index + 1}. ${call.tool_name}</strong>`;
            toolName.style.cssText = 'color: #1976d2; margin-bottom: 4px;';
            
            const args = document.createElement('div');
            args.innerHTML = `参数: <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 3px;">${JSON.stringify(call.arguments)}</code>`;
            args.style.cssText = 'margin-bottom: 4px; font-size: 0.85em;';
            
            callDiv.appendChild(toolName);
            callDiv.appendChild(args);
            
            if (call.result) {
                const result = document.createElement('div');
                result.innerHTML = `结果: ${call.result}`;
                result.style.cssText = 'color: #388e3c; font-size: 0.85em;';
                callDiv.appendChild(result);
            }
            
            toolCallsContainer.appendChild(callDiv);
        });
        
        return toolCallsContainer;
    }

    showError(message, details = null, retryAction = null) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error-message';
        
        let errorContent = `<div class="error-icon">❌</div><div class="error-text">${message}</div>`;
        
        if (details) {
            errorContent += `<div class="error-details">详细信息: ${details}</div>`;
        }
        
        if (retryAction) {
            errorContent += `<button class="retry-button" onclick="${retryAction}">🔄 重试</button>`;
        }
        
        errorDiv.innerHTML = `
            <div class="message-content error-content">${errorContent}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        errorDiv.style.cssText = `
            background: #ffebee;
            border-left: 4px solid #f44336;
            margin: 10px 0;
            animation: shake 0.5s ease-in-out;
        `;
        
        // Check if typingIndicator is a child of chatMessages before using insertBefore
        if (this.typingIndicator && this.chatMessages.contains(this.typingIndicator)) {
            this.chatMessages.insertBefore(errorDiv, this.typingIndicator);
        } else {
            this.chatMessages.appendChild(errorDiv);
        }
        this.scrollToBottom();
        
        // 自动隐藏非关键错误
        if (!details && !retryAction) {
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.style.opacity = '0.5';
                }
            }, 5000);
        }
    }

    showSuccess(message, autoHide = true) {
        const successDiv = document.createElement('div');
        successDiv.className = 'message success-message';
        successDiv.innerHTML = `
            <div class="message-content success-content">
                <div class="success-icon">✅</div>
                <div class="success-text">${message}</div>
            </div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        successDiv.style.cssText = `
            background: #e8f5e8;
            border-left: 4px solid #4caf50;
            margin: 10px 0;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Check if typingIndicator is a child of chatMessages before using insertBefore
        if (this.typingIndicator && this.chatMessages.contains(this.typingIndicator)) {
            this.chatMessages.insertBefore(successDiv, this.typingIndicator);
        } else {
            this.chatMessages.appendChild(successDiv);
        }
        this.scrollToBottom();
        
        if (autoHide) {
            setTimeout(() => {
                if (successDiv.parentNode) {
                    successDiv.style.opacity = '0.5';
                }
            }, 3000);
        }
    }

    showWarning(message, action = null) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'message warning-message';
        
        let warningContent = `<div class="warning-icon">⚠️</div><div class="warning-text">${message}</div>`;
        
        if (action) {
            warningContent += `<button class="action-button" onclick="${action.callback}">${action.text}</button>`;
        }
        
        warningDiv.innerHTML = `
            <div class="message-content warning-content">${warningContent}</div>
            <div class="message-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        warningDiv.style.cssText = `
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            margin: 10px 0;
        `;
        
        // Check if typingIndicator is a child of chatMessages before using insertBefore
        if (this.typingIndicator && this.chatMessages.contains(this.typingIndicator)) {
            this.chatMessages.insertBefore(warningDiv, this.typingIndicator);
        } else {
            this.chatMessages.appendChild(warningDiv);
        }
        this.scrollToBottom();
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    saveChatHistory() {
        const messages = [];
        const messageElements = this.chatMessages.querySelectorAll('.message');
        
        messageElements.forEach(element => {
            const sender = element.classList.contains('user') ? 'user' : 'assistant';
            const content = element.querySelector('.message-content').textContent;
            const time = element.querySelector('.message-time').textContent;
            
            messages.push({
                sender,
                content,
                timestamp: time
            });
        });
        
        localStorage.setItem('mcpChatHistory', JSON.stringify(messages));
    }

    loadChatHistory() {
        const savedHistory = localStorage.getItem('mcpChatHistory');
        if (savedHistory) {
            try {
                const messages = JSON.parse(savedHistory);
                messages.forEach(message => {
                    this.addMessage(message.sender, message.content, message.timestamp);
                });
            } catch (error) {
                console.error('加载聊天历史失败:', error);
            }
        }
    }

    clearChatHistory() {
        // 清除界面上的消息
        const messageElements = this.chatMessages.querySelectorAll('.message, .error-message, .success-message');
        messageElements.forEach(element => {
            element.remove();
        });
        
        // 清除本地存储
        localStorage.removeItem('mcpChatHistory');
        
        this.showSuccess('聊天历史已清除');
    }

    loadConfig() {
        const savedConfig = localStorage.getItem('mcpChatConfig');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            this.serverUrl = config.serverUrl || 'http://localhost:8000';
            this.apiKey = config.apiKey || '';
            this.deepseekApiKey = config.deepseekApiKey || '';
            this.model = config.model || 'gpt-3.5-turbo';
            this.temperature = config.temperature || 0.7;
            this.maxTokens = config.maxTokens || 1000;
            this.useWebSocket = config.useWebSocket !== undefined ? config.useWebSocket : true;
            
            // 更新UI
            if (this.serverUrlInput) this.serverUrlInput.value = this.serverUrl;
            if (this.apiKeyInput) this.apiKeyInput.value = this.apiKey;
            const deepseekApiKeyInput = document.getElementById('deepseekApiKey');
            if (deepseekApiKeyInput) deepseekApiKeyInput.value = this.deepseekApiKey;
            const modelSelect = document.getElementById('modelSelect');
            if (modelSelect) modelSelect.value = this.model;
            const temperatureSlider = document.getElementById('temperatureSlider');
            if (temperatureSlider) temperatureSlider.value = this.temperature;
            const temperatureValue = document.getElementById('temperatureValue');
            if (temperatureValue) temperatureValue.textContent = this.temperature;
            const maxTokensInput = document.getElementById('maxTokensInput');
            if (maxTokensInput) maxTokensInput.value = this.maxTokens;
            const useWebSocketToggle = document.getElementById('useWebSocketToggle');
            if (useWebSocketToggle) useWebSocketToggle.checked = this.useWebSocket;
        } else {
            // 设置默认值
            this.serverUrl = 'http://localhost:8000';
            this.apiKey = '';
            this.deepseekApiKey = '';
            this.model = 'gpt-3.5-turbo';
            this.temperature = 0.7;
            this.maxTokens = 1000;
            this.useWebSocket = true;
            
            // 从旧的localStorage迁移数据
            const savedServerUrl = localStorage.getItem('mcp_server_url');
            const savedApiKey = localStorage.getItem('mcp_api_key');
            
            if (savedServerUrl) {
                this.serverUrl = savedServerUrl;
                if (this.serverUrlInput) this.serverUrlInput.value = savedServerUrl;
            }
            
            if (savedApiKey) {
                this.apiKey = savedApiKey;
                if (this.apiKeyInput) this.apiKeyInput.value = savedApiKey;
            }
        }
    }

    saveConfig() {
        this.serverUrl = this.serverUrlInput.value.trim();
        this.apiKey = this.apiKeyInput.value.trim();
        const deepseekApiKeyInput = document.getElementById('deepseekApiKey');
        this.deepseekApiKey = deepseekApiKeyInput ? deepseekApiKeyInput.value.trim() : '';
        
        const config = {
            serverUrl: this.serverUrl,
            apiKey: this.apiKey,
            deepseekApiKey: this.deepseekApiKey,
            model: this.model,
            temperature: this.temperature,
            maxTokens: this.maxTokens,
            useWebSocket: this.useWebSocket
        };
        
        localStorage.setItem('mcpChatConfig', JSON.stringify(config));
        
        this.showSuccess('配置已保存');
        this.toggleConfig();
        this.checkConnection();
    }

    toggleConfig() {
        const panel = this.configPanel;
        panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
    }
}

// 全局函数
function toggleConfig() {
    if (window.chatInterface) {
        window.chatInterface.toggleConfig();
    }
}

function saveConfig() {
    const serverUrl = document.getElementById('serverUrl').value;
    const apiKey = document.getElementById('apiKey').value;
    const deepseekApiKey = document.getElementById('deepseekApiKey').value;
    const model = document.getElementById('modelSelect').value;
    const temperature = parseFloat(document.getElementById('temperatureSlider').value);
    const maxTokens = parseInt(document.getElementById('maxTokensInput').value);
    const useWebSocket = document.getElementById('useWebSocketToggle').checked;
    
    const config = {
        serverUrl,
        apiKey,
        deepseekApiKey,
        model,
        temperature,
        maxTokens,
        useWebSocket
    };
    
    localStorage.setItem('mcpChatConfig', JSON.stringify(config));
    
    // 更新实例变量
    if (window.chatInterface) {
        window.chatInterface.serverUrl = serverUrl;
        window.chatInterface.apiKey = apiKey;
        window.chatInterface.deepseekApiKey = deepseekApiKey;
        window.chatInterface.model = model;
        window.chatInterface.temperature = temperature;
        window.chatInterface.maxTokens = maxTokens;
        window.chatInterface.useWebSocket = useWebSocket;
        
        // 如果WebSocket设置改变，重新连接
        if (useWebSocket && !window.chatInterface.websocket) {
            window.chatInterface.connectWebSocket();
        } else if (!useWebSocket && window.chatInterface.websocket) {
            window.chatInterface.websocket.close();
            window.chatInterface.websocket = null;
        }
        
        window.chatInterface.showSuccess('配置已保存');
        window.chatInterface.toggleConfig();
        window.chatInterface.checkConnection();
    }
}

function resetConfig() {
    // 重置为默认值
    document.getElementById('serverUrl').value = 'http://localhost:8000';
    document.getElementById('apiKey').value = '';
    document.getElementById('deepseekApiKey').value = '';
    document.getElementById('modelSelect').value = 'gpt-3.5-turbo';
    document.getElementById('temperatureSlider').value = '0.7';
    document.getElementById('temperatureValue').textContent = '0.7';
    document.getElementById('maxTokensInput').value = '1000';
    document.getElementById('useWebSocketToggle').checked = true;
    
    // 清除localStorage
    localStorage.removeItem('mcpChatConfig');
    localStorage.removeItem('mcp_server_url');
    localStorage.removeItem('mcp_api_key');
    
    // 更新实例变量
    if (window.chatInterface) {
        window.chatInterface.serverUrl = 'http://localhost:8000';
        window.chatInterface.apiKey = '';
        window.chatInterface.deepseekApiKey = '';
        window.chatInterface.model = 'gpt-3.5-turbo';
        window.chatInterface.temperature = 0.7;
        window.chatInterface.maxTokens = 1000;
        window.chatInterface.useWebSocket = true;
        
        // 重新连接WebSocket
        if (window.chatInterface.websocket) {
            window.chatInterface.websocket.close();
        }
        window.chatInterface.connectWebSocket();
        
        window.chatInterface.showSuccess('配置已重置为默认值');
    }
}

function sendMessage() {
    if (window.chatInterface) {
        window.chatInterface.sendMessage();
    }
}

function clearChatHistory() {
    if (window.chatInterface) {
        if (confirm('确定要清除所有聊天历史吗？此操作不可撤销。')) {
            window.chatInterface.clearChatHistory();
        }
    }
}

// 配置导入导出功能
function exportConfig() {
    try {
        const config = {
            model: document.getElementById('modelSelect').value,
            temperature: parseFloat(document.getElementById('temperatureSlider').value),
            maxTokens: parseInt(document.getElementById('maxTokensInput').value),
            useWebSocket: document.getElementById('useWebSocketToggle').checked,
            serverUrl: document.getElementById('serverUrl').value,
            apiKey: document.getElementById('apiKey').value,
            deepseekApiKey: document.getElementById('deepseekApiKey').value,
            exportDate: new Date().toISOString(),
            version: '1.0'
        };
        
        const dataStr = JSON.stringify(config, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `mcp-chat-config-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        if (window.chatInterface) {
            window.chatInterface.showSuccess('配置已导出到文件');
        }
    } catch (error) {
        if (window.chatInterface) {
            window.chatInterface.showError('导出配置失败', error.message);
        }
    }
}

function importConfig() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = handleConfigImport;
    input.click();
}

function handleConfigImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.json')) {
        if (window.chatInterface) {
            window.chatInterface.showError('请选择有效的JSON配置文件');
        }
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const config = JSON.parse(e.target.result);
            
            // 验证配置格式
            if (!config.model || typeof config.temperature !== 'number' || typeof config.maxTokens !== 'number') {
                throw new Error('配置文件格式不正确');
            }
            
            // 应用配置
            if (config.model) document.getElementById('modelSelect').value = config.model;
            if (typeof config.temperature === 'number') {
                document.getElementById('temperatureSlider').value = config.temperature;
                document.getElementById('temperatureValue').textContent = config.temperature;
            }
            if (typeof config.maxTokens === 'number') {
                document.getElementById('maxTokensInput').value = config.maxTokens;
            }
            if (typeof config.useWebSocket === 'boolean') {
                document.getElementById('useWebSocketToggle').checked = config.useWebSocket;
            }
            if (config.serverUrl) document.getElementById('serverUrl').value = config.serverUrl;
            if (config.apiKey) document.getElementById('apiKey').value = config.apiKey;
            if (config.deepseekApiKey) document.getElementById('deepseekApiKey').value = config.deepseekApiKey;
            
            // 保存到本地存储
            saveConfig();
            
            if (window.chatInterface) {
                window.chatInterface.showSuccess(`配置已导入 ${config.exportDate ? '(导出时间: ' + new Date(config.exportDate).toLocaleString() + ')' : ''}`);
            }
        } catch (error) {
            if (window.chatInterface) {
                window.chatInterface.showError('导入配置失败', error.message);
            }
        }
    };
    
    reader.onerror = function() {
        if (window.chatInterface) {
            window.chatInterface.showError('读取文件失败');
        }
    };
    
    reader.readAsText(file);
    
    // 清空文件输入，允许重复选择同一文件
    event.target.value = '';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.chatInterface = new MCPChatInterface();
    console.log('MCP Chat Interface 已初始化');
});

// 导出类以供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MCPChatInterface;
}