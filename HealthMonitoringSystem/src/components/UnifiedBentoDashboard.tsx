/**
 * UnifiedBentoDashboard.tsx - 统一Bento风格仪表盘
 * 数据与UI完全解耦 - 接收外部传入的实时数据
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { GlassCard, GlassCardContainer, GlassProgress, GlassBadge } from './ui';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { UnifiedMetricData, SecondaryMetric, ChartDataPoint } from '../services/dataMapper';

// 性能优化：使用React.memo包装玻璃态卡片组件
const MemoizedGlassCard = memo(GlassCard);
const MemoizedGlassCardContainer = memo(GlassCardContainer);
const MemoizedGlassProgress = memo(GlassProgress);
const MemoizedGlassBadge = memo(GlassBadge);

interface UnifiedBentoDashboardProps {
  module: 'dry-eye' | 'sleep' | 'fatigue';
  data: UnifiedMetricData | null;  // 接收外部传入的实时数据
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
}

// 模块配置
const moduleConfigs = {
  'dry-eye': {
    title: '干眼症监测',
    mainMetricLabel: '干眼风险',
    mainMetricUnit: '%',
    chartTitle: '眨眼频率与干眼风险趋势',
    chartSeries: [
      { key: 'blinkRate', name: '眨眼频率', color: '#16C79E' },
      { key: 'dryEyeRisk', name: '干眼风险', color: '#E86830' }
    ]
  },
  'sleep': {
    title: '睡眠质量检测',
    mainMetricLabel: '睡眠质量',
    mainMetricUnit: '分',
    chartTitle: '睡眠质量与REM密度趋势',
    chartSeries: [
      { key: 'sleepScore', name: '睡眠质量', color: '#4F1091' },
      { key: 'remDensity', name: 'REM密度', color: '#8A2BE2' }
    ]
  },
  'fatigue': {
    title: '疲劳驾驶预警',
    mainMetricLabel: '疲劳评分',
    mainMetricUnit: '分',
    chartTitle: '疲劳评分与眨眼持续时间趋势',
    chartSeries: [
      { key: 'fatigueScore', name: '疲劳评分', color: '#E86830' },
      { key: 'blinkDuration', name: '眨眼持续时间', color: '#FFA500' }
    ]
  }
};

// 生成模拟数据（当无实时数据时使用）
const generateMockData = (module: 'dry-eye' | 'sleep' | 'fatigue', count: number = 24): ChartDataPoint[] => {
  const data: ChartDataPoint[] = [];
  for (let i = 0; i < count; i++) {
    const timestamp = new Date();
    timestamp.setMinutes(timestamp.getMinutes() - (count - i));

    if (module === 'dry-eye') {
      data.push({
        time: timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        blinkRate: Math.random() * 10 + 10,
        dryEyeRisk: Math.random() * 50 + 20
      });
    } else if (module === 'sleep') {
      data.push({
        time: timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        sleepScore: Math.random() * 30 + 70,
        remDensity: Math.random() * 0.5
      });
    } else {
      data.push({
        time: timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        fatigueScore: Math.random() * 40 + 30,
        blinkDuration: Math.random() * 100 + 200
      });
    }
  }
  return data;
};

// 主题颜色配置
const getThemeColors = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
  if (module === 'dry-eye') {
    return {
      primary: '#16C79E',
      secondary: '#0F8C6E',
      bgGradient: 'from-emerald-950 to-teal-950',
      cardBg: 'bg-emerald-900/40',
      cardBorder: 'border-emerald-500/30',
      badgeColor: '#16C79E'
    };
  } else if (module === 'sleep') {
    return {
      primary: '#4F1091',
      secondary: '#8A2BE2',
      bgGradient: 'from-purple-950 to-indigo-950',
      cardBg: 'bg-purple-900/40',
      cardBorder: 'border-purple-500/30',
      badgeColor: '#4F1091'
    };
  } else {
    return {
      primary: '#E86830',
      secondary: '#FFA500',
      bgGradient: 'from-orange-950 to-amber-950',
      cardBg: 'bg-orange-900/40',
      cardBorder: 'border-orange-500/30',
      badgeColor: '#E86830'
    };
  }
};

// 获取主值颜色
const getMainValueColor = (value: number, module: 'dry-eye' | 'sleep' | 'fatigue'): string => {
  if (module === 'dry-eye') {
    if (value < 30) return 'text-emerald-400';
    if (value < 60) return 'text-yellow-400';
    return 'text-red-400';
  } else if (module === 'sleep') {
    if (value > 80) return 'text-emerald-400';
    if (value > 60) return 'text-yellow-400';
    return 'text-red-400';
  } else {
    if (value < 40) return 'text-emerald-400';
    if (value < 70) return 'text-yellow-400';
    return 'text-red-400';
  }
};

export const UnifiedBentoDashboard: React.FC<UnifiedBentoDashboardProps> = ({
  module,
  data,
  connectionStatus
}) => {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [mainValue, setMainValue] = useState<number | string>(0);
  const [secondaryMetrics, setSecondaryMetrics] = useState<SecondaryMetric[]>([]);
  const [signalQuality, setSignalQuality] = useState(85);

  const config = moduleConfigs[module];
  const theme = getThemeColors(module);

  // 处理实时数据更新
  useEffect(() => {
    if (data) {
      // 更新主值
      setMainValue(data.mainValue);

      // 更新辅助指标
      setSecondaryMetrics(data.secondaryMetrics);

      // 更新信号质量
      if (data.status.signalQuality) {
        setSignalQuality(data.status.signalQuality);
      }

      // 更新图表数据（追加新数据点）
      setChartData(prev => {
        const newPoint: ChartDataPoint = {
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          ...(module === 'dry-eye' && {
            blinkRate: data.secondaryMetrics[0]?.value as number || 0,
            dryEyeRisk: data.mainValue as number || 0
          }),
          ...(module === 'sleep' && {
            sleepScore: data.mainValue as number || 0,
            remDensity: parseFloat(data.secondaryMetrics[1]?.value as string) || 0
          }),
          ...(module === 'fatigue' && {
            fatigueScore: data.mainValue as number || 0,
            blinkDuration: data.secondaryMetrics[1]?.value as number || 0
          })
        };

        const updated = [...prev, newPoint];
        // 保持最近24个数据点
        return updated.slice(-24);
      });
    }
  }, [data, module]);

  // 模拟数据开关状态
  const [showMockData, setShowMockData] = useState(true);

  // 初始化模拟数据（仅当开启模拟时）
  useEffect(() => {
    if (chartData.length === 0 && showMockData) {
      setChartData(generateMockData(module));
    }
  }, [module, chartData.length, showMockData]);

  // 定时更新模拟数据（当无实时数据且开启模拟时）
  useEffect(() => {
    if (!data && showMockData) {
      const interval = setInterval(() => {
        setChartData(generateMockData(module));
        if (module === 'dry-eye') {
          setMainValue(Math.round(Math.random() * 50 + 20));
        } else if (module === 'sleep') {
          setMainValue(Math.round(Math.random() * 30 + 70));
        } else {
          setMainValue(Math.round(Math.random() * 40 + 30));
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [module, data, showMockData]);

  // 蓝牙连接状态
  const bluetoothConnected = connectionStatus === 'connected';

  return (
    <div className={`bento-grid min-h-screen bg-gradient-to-br ${theme.bgGradient} p-4 md:p-8`}>
      {/* 主指标卡片 */}
      <MemoizedGlassCardContainer layout="large">
        <MemoizedGlassCard variant="large" className={`${theme.cardBg} ${theme.cardBorder} border flex flex-col justify-center items-center`}>
          <h2 className="text-2xl font-bold mb-4 text-white">{config.mainMetricLabel}</h2>
          <div className={`text-6xl font-bold mb-4 ${getMainValueColor(mainValue as number, module)}`}>
            {mainValue}{config.mainMetricUnit}
          </div>
          <MemoizedGlassBadge className={`text-lg px-6 py-2 text-white`} style={{ backgroundColor: theme.badgeColor }}>
            {connectionStatus === 'connected' ? (
              module === 'dry-eye' ? '实时监测中' :
              module === 'sleep' ? '睡眠分析中' : '驾驶监测中'
            ) : (
              '等待连接...'
            )}
          </MemoizedGlassBadge>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>

      {/* 辅助指标卡片 */}
      {secondaryMetrics.length > 0 ? (
        secondaryMetrics.map((metric, index) => (
          <MemoizedGlassCardContainer key={metric.key || index}>
            <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} border`}>
              <h3 className="text-sm opacity-70 mb-2 text-white/70">{metric.label}</h3>
              <div className="text-2xl font-bold mb-2 text-white">
                {metric.value}{metric.unit}
              </div>
              {typeof metric.value === 'number' && metric.progress !== undefined && (
                <MemoizedGlassProgress
                  value={metric.progress}
                  max={100}
                  className="mt-2"
                  style={{ backgroundColor: theme.primary }}
                />
              )}
            </MemoizedGlassCard>
          </MemoizedGlassCardContainer>
        ))
      ) : (
        // 默认辅助指标（无数据时显示）
        [0, 1, 2].map((i) => (
          <MemoizedGlassCardContainer key={i}>
            <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} border`}>
              <h3 className="text-sm opacity-70 mb-2 text-white/70">等待数据...</h3>
              <div className="text-2xl font-bold mb-2 text-white">--</div>
            </MemoizedGlassCard>
          </MemoizedGlassCardContainer>
        ))
      )}

      {/* 图表卡片 */}
      <MemoizedGlassCardContainer layout="wide">
        <MemoizedGlassCard variant="large" className={`${theme.cardBg} ${theme.cardBorder} border`}>
          <h3 className="text-lg font-bold mb-4 text-white">{config.chartTitle}</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" />
                <YAxis stroke="rgba(255,255,255,0.5)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff'
                  }}
                />
                {config.chartSeries.map((series) => (
                  <Line
                    key={series.key}
                    type="monotone"
                    dataKey={series.key}
                    name={series.name}
                    stroke={series.color}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>

      {/* 设备状态卡片 */}
      <MemoizedGlassCardContainer>
        <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} border`}>
          <h3 className="text-sm opacity-70 mb-3 text-white/70">设备状态</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-white/80">后端连接</span>
              <MemoizedGlassBadge
                className={`text-white ${
                  connectionStatus === 'connected' ? 'bg-green-500' :
                  connectionStatus === 'connecting' ? 'bg-yellow-500' :
                  connectionStatus === 'error' ? 'bg-red-500' : 'bg-gray-500'
                }`}
              >
                {connectionStatus === 'connected' ? '已连接' :
                 connectionStatus === 'connecting' ? '连接中...' :
                 connectionStatus === 'error' ? '连接错误' : '未连接'}
              </MemoizedGlassBadge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">电池电量</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-white/20 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: '85%', backgroundColor: '#22c55e' }}
                  ></div>
                </div>
                <span className="text-white">85%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">信号质量</span>
              <MemoizedGlassBadge
                className={`text-white ${signalQuality > 70 ? 'bg-green-500' : signalQuality > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
              >
                {signalQuality > 70 ? '良好' : signalQuality > 40 ? '一般' : '较差'}
              </MemoizedGlassBadge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">模拟数据</span>
              <button
                onClick={() => setShowMockData(!showMockData)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  showMockData
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-gray-700/50 text-gray-400'
                }`}
              >
                {showMockData ? '开启' : '关闭'}
              </button>
            </div>
          </div>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>

      {/* 系统信息卡片 */}
      <MemoizedGlassCardContainer>
        <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} border`}>
          <h3 className="text-sm opacity-70 mb-3 text-white/70">系统信息</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-white/80">软件版本</span>
              <span className="text-white">v2.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">数据更新</span>
              <span className="text-white">{connectionStatus === 'connected' ? '实时' : '离线'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">当前模块</span>
              <span className="text-white">{config.title}</span>
            </div>
          </div>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>
    </div>
  );
};