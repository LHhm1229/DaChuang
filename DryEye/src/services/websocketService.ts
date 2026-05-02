// 定义WebSocket数据接口，与后端推送的数据格式保持一致
export interface WSDryEyeData {
    lastUpdate: string;
    dryEyeRiskScore: number; // 算法输出的风险分数 (0-100)
    dryEyeRiskLevel: '低风险' | '中风险' | '高风险'; // 算法输出的风险等级
    blinkRate: number; // 眨眼频率 (次/分钟)
    avgBlinkDuration: number; // 平均眨眼时长 (ms)
    eyeClosureRatio: number; // 眼部闭合占比 (%)
    incompleteBlinkRatio: number; // 不完全眨眼占比 (%)
    longBlinkRatio: number; // 长眨眼占比 (%)
    totalBlinks: number; // 总眨眼次数
    incompleteBlinks: number; // 不完全眨眼次数
    longBlinks: number; // 长眨眼次数
    sensorStatus: {
      signalQuality: number;
    };
    // 可选：后端如果提供眼部状态，前端会自行归一化展示
    eyeState?: string;
  }
  
  // WebSocket服务单例
  class WebSocketService {
    private socket: WebSocket | null = null;
    private url: string;
    private listeners: ((data: WSDryEyeData) => void)[] = [];
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectInterval = 3000; // 重连间隔3秒
  
    constructor(url: string = 'ws://localhost:3000/ws') {
      this.url = url;
    }
  
    // 连接WebSocket
    connect() {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        return;
      }
  
      try {
        this.socket = new WebSocket(this.url);
        
        // 连接成功
        this.socket.onopen = () => {
          console.log('WebSocket连接成功');
          this.reconnectAttempts = 0; // 重置重连次数
        };
  
        // 接收消息
        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as WSDryEyeData;
            this.notifyListeners(data);
          } catch (error) {
            console.error('解析WebSocket数据失败:', error);
          }
        };
  
        // 连接关闭
        this.socket.onclose = (event) => {
          console.log(`WebSocket连接关闭: ${event.code} - ${event.reason}`);
          this.socket = null;
          
          // 自动重连逻辑
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连(${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this.connect(), this.reconnectInterval);
          }
        };
  
        // 连接错误
        this.socket.onerror = (error) => {
          console.error('WebSocket错误:', error);
        };
      } catch (error) {
        console.error('创建WebSocket连接失败:', error);
      }
    }
  
    // 断开连接
    disconnect() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      this.reconnectAttempts = this.maxReconnectAttempts; // 停止自动重连
    }
  
    // 添加数据监听器
    addListener(listener: (data: WSDryEyeData) => void) {
      this.listeners.push(listener);
    }
  
    // 移除数据监听器
    removeListener(listener: (data: WSDryEyeData) => void) {
      this.listeners = this.listeners.filter(l => l !== listener);
    }
  
    // 通知所有监听器
    private notifyListeners(data: WSDryEyeData) {
      this.listeners.forEach(listener => listener(data));
    }
  
    // 检查连接状态
    isConnected(): boolean {
      return this.socket?.readyState === WebSocket.OPEN;
    }
  }
  
  // 创建单例实例
  export const websocketService = new WebSocketService();