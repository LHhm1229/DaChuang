// 数据服务 - 模拟实时数据流
export interface DryEyeData {
  eyeStatus: 'open' | 'closing' | 'closed';
  eyeHealthScore: number; // 风险分数的补数 (100 - riskScore)，分数越高越健康
  dryEyeRiskScore: number; // 直接对应算法输出的风险分数
  dryEyeRiskLevel: '低风险' | '中风险' | '高风险'; // 对应算法输出的等级
  blinkRate: number; // 眨眼频率
  avgBlinkDuration: number; // 平均眨眼时长 (ms)
  incompleteBlinkRatio: number; // 不完全眨眼占比 (%)
  longBlinkRatio: number; // 长眨眼占比 (%)
  totalBlinks: number; // 总眨眼次数
  incompleteBlinks: number; // 不完全眨眼次数
  longBlinks: number; // 长眨眼次数
  eyelidStatus: {
    leftEye: 'open' | 'closing' | 'closed';
    rightEye: 'open' | 'closing' | 'closed';
    blinkDuration: number; // 最近一次眨眼持续时间(ms)
    eyeClosureRatio: number; // 眼部闭合占比 (%)
  };
  sensorStatus: {
    connected: boolean;
    signalQuality: number;
    batteryLevel: number;
  };
  alertLevel: 'normal' | 'warning' | 'danger';
  monitoringTime: string;
  lastUpdate: string;
  eyeState: '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼'; // 当前眼部状态
}

// 模拟数据生成器
class DataGenerator {
  private baseHealthScore = 75;
  private healthTrend = 0; // 健康趋势
  private blinkRateBase = 12;
  private isConnected = true;
  private sensitivity = 75; // 检测灵敏度

  // 生成更真实的眼部健康数据
  generateRealisticData(): DryEyeData {
    const now = new Date();
    
    // 模拟健康评分随时间波动
    this.healthTrend += (Math.random() - 0.5) * 6; // 轻微波动
    this.healthTrend = Math.max(-20, Math.min(20, this.healthTrend));
    
    const healthScore = Math.max(30, Math.min(100, this.baseHealthScore + this.healthTrend + (Math.random() - 0.5) * 8));
    
    // 根据健康评分调整眨眼频率
    const blinkRate = Math.max(5, Math.min(40, this.blinkRateBase + (90 - healthScore) * 0.25 + (Math.random() - 0.5) * 6));

    // 眼部状态映射逻辑
    const stateRandom = Math.random();
    let eyeState: '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼';
    if (stateRandom < 0.2) {
      eyeState = '睁眼';
    } else if (stateRandom < 0.35) {
      eyeState = '闭眼';
    } else if (stateRandom < 0.5) {
      eyeState = '频繁眨眼';
    } else if (stateRandom < 0.65) {
      eyeState = '慢速眨眼';
    } else {
      eyeState = '正常眨眼';
    }

    // 眼部状态
    let eyeStatus: 'open' | 'closing' | 'closed';
    if (healthScore < 40) {
      eyeStatus = Math.random() > 0.3 ? 'closing' : 'closed';
    } else if (healthScore < 60) {
      eyeStatus = Math.random() > 0.5 ? 'closing' : 'open';
    } else {
      eyeStatus = 'open';
    }

    const stability = Math.max(30, Math.min(100, healthScore + (Math.random() - 0.5) * 12));
    const blinkDuration = Math.max(120, Math.min(420, 180 + (100 - healthScore) * 1.2 + (Math.random() - 0.5) * 80));

    const leftEyeStatus = eyeStatus === 'open' ? 'open' : Math.random() > 0.5 ? 'closing' : 'closed';
    const rightEyeStatus = eyeStatus === 'open' ? 'open' : Math.random() > 0.5 ? 'closing' : 'closed';

    const signalQuality = Math.max(70, Math.min(100, 95 - (Math.random() * 20)));
    const batteryLevel = Math.max(60, Math.min(100, 85 - (Math.random() * 20)));

    if (Math.random() > 0.98) {
      this.isConnected = !this.isConnected;
    }

    const riskScore = 100 - healthScore;
    const riskLevel = riskScore < 30 ? '低风险' : riskScore < 60 ? '中风险' : '高风险';

    return {
      eyeStatus,
      eyeHealthScore: Math.round(healthScore),
      dryEyeRiskScore: Math.round(riskScore),
      dryEyeRiskLevel: riskLevel,
      blinkRate: Math.round(blinkRate),
      avgBlinkDuration: Math.round(blinkDuration),
      incompleteBlinkRatio: Math.round(Math.random() * 30),
      longBlinkRatio: Math.round(Math.random() * 20),
      totalBlinks: Math.round(Math.random() * 50) + 10,
      incompleteBlinks: Math.round(Math.random() * 5),
      longBlinks: Math.round(Math.random() * 5),
      eyelidStatus: {
        leftEye: leftEyeStatus,
        rightEye: rightEyeStatus,
        blinkDuration: Math.round(blinkDuration),
        eyeClosureRatio: Math.round(stability),
      },
      sensorStatus: {
        connected: this.isConnected,
        signalQuality: Math.round(signalQuality),
        batteryLevel: Math.round(batteryLevel),
      },
      alertLevel: healthScore >= 60 ? 'normal' : healthScore >= 40 ? 'warning' : 'danger',
      monitoringTime: this.formatMonitoringTime(now),
      lastUpdate: now.toLocaleTimeString("zh-CN"),
      eyeState,
    };
  }

  // 设置检测灵敏度
  setSensitivity(value: number) {
    this.sensitivity = value;
  }

  private formatMonitoringTime(date: Date): string {
    // 模拟监测时间从当前时间往前推移
    const startTime = new Date(date);
    startTime.setHours(startTime.getHours() - 1); // 假设已经监测了1小时
    
    const diffMs = date.getTime() - startTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${diffHours}小时${diffMinutes}分钟`;
  }
}

// 数据服务类
class DataService {
  private generator = new DataGenerator();
  private listeners: ((data: DryEyeData) => void)[] = [];
  private intervalId: any = null;
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
  addListener(callback: (data: DryEyeData) => void) {
    this.listeners.push(callback);
  }

  // 移除数据监听器
  removeListener(callback: (data: DryEyeData) => void) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  // 通知所有监听器
  private notifyListeners(data: DryEyeData) {
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
  getCurrentData(): DryEyeData {
    return this.generator.generateRealisticData();
  }

  // 检查是否正在运行
  isDataStreamRunning(): boolean {
    return this.isRunning;
  }
}

// 导出单例实例
export const dataService = new DataService();
