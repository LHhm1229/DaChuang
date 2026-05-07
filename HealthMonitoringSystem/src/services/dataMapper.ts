/**
 * dataMapper.ts
 * 统一数据映射层 - 解耦后端数据与前端UI
 * 将后端各模块数据统一转换为前端期望的格式
 */

import { ModuleType } from '../hooks/useDynamicWebSocket';

// =========================
// 类型定义
// =========================

// 后端原始数据类型
export interface BackendFatigueData {
  fatigueScore: number;
  fatigueLevel: string;
  blinkRate: number;
  avgBlinkDuration: number;
  alertLevel: string;
  eyeStatus?: string;
  drivingTime?: string;
}

export interface BackendDryEyeData {
  blinkRate: number;
  avgBlinkDuration: number;
  eyeClosureRatio: number;
  incompleteBlinkRatio: number;
  longBlinkRatio: number;
  dryEyeRiskScore: number;
  dryEyeRiskLevel: string;
  totalBlinks: number;
  incompleteBlinks: number;
  longBlinks: number;
}

export interface BackendSleepData {
  totalMinutes: number;
  tstMinutes: number;
  sleepEfficiency: number;
  qualityScore: number;
  currentStage: number;
  currentStageName: string;
  stageSequence: number[];
  stageDurations: {
    wake: number;
    n1: number;
    n2: number;
    n3: number;
    rem: number;
  };
  stagePercentages: {
    wake: number;
    n1: number;
    n2: number;
    n3: number;
    rem: number;
  };
  rem_density?: number;
  sem_count?: number;
  signal_std?: number;
}

// 前端统一数据类型
export interface UnifiedMetricData {
  // 主指标
  mainValue: number;
  mainValueLabel: string;
  mainValueUnit: string;
  mainValueColor: 'green' | 'yellow' | 'red' | 'white';

  // 辅助指标
  secondaryMetrics: SecondaryMetric[];

  // 图表数据
  chartData: ChartDataPoint[];

  // 状态信息
  status: {
    connected: boolean;
    signalQuality: number;
    lastUpdate: string;
  };
}

export interface SecondaryMetric {
  key: string;
  label: string;
  value: string | number;
  unit: string;
  progress?: number;  // 用于进度条显示
  color?: string;
}

export interface ChartDataPoint {
  time: string;
  [key: string]: string | number;
}

// =========================
// 映射函数
// =========================

/**
 * 疲劳数据映射
 * 支持两种数据格式：
 * 1. 原始蓝牙数据格式：{ rawData: [2.5, 2.8, ...], timestamp: ... }
 * 2. 已计算的疲劳数据格式：{ fatigueScore: 38.8, blinkRate: 111.1, ... }
 */
