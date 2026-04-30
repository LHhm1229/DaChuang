import { useState, useEffect, useCallback } from 'react';

// 数据防抖函数
const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), wait);
  };
};

// WebSocket服务类
class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, ((data: any) => void)[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const listeners = this.listeners.get(data.type) || [];
        listeners.forEach(listener => listener(data.data));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.handleReconnect(url);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleReconnect(url: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(url), this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnect attempts reached');
    }
  }

  on(type: string, callback: (data: any) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)?.push(callback);
  }

  off(type: string, callback: (data: any) => void) {
    const listeners = this.listeners.get(type);
    if (listeners) {
      this.listeners.set(type, listeners.filter(l => l !== callback));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }
}

// 全局WebSocket服务实例
const wsService = new WebSocketService();

// 数据服务Hook
export const useDataService = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
  const [data, setData] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  // 防抖处理数据更新
  const debouncedSetData = useCallback(
    debounce((newData: any) => {
      setData(newData);
    }, 100),
    []
  );

  useEffect(() => {
    const wsUrl = `ws://localhost:${module === 'dry-eye' ? 3000 : module === 'sleep' ? 3001 : 3002}/ws`;
    
    wsService.connect(wsUrl);
    setIsConnected(true);

    // 监听数据
    const handleData = (newData: any) => {
      debouncedSetData(newData);
    };

    wsService.on(module === 'dry-eye' ? 'dryEye' : module === 'sleep' ? 'sleepQuality' : 'fatigue', handleData);

    return () => {
      wsService.off(module === 'dry-eye' ? 'dryEye' : module === 'sleep' ? 'sleepQuality' : 'fatigue', handleData);
    };
  }, [module, debouncedSetData]);

  return { data, isConnected };
};

// 模拟数据生成函数
export const generateMockData = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
  if (module === 'dry-eye') {
    return {
      blinkRate: Math.random() * 10 + 10,
      avgBlinkDuration: Math.random() * 100 + 200,
      eyeClosureRatio: Math.random() * 5 + 2,
      dryEyeRiskScore: Math.random() * 50 + 20,
      dryEyeRiskLevel: Math.random() > 0.5 ? '中风险' : '低风险'
    };
  } else if (module === 'sleep') {
    return {
      qualityScore: Math.random() * 30 + 70,
      currentStage: Math.floor(Math.random() * 5),
      currentStageName: ['清醒', '浅睡N1', '浅睡N2', '深睡', 'REM'][Math.floor(Math.random() * 5)],
      remDensity: Math.random() * 0.5,
      sleepEfficiency: Math.random() * 20 + 80
    };
  } else if (module === 'fatigue') {
    return {
      fatigueScore: Math.random() * 40 + 30,
      fatigueLevel: Math.random() > 0.5 ? '中度疲劳' : '轻度疲劳',
      blinkRate: Math.random() * 5 + 10,
      avgBlinkDuration: Math.random() * 100 + 250,
      alertLevel: Math.random() > 0.5 ? '警告' : '注意'
    };
  }
  return {};
};
