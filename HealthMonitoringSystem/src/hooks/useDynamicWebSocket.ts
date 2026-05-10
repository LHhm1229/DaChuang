/**
 * useDynamicWebSocket.ts
 * 统一Socket.IO通信层 - 支持动态端口切换
 * 使用socket.io-client替代原生WebSocket
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

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
  heartbeatInterval?: number;
  reconnectDelay?: number;
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
  'dry-eye': 3001,
  'sleep': 3003,
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
    heartbeatInterval = 15000,
    reconnectDelay = 3000,
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
  const socketRef = useRef<Socket | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnectRef = useRef(false);

  // 获取Socket.IO URL
  const getSocketUrl = useCallback((): string => {
    const port = MODULE_PORT_MAP[module];
    return `http://localhost:${port}`;
  }, [module]);

  // 启动心跳
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }

    heartbeatTimerRef.current = setInterval(() => {
      if (socketRef.current && socketRef.current.connected) {
        socketRef.current.emit('ping', { ts: Date.now() });
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
  const handleMessage = useCallback((msg: WebSocketMessage) => {
    setLastMessage(msg);
    console.log(`[WS] 收到消息: type=${msg.type}, data=${JSON.stringify(msg.data)?.substring(0, 100)}...`);

    // 回调
    if (msg.type !== 'pong') {
      onMessage?.(msg);
    }

    // 连接成功时触发（如果还没设置）
    if (msg.type === 'hello') {
      setStatus('connected');
      onConnect?.();
    }
  }, [onMessage, onConnect]);

  // 连接
  const connect = useCallback(() => {
    // 如果已连接，先断开
    if (socketRef.current) {
      socketRef.current.disconnect();
    }

    isManualDisconnectRef.current = false;
    setStatus('connecting');

    const socketUrl = getSocketUrl();
    console.log(`[WS] 正在连接 ${module} 模块 → ${socketUrl}`);

    try {
      const socket = io(socketUrl, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: reconnectDelay,
        reconnectionDelayMax: 30000,
        reconnectionAttempts: maxReconnectAttempts,
        pingInterval: heartbeatInterval,
        pingTimeout: 120000,
        autoConnect: false
      });

      socket.connect();

      socket.on('connect', () => {
        console.log(`[WS] ${module} 模块连接成功`);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        onConnect?.();
        setStatus('connected');
      });

      // 监听所有消息类型
      socket.on('hello', (data) => {
        handleMessage({ type: 'hello', data });
      });

      socket.on('stats', (data) => {
        handleMessage({ type: 'stats', data });
      });

      socket.on('dryEye', (data) => {
        handleMessage({ type: 'dryEye', data });
      });

      socket.on('sleepQuality', (data) => {
        handleMessage({ type: 'sleepQuality', data });
      });

      socket.on('fatigue', (data) => {
        handleMessage({ type: 'fatigue', data });
      });

      socket.on('bluetooth_data', (data) => {
        handleMessage({ type: 'bluetooth_data', data });
      });

      socket.on('pong', (data) => {
        handleMessage({ type: 'pong', data });
      });

      socket.on('connect_error', (error) => {
        console.error(`[WS] ${module} 模块连接错误:`, error);
        setStatus('error');
        onError?.(error);
      });

      socket.on('disconnect', (reason) => {
        const reasonText = reason === 'io server disconnect' ? '服务端主动断开' :
                          reason === 'io client disconnect' ? '客户端主动断开' :
                          reason === 'ping timeout' ? '心跳超时' : `未知原因 (${reason})`;
        console.log(`[WS] ${module} 模块连接关闭 | reason: ${reasonText}`);
        stopHeartbeat();
        setStatus('disconnected');
        onDisconnect?.();

        if (!isManualDisconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[WS] 尝试第 ${reconnectAttemptsRef.current}/${maxReconnectAttempts} 次重连... (延迟 ${reconnectDelay}ms)`);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.warn(`[WS] 已达到最大重连次数 (${maxReconnectAttempts})`);
        }
      });

      socketRef.current = socket;
    } catch (error) {
      console.error(`[WS] ${module} 模块连接异常:`, error);
      setStatus('error');
    }
  }, [module, getSocketUrl, handleMessage, startHeartbeat, stopHeartbeat, onConnect, onDisconnect, onError, reconnectDelay, maxReconnectAttempts, heartbeatInterval]);

  // 断开连接
  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    stopHeartbeat();
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    
    setStatus('disconnected');
    console.log(`[WS] ${module} 模块已手动断开`);
  }, [module, stopHeartbeat]);

  // 重连
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      connect();
    }, 500);
  }, [disconnect, connect]);

  // 发送消息
  const sendMessage = useCallback((msg: WebSocketMessage) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit(msg.type, msg.data);
    }
  }, []);

  // 获取统计
  const getStats = useCallback(() => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('stats');
    }
  }, []);

  // 获取最新数据
  const getLatest = useCallback(() => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('latest');
    }
  }, []);

  // 自动连接
  useEffect(() => {
    if (autoConnect && module !== 'gateway') {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, module, connect, disconnect]);

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
