package com.fourquadrant.server;

import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;
import android.util.Log;
import android.content.Context;

/**
 * 四象限Android HTTP服务器
 * 处理来自PC端MCP服务器的API调用
 */
public class AndroidHttpServer {
    private static final String TAG = "AndroidHttpServer";
    private static final int PORT = 8080;
    private static final String CORS_ORIGIN = "*";
    
    private ServerSocket serverSocket;
    private boolean isRunning = false;
    private ExecutorService threadPool;
    private Context context;
    private CommandRouter commandRouter;
    
    public AndroidHttpServer(Context context) {
        this.context = context;
        this.threadPool = Executors.newFixedThreadPool(10);
        this.commandRouter = new CommandRouter(context);
    }
    
    /**
     * 启动HTTP服务器
     */
    public void startServer() {
        try {
            serverSocket = new ServerSocket(PORT);
            isRunning = true;
            
            Log.i(TAG, "🚀 四象限HTTP服务器启动成功，监听端口: " + PORT);
            
            // 在后台线程中处理连接
            threadPool.execute(this::handleConnections);
            
        } catch (IOException e) {
            Log.e(TAG, "❌ 启动服务器失败: " + e.getMessage());
        }
    }
    
    /**
     * 停止HTTP服务器
     */
    public void stopServer() {
        isRunning = false;
        try {
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            threadPool.shutdown();
            Log.i(TAG, "🛑 HTTP服务器已停止");
        } catch (IOException e) {
            Log.e(TAG, "停止服务器时出错: " + e.getMessage());
        }
    }
    
    /**
     * 处理连接请求
     */
    private void handleConnections() {
        while (isRunning) {
            try {
                Socket clientSocket = serverSocket.accept();
                threadPool.execute(() -> handleClient(clientSocket));
            } catch (IOException e) {
                if (isRunning) {
                    Log.e(TAG, "接受连接时出错: " + e.getMessage());
                }
            }
        }
    }
    
    /**
     * 处理客户端请求
     */
    private void handleClient(Socket clientSocket) {
        try (BufferedReader in = new BufferedReader(
                new InputStreamReader(clientSocket.getInputStream()));
             PrintWriter out = new PrintWriter(
                clientSocket.getOutputStream(), true)) {
            
            // 读取HTTP请求
            String requestLine = in.readLine();
            if (requestLine == null) return;
            
            Map<String, String> headers = new HashMap<>();
            String line;
            while ((line = in.readLine()) != null && !line.isEmpty()) {
                String[] parts = line.split(": ", 2);
                if (parts.length == 2) {
                    headers.put(parts[0].toLowerCase(), parts[1]);
                }
            }
            
            // 解析请求
            String[] requestParts = requestLine.split(" ");
            String method = requestParts[0];
            String path = requestParts[1];
            
            Log.i(TAG, "📨 收到请求: " + method + " " + path);
            
            // 处理CORS预检请求
            if ("OPTIONS".equals(method)) {
                sendCorsResponse(out);
                return;
            }
            
            // 读取请求体
            String requestBody = "";
            if ("POST".equals(method)) {
                int contentLength = Integer.parseInt(
                    headers.getOrDefault("content-length", "0"));
                if (contentLength > 0) {
                    char[] buffer = new char[contentLength];
                    in.read(buffer);
                    requestBody = new String(buffer);
                }
            }
            
            // 路由处理
            String response;
            if ("/api/command/execute".equals(path) && "POST".equals(method)) {
                response = handleCommandExecution(requestBody);
            } else if ("/api/status".equals(path) && "GET".equals(method)) {
                response = handleStatusCheck();
            } else if ("/ping".equals(path)) {
                response = handlePing();
            } else {
                response = createErrorResponse("404 Not Found", "API端点不存在");
            }
            
            // 发送响应
            sendHttpResponse(out, "200 OK", response);
            
        } catch (Exception e) {
            Log.e(TAG, "处理客户端请求时出错: " + e.getMessage());
        } finally {
            try {
                clientSocket.close();
            } catch (IOException e) {
                Log.e(TAG, "关闭客户端连接时出错: " + e.getMessage());
            }
        }
    }
    
    /**
     * 处理命令执行请求
     */
    private String handleCommandExecution(String requestBody) {
        try {
            JSONObject request = new JSONObject(requestBody);
            String command = request.getString("command");
            JSONObject args = request.optJSONObject("args");
            
            Log.i(TAG, "🔧 执行命令: " + command);
            
            // 调用命令路由器执行命令
            JSONObject result = commandRouter.executeCommand(command, args);
            
            // 添加时间戳
            result.put("timestamp", System.currentTimeMillis() / 1000);
            
            Log.i(TAG, "✅ 命令执行完成: " + result.optString("message"));
            
            return result.toString();
            
        } catch (JSONException e) {
            Log.e(TAG, "❌ 解析请求JSON失败: " + e.getMessage());
            return createErrorResponse("400 Bad Request", "请求格式错误: " + e.getMessage());
        } catch (Exception e) {
            Log.e(TAG, "❌ 执行命令失败: " + e.getMessage());
            return createErrorResponse("500 Internal Server Error", "命令执行失败: " + e.getMessage());
        }
    }
    
