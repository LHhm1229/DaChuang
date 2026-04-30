// 数据服务 - 模拟实时数据流
export interface FatigueData {
  eyeStatus: 'open' | 'closing' | 'closed';
  fatigueScore: number;
  blinkRate: number;
  eyelidStatus: {
    leftEye: 'open' | 'closing' | 'closed';
    rightEye: 'open' | 'closing' | 'closed';
    blinkDuration: number; // 眨眼持续时间(ms)
    eyeClosureRatio: number; // 眼睑闭合比例(0-100%)
  };
  sensorStatus: {
    connected: boolean;
    signalQuality: number;
    batteryLevel: number;
  };
  alertLevel: 'normal' | 'warning' | 'danger';
  drivingTime: string;
  lastUpdate: string;
}

// 模拟数据生成器
class DataGenerator {
  private baseFatigueScore = 20;
  private fatigueTrend = 0; // 疲劳度趋势
  private blinkRateBase = 15;
  private isConnected = true;
  private sensitivity = 75; // 检测灵敏度

  // 生成更真实的疲劳数据
  generateRealisticData(): FatigueData {
    const now = new Date();
    
    // 模拟疲劳度随时间增加
    this.fatigueTrend += (Math.random() - 0.4) * 2; // 轻微上升趋势
    this.fatigueTrend = Math.max(-10, Math.min(30, this.fatigueTrend)); // 限制范围
    
    const fatigueScore = Math.max(0, Math.min(100, this.baseFatigueScore + this.fatigueTrend + (Math.random() - 0.5) * 10));
    
    // 根据疲劳度调整眨眼频率
    const blinkRate = Math.max(8, Math.min(40, this.blinkRateBase + (fatigueScore - 20) * 0.3 + (Math.random() - 0.5) * 5));
    
    // 根据检测灵敏度调整疲劳评分阈值
    const sensitivityFactor = this.sensitivity / 75; // 75为基准值
    const adjustedFatigueScore = fatigueScore * sensitivityFactor;
    
    // 根据疲劳度确定眼部状态（考虑灵敏度）
    let eyeStatus: 'open' | 'closing' | 'closed';
    const warningThreshold = 30 / sensitivityFactor;
    const dangerThreshold = 70 / sensitivityFactor;
    
    if (adjustedFatigueScore < warningThreshold) {
      eyeStatus = 'open';
    } else if (adjustedFatigueScore < dangerThreshold) {
      eyeStatus = Math.random() > 0.7 ? 'closing' : 'open';
    } else {
      eyeStatus = Math.random() > 0.5 ? 'closed' : 'closing';
    }
    
    // 眼睑状态随疲劳度变化（考虑灵敏度）
    const eyeClosureRatio = Math.min(100, Math.max(0, (adjustedFatigueScore - 20) * 2 + (Math.random() - 0.5) * 10));
    const blinkDuration = Math.max(100, Math.min(500, 200 + (adjustedFatigueScore - 20) * 5 + (Math.random() - 0.5) * 100));
    
    // 左右眼状态（可能不同步，考虑灵敏度）
    const leftEyeStatus = adjustedFatigueScore < warningThreshold ? 'open' : 
                         adjustedFatigueScore < dangerThreshold ? (Math.random() > 0.7 ? 'closing' : 'open') : 
                         Math.random() > 0.5 ? 'closed' : 'closing';
    const rightEyeStatus = adjustedFatigueScore < warningThreshold ? 'open' : 
                          adjustedFatigueScore < dangerThreshold ? (Math.random() > 0.7 ? 'closing' : 'open') : 
                          Math.random() > 0.5 ? 'closed' : 'closing';
    
    // 传感器状态
    const signalQuality = Math.max(70, Math.min(100, 95 - (Math.random() * 20)));
    const batteryLevel = Math.max(60, Math.min(100, 85 - (Math.random() * 20)));
    
    // 偶尔模拟连接断开
    if (Math.random() > 0.98) {
      this.isConnected = !this.isConnected;
    }

    return {
      eyeStatus,
      fatigueScore: Math.round(fatigueScore),
      blinkRate: Math.round(blinkRate),
      eyelidStatus: {
        leftEye: leftEyeStatus,
        rightEye: rightEyeStatus,
        blinkDuration: Math.round(blinkDuration),
        eyeClosureRatio: Math.round(eyeClosureRatio),
      },
      sensorStatus: {
        connected: this.isConnected,
        signalQuality: Math.round(signalQuality),
        batteryLevel: Math.round(batteryLevel),
      },
      alertLevel: adjustedFatigueScore < warningThreshold ? 'normal' : adjustedFatigueScore < dangerThreshold ? 'warning' : 'danger',
      drivingTime: this.formatDrivingTime(now),
      lastUpdate: now.toLocaleTimeString("zh-CN"),
    };
  }

  // 设置检测灵敏度
  setSensitivity(value: number) {
    this.sensitivity = value;
  }

  private formatDrivingTime(date: Date): string {
    // 模拟驾驶时间从某个固定时间开始
    const startTime = new Date(date);
    startTime.setHours(8, 0, 0, 0); // 假设从早上8点开始
    
    const diffMs = date.getTime() - startTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${diffHours}小时${diffMinutes}分钟`;
  }
}

// 数据服务类
class DataService {
  private generator = new DataGenerator();
  private listeners: ((data: FatigueData) => void)[] = [];
  private intervalId: NodeJS.Timeout | null = null;
  private isRunning = false;
  private sensitivity = 75; // 默认检测灵敏度

  // 开始实时数据流
  startRealTimeData(intervalMs: number = 2000) {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.intervalId = setInterval(() => {
      const data = this.generator.generateRealisticData();
      this.notifyListeners(data);
    }, intervalMs);
  }

  // 停止实时数据流
  stopRealTimeData() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
  }

  // 添加数据监听器
  addListener(callback: (data: FatigueData) => void) {
    this.listeners.push(callback);
  }

  // 移除数据监听器
  removeListener(callback: (data: FatigueData) => void) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  // 通知所有监听器
  private notifyListeners(data: FatigueData) {
    this.listeners.forEach(listener => listener(data));
  }

  // 设置检测灵敏度
  setSensitivity(value: number) {
    this.sensitivity = value;
    this.generator.setSensitivity(value);
  }

  // 获取检测灵敏度
  getSensitivity(): number {
    return this.sensitivity;
  }

  // 获取单次数据
  getCurrentData(): FatigueData {
    return this.generator.generateRealisticData();
  }

  // 检查是否正在运行
  isDataStreamRunning(): boolean {
    return this.isRunning;
  }
}

// 导出单例实例
export const dataService = new DataService();
