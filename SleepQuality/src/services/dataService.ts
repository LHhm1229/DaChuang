// 数据服务 - 模拟实时数据流
export interface SleepData {
  eyeStatus: 'open' | 'closing' | 'closed';
  sleepScore: number; // 这里表示睡眠质量评分，越高越好
  movementRate: number; // 体动幅度/翻身指数
  eyelidStatus: {
    leftEye: 'open' | 'closing' | 'closed';
    rightEye: 'open' | 'closing' | 'closed';
    blinkDuration: number; // 眨眼/眼动持续时间(ms)
    eyeClosureRatio: number; // 睡眠稳定度指标(0-100%)
  };
  sensorStatus: {
    connected: boolean;
    signalQuality: number;
    batteryLevel: number;
  };
  alertLevel: 'normal' | 'warning' | 'danger';
  monitoringDuration: string;
  lastUpdate: string;
  sleepStage?: 'awake' | 'light' | 'deep' | 'rem';
  movementIndex?: number;
  sleepStability?: number;
  // 新增眼部状态检测
  eyeState: '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼' | '快速眼动'; // 当前眼部状态
  // 算法输出字段
  remDensity?: number;
  semCount?: number;
  remEnergy?: number;
  semEnergy?: number;
  remSemRatio?: number;
  signalStd?: number;
  totalMinutes?: number;
  tstMinutes?: number;
  sleepEfficiency?: number;
  currentStageName?: string;
}

// 模拟数据生成器
class DataGenerator {
  private baseSleepScore = 75;
  private sleepTrend = 0; // 睡眠质量趋势
  private movementRateBase = 8;
  private isConnected = true;
  private sensitivity = 75; // 检测灵敏度

  // 生成更真实的睡眠质量数据
  generateRealisticData(): SleepData {
    const now = new Date();
    
    // 模拟睡眠质量随时间波动
    this.sleepTrend += (Math.random() - 0.5) * 6; // 轻微波动
    this.sleepTrend = Math.max(-20, Math.min(20, this.sleepTrend));
    
    const sleepScore = Math.max(30, Math.min(100, this.baseSleepScore + this.sleepTrend + (Math.random() - 0.5) * 8));
    
    // 根据睡眠质量调整体动指数
    const movementIndex = Math.max(1, Math.min(40, this.movementRateBase + (90 - sleepScore) * 0.25 + (Math.random() - 0.5) * 6));

    // 睡眠阶段映射
    let sleepStage: 'awake' | 'light' | 'deep' | 'rem';
    if (sleepScore >= 80) {
      sleepStage = 'deep';
    } else if (sleepScore >= 65) {
      sleepStage = 'rem';
    } else if (sleepScore >= 45) {
      sleepStage = 'light';
    } else {
      sleepStage = 'awake';
    }

    // 眼部状态与睡眠阶段相关
    let eyeStatus: 'open' | 'closing' | 'closed';
    if (sleepStage === 'deep') {
      eyeStatus = 'closed';
    } else if (sleepStage === 'rem') {
      eyeStatus = Math.random() > 0.4 ? 'closing' : 'closed';
    } else if (sleepStage === 'light') {
      eyeStatus = Math.random() > 0.6 ? 'closing' : 'open';
    } else {
      eyeStatus = 'open';
    }

    const stability = Math.max(30, Math.min(100, sleepScore + (Math.random() - 0.5) * 12));
    const blinkDuration = Math.max(120, Math.min(420, 180 + (100 - sleepScore) * 1.2 + (Math.random() - 0.5) * 80));

    const leftEyeStatus = eyeStatus === 'open' ? 'open' : Math.random() > 0.5 ? 'closing' : 'closed';
    const rightEyeStatus = eyeStatus === 'open' ? 'open' : Math.random() > 0.5 ? 'closing' : 'closed';

    // 根据睡眠阶段和体动指数生成眼部状态检测结果
    let eyeState: '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼' | '快速眼动';
    if (sleepStage === 'awake') {
      // 清醒状态：频繁眨眼或正常眨眼
      if (movementIndex > 20) {
        eyeState = '频繁眨眼';
      } else {
        eyeState = '正常眨眼';
      }
    } else if (sleepStage === 'light') {
      // 浅睡状态：慢速眨眼或闭眼
      if (movementIndex > 15) {
        eyeState = '慢速眨眼';
      } else {
        eyeState = '闭眼';
      }
    } else if (sleepStage === 'deep') {
      // 深睡状态：闭眼
      eyeState = '闭眼';
    } else if (sleepStage === 'rem') {
      // REM状态：快速眼动
      eyeState = '快速眼动';
    } else {
      eyeState = '正常眨眼';
    }

    const signalQuality = Math.max(70, Math.min(100, 95 - (Math.random() * 20)));
    const batteryLevel = Math.max(60, Math.min(100, 85 - (Math.random() * 20)));

    if (Math.random() > 0.98) {
      this.isConnected = !this.isConnected;
    }

    return {
      eyeStatus,
      sleepScore: Math.round(sleepScore),
      movementRate: Math.round(movementIndex),
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
      alertLevel: sleepScore >= 60 ? 'normal' : sleepScore >= 40 ? 'warning' : 'danger',
      monitoringDuration: this.formatSleepTime(now),
      lastUpdate: now.toLocaleTimeString("zh-CN"),
      sleepStage,
      movementIndex: Math.round(movementIndex),
      sleepStability: Math.round(stability),
      eyeState,
      remDensity: Math.random() * 5,
      semCount: Math.floor(Math.random() * 10),
      remEnergy: Math.random() * 100,
      semEnergy: Math.random() * 100,
      remSemRatio: Math.random() * 2,
      signalStd: Math.random() * 0.01,
      totalMinutes: Math.floor(Math.random() * 480),
      tstMinutes: Math.floor(Math.random() * 420),
      sleepEfficiency: Math.floor(70 + Math.random() * 25),
    };
  }

  // 设置检测灵敏度
  setSensitivity(value: number) {
    this.sensitivity = value;
  }

  private formatSleepTime(date: Date): string {
    // 模拟睡眠时间从某个固定时间开始
    const startTime = new Date(date);
    startTime.setHours(22, 0, 0, 0); // 假设从晚上10点开始
    
    const diffMs = date.getTime() - startTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${diffHours}小时${diffMinutes}分钟`;
  }
}

// 数据服务类
class DataService {
  private generator = new DataGenerator();
  private listeners: ((data: SleepData) => void)[] = [];
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
  addListener(callback: (data: SleepData) => void) {
    this.listeners.push(callback);
  }

  // 移除数据监听器
  removeListener(callback: (data: SleepData) => void) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  // 通知所有监听器
  private notifyListeners(data: SleepData) {
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
  getCurrentData(): SleepData {
    return this.generator.generateRealisticData();
  }

  // 检查是否正在运行
  isDataStreamRunning(): boolean {
    return this.isRunning;
  }
}

// 导出单例实例
export const dataService = new DataService();