    /**
     * 处理状态检查请求
     */
    private String handleStatusCheck() {
        try {
            JSONObject status = new JSONObject();
            status.put("success", true);
            status.put("message", "📱 Android服务器运行正常");
            status.put("server_info", new JSONObject()
                .put("port", PORT)
                .put("version", "1.0.0")
                .put("uptime", System.currentTimeMillis())
            );
            status.put("features", new JSONObject()
                .put("pomodoro", true)
                .put("tasks", true)
                .put("statistics", true)
                .put("settings", true)
            );
            status.put("timestamp", System.currentTimeMillis() / 1000);
            
            return status.toString();
        } catch (JSONException e) {
            return createErrorResponse("500 Internal Server Error", "生成状态信息失败");
        }
    }
    
    /**
     * 处理ping请求
     */
    private String handlePing() {
        try {
            JSONObject pong = new JSONObject();
            pong.put("success", true);
            pong.put("message", "🏓 pong");
            pong.put("timestamp", System.currentTimeMillis() / 1000);
            return pong.toString();
        } catch (JSONException e) {
            return createErrorResponse("500 Internal Server Error", "生成ping响应失败");
        }
    }
    
    /**
     * 发送CORS响应
     */
    private void sendCorsResponse(PrintWriter out) {
        out.println("HTTP/1.1 200 OK");
        out.println("Access-Control-Allow-Origin: " + CORS_ORIGIN);
        out.println("Access-Control-Allow-Methods: GET, POST, OPTIONS");
        out.println("Access-Control-Allow-Headers: Content-Type, Authorization");
        out.println("Access-Control-Max-Age: 86400");
        out.println("Content-Length: 0");
        out.println();
        out.flush();
    }
    
    /**
     * 发送HTTP响应
     */
    private void sendHttpResponse(PrintWriter out, String status, String body) {
        byte[] bodyBytes = body.getBytes();
        
        out.println("HTTP/1.1 " + status);
        out.println("Content-Type: application/json; charset=UTF-8");
        out.println("Content-Length: " + bodyBytes.length);
        out.println("Access-Control-Allow-Origin: " + CORS_ORIGIN);
        out.println("Access-Control-Allow-Methods: GET, POST, OPTIONS");
        out.println("Access-Control-Allow-Headers: Content-Type, Authorization");
        out.println("Connection: close");
        out.println();
        out.print(body);
        out.flush();
    }
    
    /**
     * 创建错误响应
     */
    private String createErrorResponse(String error, String message) {
        try {
            JSONObject response = new JSONObject();
            response.put("success", false);
            response.put("error", error);
            response.put("message", "❌ " + message);
            response.put("timestamp", System.currentTimeMillis() / 1000);
            return response.toString();
        } catch (JSONException e) {
            return "{\"success\":false,\"message\":\"JSON生成失败\"}";
        }
    }
    
    /**
     * 获取服务器状态
     */
    public boolean isRunning() {
        return isRunning && serverSocket != null && !serverSocket.isClosed();
    }
    
    /**
     * 获取服务器端口
     */
    public int getPort() {
        return PORT;
    }
}

/**
 * 命令路由器 - 处理具体的功能命令
 */
class CommandRouter {
    private static final String TAG = "CommandRouter";
    private Context context;
    
    public CommandRouter(Context context) {
        this.context = context;
    }
    
    /**
     * 执行命令
     */
    public JSONObject executeCommand(String command, JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        switch (command) {
            case "start_pomodoro":
                return handleStartPomodoro(args);
            case "control_pomodoro":
                return handleControlPomodoro(args);
            case "manage_break":
                return handleManageBreak(args);
            case "manage_tasks":
                return handleManageTasks(args);
            case "get_statistics":
                return handleGetStatistics(args);
            case "update_settings":
                return handleUpdateSettings(args);
            case "check_status":
                return handleCheckStatus();
            case "ping":
                result.put("success", true);
                result.put("message", "🏓 pong");
                return result;
            default:
                result.put("success", false);
                result.put("message", "❌ 未知命令: " + command);
                return result;
        }
    }
    
    private JSONObject handleStartPomodoro(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        String taskName = args.optString("task_name", "");
        int duration = args.optInt("duration", 25);
        String taskId = args.optString("task_id", "");
        
        if (taskName.isEmpty()) {
            result.put("success", false);
            result.put("message", "❌ 任务名称不能为空");
            return result;
        }
        
        // 这里应该调用实际的番茄钟功能
        // 模拟实现
        String sessionId = "session_" + System.currentTimeMillis();
        long startTime = System.currentTimeMillis() / 1000;
        long endTime = startTime + (duration * 60);
        
        JSONObject data = new JSONObject();
        data.put("session_id", sessionId);
        data.put("task_name", taskName);
        data.put("duration", duration);
        data.put("start_time", startTime);
        data.put("end_time", endTime);
        if (!taskId.isEmpty()) {
            data.put("task_id", taskId);
        }
        
        result.put("success", true);
        result.put("message", "🍅 番茄钟启动成功！任务: " + taskName + "，时长: " + duration + "分钟");
        result.put("data", data);
        
        Log.i(TAG, "🍅 番茄钟已启动: " + taskName + " (" + duration + "分钟)");
        
        return result;
    }
    