export function mapFatigueData(backend: BackendFatigueData | any): UnifiedMetricData {
  console.log("[DataMapper] Raw fatigue data received:", JSON.stringify(backend, null, 2));

  // 根据评分确定颜色
  const getScoreColor = (score: number): 'green' | 'yellow' | 'red' => {
    if (score < 40) return 'green';   // 精神好
    if (score < 70) return 'yellow';  // 轻度疲劳
    return 'red';                      // 疲劳警告
  };

  // 提取实际数据（处理嵌套格式）
  let actualData = backend;
  
  // 处理嵌套格式 { type: 'xxx', data: {...} }
  if (backend.data) {
    // 如果 data 是字符串，尝试解析为 JSON
    if (typeof backend.data === 'string') {
      try {
        actualData = JSON.parse(backend.data);
        console.log("[DataMapper] 解析JSON字符串");
      } catch (e) {
        console.error("[DataMapper] 解析JSON失败:", e);
      }
    } 
    // 如果 data 是对象，直接使用
    else if (typeof backend.data === 'object') {
      actualData = backend.data;
      console.log("[DataMapper] 提取嵌套对象");
    }
  }
  
  // 检查是否是原始蓝牙数据格式
  const isRawData = actualData && actualData.rawData && Array.isArray(actualData.rawData);
  
  let fatigueScore: number;
  let blinkRate: number;
  let avgBlinkDuration: number;
  let alertLevel: string;

  if (isRawData) {
    // 处理原始蓝牙数据 - 计算疲劳评分
    console.log("[DataMapper] Processing raw bluetooth data");
    const rawValues = actualData.rawData;
    const avgValue = rawValues.reduce((a: number, b: number) => a + b, 0) / rawValues.length;
    
    // 简单的疲劳评分计算：基于原始数据的值
    fatigueScore = Math.min(100, Math.max(0, Math.round(avgValue * 30)));
    blinkRate = Math.round(20 + (avgValue * 5));
    avgBlinkDuration = Math.round(200 + (avgValue * 50));
    alertLevel = fatigueScore < 40 ? '正常' : fatigueScore < 70 ? '警告' : '危险';
  } else if (typeof actualData.fatigueScore === 'number') {
    // 处理已计算的疲劳数据
    fatigueScore = actualData.fatigueScore;
    blinkRate = typeof actualData.blinkRate === 'number' ? actualData.blinkRate : 0;
    avgBlinkDuration = typeof actualData.avgBlinkDuration === 'number' ? actualData.avgBlinkDuration : 0;
    alertLevel = actualData.alertLevel || (fatigueScore < 40 ? '正常' : fatigueScore < 70 ? '警告' : '危险');
  } else {
    // 数据格式无效
    console.error("[DataMapper] Validation failed: No valid data found");
    return {
      mainValue: 0,
      mainValueLabel: '疲劳评分',
      mainValueUnit: '分',
      mainValueColor: 'white',
      secondaryMetrics: [],
      chartData: [],
      status: {
        connected: false,
        signalQuality: actualData.signalQuality || 0,
        lastUpdate: new Date().toISOString()
      }
    };
  }

  // 辅助指标
  const secondaryMetrics: SecondaryMetric[] = [
    {
      key: 'blinkRate',
      label: '眨眼频率',
      value: blinkRate,
      unit: '次/分钟',
      progress: Math.min(100, (blinkRate / 30) * 100)
    },
    {
      key: 'avgBlinkDuration',
      label: '平均眨眼时长',
      value: Math.round(avgBlinkDuration),
      unit: 'ms',
      progress: Math.min(100, (avgBlinkDuration / 500) * 100)
    },
    {
      key: 'alertLevel',
      label: '预警等级',
      value: alertLevel,
      unit: ''
    }
  ];

  return {
    mainValue: Math.round(fatigueScore),
    mainValueLabel: '疲劳评分',
    mainValueUnit: '分',
    mainValueColor: getScoreColor(fatigueScore),
    secondaryMetrics,
    chartData: [],
    status: {
      connected: true,
      signalQuality: actualData.signalQuality || 100,
      lastUpdate: new Date().toISOString()
    }
  };
}

/**
 * 干眼症数据映射
 */
export function mapDryEyeData(backend: BackendDryEyeData): UnifiedMetricData {
  console.log("[DataMapper] Raw dry eye data received:", JSON.stringify(backend, null, 2));

  const getScoreColor = (score: number): 'green' | 'yellow' | 'red' => {
    if (score < 30) return 'green';
    if (score < 60) return 'yellow';
    return 'red';
  };

  const validateData = (data: BackendDryEyeData): boolean => {
    if (typeof data.dryEyeRiskScore !== 'number' || isNaN(data.dryEyeRiskScore)) {
      console.error("[DataMapper] Validation failed: dryEyeRiskScore is invalid", data.dryEyeRiskScore);
      return false;
    }
    return true;
  };

  if (!validateData(backend)) {
    return {
      mainValue: 0,
      mainValueLabel: '干眼风险',
      mainValueUnit: '%',
      mainValueColor: 'white',
      secondaryMetrics: [],
      chartData: [],
      status: {
        connected: false,
        signalQuality: 0,
        lastUpdate: new Date().toISOString()
      }
    };
  }

  const secondaryMetrics: SecondaryMetric[] = [
    {
      key: 'blinkRate',
      label: '眨眼频率',
      value: backend.blinkRate,
      unit: '次/分钟',
      progress: Math.min(100, (backend.blinkRate / 40) * 100)
    },
    {
      key: 'avgBlinkDuration',
      label: '平均眨眼时长',
      value: Math.round(backend.avgBlinkDuration),
      unit: 'ms',
      progress: Math.min(100, (backend.avgBlinkDuration / 400) * 100)
    },
    {
      key: 'eyeClosureRatio',
      label: '眼睛闭合比例',
      value: backend.eyeClosureRatio,
      unit: '%',
      progress: Math.min(100, backend.eyeClosureRatio)
    }
  ];

  return {
    mainValue: Math.round(backend.dryEyeRiskScore),
    mainValueLabel: '干眼风险',
    mainValueUnit: '%',
    mainValueColor: getScoreColor(backend.dryEyeRiskScore),
    secondaryMetrics,
    chartData: [],
    status: {
      connected: true,
      signalQuality: 100,
      lastUpdate: new Date().toISOString()
    }
  };
}

