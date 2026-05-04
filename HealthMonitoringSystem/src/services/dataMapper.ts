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
 */
export function mapFatigueData(backend: BackendFatigueData): UnifiedMetricData {
  console.log("[DataMapper] Raw fatigue data received:", JSON.stringify(backend, null, 2));

  // 根据评分确定颜色
  const getScoreColor = (score: number): 'green' | 'yellow' | 'red' => {
    if (score < 40) return 'green';   // 精神好
    if (score < 70) return 'yellow';  // 轻度疲劳
    return 'red';                      // 疲劳警告
  };

  // 数据验证
  const validateData = (data: BackendFatigueData): boolean => {
    if (typeof data.fatigueScore !== 'number' || isNaN(data.fatigueScore)) {
      console.error("[DataMapper] Validation failed: fatigueScore is invalid", data.fatigueScore);
      return false;
    }
    return true;
  };

  if (!validateData(backend)) {
    return {
      mainValue: 0,
      mainValueLabel: '疲劳评分',
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

  // 辅助指标
  const secondaryMetrics: SecondaryMetric[] = [
    {
      key: 'blinkRate',
      label: '眨眼频率',
      value: typeof backend.blinkRate === 'number' ? backend.blinkRate : 0,
      unit: '次/分钟',
      progress: Math.min(100, ((typeof backend.blinkRate === 'number' ? backend.blinkRate : 0) / 30) * 100)
    },
    {
      key: 'avgBlinkDuration',
      label: '平均眨眼时长',
      value: Math.round(typeof backend.avgBlinkDuration === 'number' ? backend.avgBlinkDuration : 0),
      unit: 'ms',
      progress: Math.min(100, ((typeof backend.avgBlinkDuration === 'number' ? backend.avgBlinkDuration : 0) / 500) * 100)
    },
    {
      key: 'alertLevel',
      label: '预警等级',
      value: backend.alertLevel,
      unit: ''
    }
  ];

  return {
    mainValue: Math.round(backend.fatigueScore),
    mainValueLabel: '疲劳评分',
    mainValueUnit: '分',
    mainValueColor: getScoreColor(backend.fatigueScore),
    secondaryMetrics,
    chartData: [],  // 由调用方填充历史数据
    status: {
      connected: true,
      signalQuality: 100,
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
 */
export function mapModuleData(module: ModuleType, backendData: any): UnifiedMetricData | null {
  if (!backendData) return null;

  try {
    switch (module) {
      case 'fatigue':
        return mapFatigueData(backendData);
      case 'dry-eye':
        return mapDryEyeData(backendData);
      case 'sleep':
        return mapSleepData(backendData);
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