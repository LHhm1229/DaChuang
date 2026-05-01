/**
 * useDynamicWebSocket.ts
 * 统一WebSocket通信层 - 支持动态端口切换
 * 基于《新项目数据传输方案与设计思路》的15秒心跳+断线重连机制
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// =========================
// 类型定义
// =========================
export type ModuleType = 'dry-eye' | 'sleep' | 'fatigue';
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
}

export interface UseDynamicWebSocketOptions {
  module: ModuleType;
  autoConnect?: boolean;
  heartbeatInterval?: number;  // 默认15秒
  reconnectDelay?: number;      // 默认3秒
  maxReconnectAttempts?: number;
  onMessage?: (msg: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export interface UseDynamicWebSocketReturn {
  status: ConnectionStatus;
  lastMessage: WebSocketMessage | null;
  sendMessage: (msg: WebSocketMessage) => void;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  getStats: () => void;
  getLatest: () => void;
}

// =========================
// 端口映射配置
// =========================
const MODULE_PORT_MAP: Record<ModuleType, number> = {
  'dry-eye': 3000,
  'sleep': 3001,
  'fatigue': 3002
};

const MODULE_WS_MAP: Record<ModuleType, string> = {
  'dry-eye': 'dryEye',
  'sleep': 'sleepQuality',
  'fatigue': 'fatigue'
};

// =========================
// 自定义Hook实现
// =========================
export function useDynamicWebSocket(options: UseDynamicWebSocketOptions): UseDynamicWebSocketReturn {
  const {
    module,
    autoConnect = true,
    heartbeatInterval = 15000,     // 15秒心跳
    reconnectDelay = 3000,         // 3秒重连延迟
    maxReconnectAttempts = 5,
    onMessage,
    onConnect,
    onDisconnect,
    onError
  } = options;

  // 状态
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnectRef = useRef(false);

  // 获取WebSocket URL（使用代理路径）
  const getWebSocketUrl = useCallback((): string => {
    return `/ws/${module}`;
  }, [module]);

  // 获取HTTP URL（使用代理路径）
  const getHttpUrl = useCallback((): string => {
    return `/api/${module}`;
  }, [module]);

  // 启动心跳
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }

    heartbeatTimerRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  // 停止心跳
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  // 处理消息
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(msg);
      console.log(`[WS] 收到消息: type=${msg.type}, data=${JSON.stringify(msg.data)?.substring(0, 100)}...`);

      // 回调
      if (msg.type !== 'pong') {
        onMessage?.(msg);
      }

      // 连接成功时触发
      if (msg.type === 'hello') {
        setStatus('connected');
        onConnect?.();
      }
    } catch (error) {
      console.error('[WS] 消息解析失败:', error);
    }
  }, [onMessage, onConnect]);

  // 连接
  const connect = useCallback(() => {
    // 如果已连接，先断开
    if (wsRef.current) {
      wsRef.current.close();
    }

    isManualDisconnectRef.current = false;
    setStatus('connecting');

    const wsUrl = getWebSocketUrl();
    console.log(`[WS] 正在连接 ${module} 模块 → ${wsUrl}`);

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`[WS] ${module} 模块连接成功`);
        setStatus('connected');
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        onConnect?.();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error(`[WS] ${module} 模块连接错误 | type: ${error.type} | message: ${error.message}`);
        setStatus('error');
        onError?.(error);
      };

      ws.onclose = (event) => {
        const reason = event.code === 1000 ? '正常关闭' : 
                      event.code === 1001 ? '端点离开' :
                      event.code === 1006 ? '异常断开（可能是网络问题或服务端关闭）' :
                      event.code === 1011 ? '服务端内部错误' : `未知原因 (code: ${event.code})`;
        console.log(`[WS] ${module} 模块连接关闭 | code: ${event.code} | reason: ${reason} | wasClean: ${event.wasClean}`);
        stopHeartbeat();
        setStatus('disconnected');
        onDisconnect?.();

        if (!isManualDisconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[WS] 尝试第 ${reconnectAttemptsRef.current}/${maxReconnectAttempts} 次重连... (延迟 ${reconnectDelay}ms)`);
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.warn(`[WS] 已达到最大重连次数 (${maxReconnectAttempts})，停止重连`);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error(`[WS] ${module} 模块连接异常:`, error);
      setStatus('error');
    }
  }, [module, getWebSocketUrl, handleMessage, startHeartbeat, stopHeartbeat, onConnect, onDisconnect, onError, reconnectDelay, maxReconnectAttempts]);

  // 断开连接
  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    stopHeartbeat();

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus('disconnected');
  }, [stopHeartbeat]);

  // 重新连接
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // 发送消息
  const sendMessage = useCallback((msg: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn('[WS] WebSocket未连接，消息未发送');
    }
  }, []);

  // 获取统计
  const getStats = useCallback(() => {
    sendMessage({ type: 'getStats' });
  }, [sendMessage]);

  // 获取最新数据
  const getLatest = useCallback(() => {
    sendMessage({ type: 'getLatest' });
  }, [sendMessage]);

  // 监听module变化，自动重连
  useEffect(() => {
    if (autoConnect) {
      reconnect();
    }

    return () => {
      disconnect();
    };
  }, [module, autoConnect]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      stopHeartbeat();
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [stopHeartbeat]);

  return {
    status,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    reconnect,
    getStats,
    getLatest
  };
}

// =========================
// 便捷Hook - 获取特定模块数据
// =========================
export function useModuleWebSocket(module: ModuleType) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleMessage = useCallback((msg: WebSocketMessage) => {
    if (msg.type === MODULE_WS_MAP[module]) {
      setData(msg.data);
      setError(null);
    } else if (msg.type === 'error') {
      setError(msg.data?.message || '未知错误');
    }
  }, [module]);

  const { status, connect, disconnect, reconnect } = useDynamicWebSocket({
    module,
    autoConnect: false,
    onMessage: handleMessage
  });

  return {
    data,
    error,
    status,
    connect,
    disconnect,
    reconnect
  };
}