/**
 * 睡眠数据映射
 */
export function mapSleepData(backend: BackendSleepData): UnifiedMetricData {
  console.log("[DataMapper] Raw sleep quality data received:", JSON.stringify(backend, null, 2));

  const getScoreColor = (score: number): 'green' | 'yellow' | 'red' => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  const validateData = (data: BackendSleepData): boolean => {
    if (typeof data.qualityScore !== 'number' || isNaN(data.qualityScore)) {
      console.error("[DataMapper] Validation failed: qualityScore is invalid", data.qualityScore);
      return false;
    }
    return true;
  };

  if (!validateData(backend)) {
    return {
      mainValue: 0,
      mainValueLabel: '睡眠质量',
      mainValueUnit: '分',
      mainValueColor: 'white',
      secondaryMetrics: [],
      chartData: [],
      status: {
        connected: false,
        signalQuality: 0,
        lastUpdate: new Date().toISOString()
      }
    };
  }

  const stageNames: Record<number, string> = {
    0: '清醒',
    1: '浅睡N1',
    2: '浅睡N2',
    3: '深睡',
    4: 'REM'
  };

  const secondaryMetrics: SecondaryMetric[] = [
    {
      key: 'currentStage',
      label: '当前阶段',
      value: backend.currentStageName || stageNames[backend.currentStage] || '未知',
      unit: ''
    },
    {
      key: 'remDensity',
      label: 'REM密度',
      value: backend.rem_density?.toFixed(2) || '0.00',
      unit: '',
      progress: Math.min(100, (backend.rem_density || 0) * 100)
    },
    {
      key: 'sleepEfficiency',
      label: '睡眠效率',
      value: backend.sleepEfficiency,
      unit: '%',
      progress: Math.min(100, backend.sleepEfficiency)
    }
  ];

  return {
    mainValue: Math.round(backend.qualityScore),
    mainValueLabel: '睡眠质量',
    mainValueUnit: '分',
    mainValueColor: getScoreColor(backend.qualityScore),
    secondaryMetrics,
    chartData: [],
    status: {
      connected: true,
      signalQuality: 100,
      lastUpdate: new Date().toISOString()
    }
  };
}

/**
 * 统一数据映射入口
 * 处理多种数据格式：
 * 1. 直接的后端数据对象
 * 2. 嵌套格式 { data: {...} }
 * 3. WebSocket 消息格式 { type: 'xxx', data: {...} }
 */
export function mapModuleData(module: ModuleType, backendData: any): UnifiedMetricData | null {
  if (!backendData) {
    console.log('[DataMapper] backendData 为空');
    return null;
  }

  // 直接使用传入的数据（App.tsx 已经提取了 msg.data）
  let actualData = backendData;

  console.log(`[DataMapper] 处理${module}数据 | 数据键:`, Object.keys(actualData));

  try {
    switch (module) {
      case 'fatigue':
        return mapFatigueData(actualData);
      case 'dry-eye':
        return mapDryEyeData(actualData);
      case 'sleep':
        return mapSleepData(actualData);
      default:
        console.warn(`[DataMapper] 未知模块类型: ${module}`);
        return null;
    }
  } catch (error) {
    console.error(`[DataMapper] 映射${module}数据失败:`, error);
    return null;
  }
}

// =========================
// 便捷类型守卫
// =========================
export function isFatigueData(data: any): data is BackendFatigueData {
  return data && typeof data.fatigueScore === 'number';
}

export function isDryEyeData(data: any): data is BackendDryEyeData {
  return data && typeof data.dryEyeRiskScore === 'number';
}

export function isSleepData(data: any): data is BackendSleepData {
  return data && typeof data.qualityScore === 'number';
}

/**
 * 类型守卫联合 - 判断数据类型
 */
export function detectDataType(data: any): ModuleType | null {
  if (isFatigueData(data)) return 'fatigue';
  if (isDryEyeData(data)) return 'dry-eye';
  if (isSleepData(data)) return 'sleep';
  return null;
}