    private JSONObject handleControlPomodoro(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        String action = args.optString("action", "");
        String reason = args.optString("reason", "");
        
        // 模拟实现
        switch (action) {
            case "pause":
                result.put("success", true);
                result.put("message", "⏸️ 番茄钟已暂停");
                break;
            case "resume":
                result.put("success", true);
                result.put("message", "▶️ 番茄钟已恢复");
                break;
            case "stop":
                result.put("success", true);
                result.put("message", "⏹️ 番茄钟已停止");
                break;
            case "status":
                JSONObject statusData = new JSONObject();
                statusData.put("state", "running");
                statusData.put("remaining_time", 1200); // 20分钟
                statusData.put("task_name", "示例任务");
                
                result.put("success", true);
                result.put("message", "📊 番茄钟状态查询成功");
                result.put("data", statusData);
                break;
            default:
                result.put("success", false);
                result.put("message", "❌ 无效的操作: " + action);
        }
        
        return result;
    }
    
    private JSONObject handleManageBreak(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        String action = args.optString("action", "");
        
        switch (action) {
            case "start":
                result.put("success", true);
                result.put("message", "☕ 休息时间开始，好好放松一下吧！");
                
                JSONObject breakData = new JSONObject();
                breakData.put("type", "short_break");
                breakData.put("duration", 5);
                breakData.put("start_time", System.currentTimeMillis() / 1000);
                result.put("data", breakData);
                break;
                
            case "skip":
                result.put("success", true);
                result.put("message", "⏭️ 跳过休息，继续加油工作！");
                break;
                
            default:
                result.put("success", false);
                result.put("message", "❌ 无效的休息操作: " + action);
        }
        
        return result;
    }
    
    private JSONObject handleManageTasks(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        String action = args.optString("action", "");
        
        switch (action) {
            case "create":
                JSONObject taskData = args.optJSONObject("task_data");
                if (taskData == null) {
                    result.put("success", false);
                    result.put("message", "❌ 缺少任务数据");
                    return result;
                }
                
                String taskId = "task_" + System.currentTimeMillis();
                JSONObject createdTask = new JSONObject(taskData.toString());
                createdTask.put("id", taskId);
                createdTask.put("created_at", System.currentTimeMillis() / 1000);
                createdTask.put("status", "pending");
                
                result.put("success", true);
                result.put("message", "📝 任务创建成功");
                result.put("data", createdTask);
                break;
                
            case "list":
                JSONArray taskList = new JSONArray();
                // 模拟任务列表
                JSONObject sampleTask = new JSONObject();
                sampleTask.put("id", "task_sample");
                sampleTask.put("name", "示例任务");
                sampleTask.put("importance", 3);
                sampleTask.put("urgency", 2);
                sampleTask.put("quadrant", "第二象限");
                taskList.put(sampleTask);
                
                result.put("success", true);
                result.put("message", "📋 任务列表获取成功");
                result.put("data", new JSONObject().put("tasks", taskList));
                break;
                
            case "complete":
                String completeTaskId = args.optString("task_id", "");
                result.put("success", true);
                result.put("message", "✅ 任务已完成: " + completeTaskId);
                break;
                
            default:
                result.put("success", true);
                result.put("message", "✅ 任务操作完成: " + action);
        }
        
        return result;
    }
    
    private JSONObject handleGetStatistics(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        String type = args.optString("type", "general");
        
        // 模拟统计数据
        JSONObject stats = new JSONObject();
        stats.put("completed_pomodoros", 15);
        stats.put("total_focus_time", 375); // 分钟
        stats.put("completed_tasks", 8);
        stats.put("productivity_score", 85);
        
        result.put("success", true);
        result.put("message", "📊 统计数据获取成功");
        result.put("data", stats);
        
        return result;
    }
    
    private JSONObject handleUpdateSettings(JSONObject args) throws JSONException {
        JSONObject result = new JSONObject();
        
        // 模拟设置更新
        JSONObject updatedSettings = new JSONObject();
        Iterator<String> keys = args.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            updatedSettings.put(key, args.get(key));
        }
        
        result.put("success", true);
        result.put("message", "⚙️ 设置更新成功");
        result.put("data", updatedSettings);
        
        return result;
    }
    
    private JSONObject handleCheckStatus() throws JSONException {
        JSONObject result = new JSONObject();
        
        JSONObject status = new JSONObject();
        status.put("server_running", true);
        status.put("features_available", true);
        status.put("last_activity", System.currentTimeMillis() / 1000);
        
        result.put("success", true);
        result.put("message", "📱 系统状态正常");
        result.put("data", status);
        
        return result;
    }
}
