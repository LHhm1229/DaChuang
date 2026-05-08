/**
 * UnifiedBentoDashboard.tsx - 统一Bento风格仪表盘
 * 数据与UI完全解耦 - 接收外部传入的实时数据
 * 布局已根据理想图进行重构
 */

import React, { useState, useEffect, memo } from 'react';
import { GlassCard, GlassProgress, GlassBadge } from './ui';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { UnifiedMetricData, SecondaryMetric, ChartDataPoint } from '../services/dataMapper';
import { Smartphone, Activity, Wind, Droplets, Thermometer, Zap } from 'lucide-react';

// 性能优化：使用React.memo包装玻璃态卡片组件
const MemoizedGlassCard = memo(GlassCard);

interface UnifiedBentoDashboardProps {
  module: 'dry-eye' | 'sleep' | 'fatigue';
  data: UnifiedMetricData | null;  // 接收外部传入的实时数据
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
}

// 模块配置
const moduleConfigs = {
  'dry-eye': {
    title: '干眼症监测',
    mainMetricLabel: '干眼风险评分',
    mainMetricUnit: '分',
    chartTitle: '眨眼频率与干眼风险趋势',
    chartSeries: [
      { key: 'blinkRate', name: '眨眼频率', color: '#10b981' },
      { key: 'dryEyeRisk', name: '干眼风险', color: '#f59e0b' }
    ],
    device: '智能监测眼镜',
    envIcons: [Thermometer, Droplets, Wind]
  },
  'sleep': {
    title: '睡眠质量检测',
    mainMetricLabel: '昨晚睡眠评分',
    mainMetricUnit: '分',
    chartTitle: '睡眠质量与 REM 密度趋势',
    chartSeries: [
      { key: 'sleepScore', name: '睡眠质量', color: '#a855f7' },
      { key: 'remDensity', name: 'REM 密度', color: '#ec4899' }
    ],
    device: '智能睡眠枕',
    envIcons: [Thermometer, Droplets, Wind]
  },
  'fatigue': {
    title: '疲劳驾驶预警',
    mainMetricLabel: '当前疲劳评分',
    mainMetricUnit: '分',
    chartTitle: '疲劳评分与眨眼持续时间趋势',
    chartSeries: [
      { key: 'fatigueScore', name: '疲劳评分', color: '#f97316' },
      { key: 'blinkDuration', name: '眨眼时长', color: '#eab308' }
    ],
    device: '驾驶监测终端',
    envIcons: [Thermometer, Activity, Zap]
  }
};

// 获取主题颜色配置
const getThemeColors = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
  if (module === 'dry-eye') {
    return {
      primary: '#10b981',
      accent: 'text-emerald-300',
      cardBg: 'bg-[#2a4d45]/80', // 提升亮度
      cardBorder: 'border-emerald-400/30',
      bgGradient: 'bg-[#122b25]', // 提升背景亮度
      selection: 'selection:bg-emerald-500/30'
    };
  } else if (module === 'sleep') {
    return {
      primary: '#a855f7',
      accent: 'text-purple-300',
      cardBg: 'bg-[#3d2b6b]/80', // 显眼的紫色模块
      cardBorder: 'border-purple-400/30',
      bgGradient: 'bg-[#1a1135]', // 显眼的深紫背景
      selection: 'selection:bg-purple-500/30'
    };
  } else {
    return {
      primary: '#f97316',
      accent: 'text-orange-300',
      cardBg: 'bg-[#5e3a29]/80', // 提升亮度
      cardBorder: 'border-orange-400/30',
      bgGradient: 'bg-[#2b1810]', // 提升背景亮度
      selection: 'selection:bg-orange-500/30'
    };
  }
};

// 3/4圆仪表盘组件
const SemiCircularGauge = ({ value, module }: { value: number, module: 'dry-eye' | 'sleep' | 'fatigue' }) => {
  const radius = 80;
  const strokeWidth = 14;
  const normalizedValue = Math.min(100, Math.max(0, value));
  const fullCircumference = 2 * Math.PI * radius;
  const circumference = fullCircumference * 0.75;
  const strokeDashoffset = circumference - (normalizedValue / 100) * circumference;

  const getDynamicColor = () => {
    if (module === 'dry-eye') {
      if (value < 30) return '#10b981';
      if (value < 60) return '#f59e0b';
      return '#ef4444';
    } else if (module === 'sleep') {
      if (value >= 80) return '#a855f7';
      if (value >= 60) return '#f59e0b';
      return '#ef4444';
    } else {
      if (value < 40) return '#10b981';
      if (value < 70) return '#f97316';
      return '#ef4444';
    }
  };

  const activeColor = getDynamicColor();

  return (
    <div className="relative flex flex-col items-center justify-center py-4">
      <svg width="220" height="180" viewBox="0 0 200 200" style={{ transform: 'rotate(135deg)', transformOrigin: 'center' }}>
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference} ${fullCircumference}`}
          strokeLinecap="round"
        />
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={activeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference} ${fullCircumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
          style={{ filter: `drop-shadow(0 0 12px ${activeColor}44)` }}
        />
      </svg>
      <div className="absolute top-[48%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
        <div className="flex items-baseline justify-center">
          <span className="text-6xl font-bold text-white tracking-tighter">{Math.round(value)}</span>
          <span className="text-2xl text-white/70 ml-1">分</span>
        </div>
        <p className="text-sm font-medium mt-1" style={{ color: activeColor }}>
          {module === 'dry-eye' ? (
            value >= 60 ? '高风险 (High Risk)' : value >= 30 ? '中风险 (Medium Risk)' : '健康 (Healthy)'
          ) : module === 'sleep' ? (
            value >= 80 ? '优 (Excellent)' : value >= 60 ? '良 (Good)' : '差 (Poor)'
          ) : (
            value >= 70 ? '极度疲劳 (Severe)' : value >= 40 ? '轻度疲劳 (Mild)' : '清醒 (Awake)'
          )}
        </p>
      </div>
    </div>
  );
};

// 心率波形模拟组件
const HeartRateWave = ({ color }: { color: string }) => {
  return (
    <div className="w-full h-16 opacity-40 overflow-hidden">
      <svg viewBox="0 0 200 60" className="w-full h-full">
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="2"
          points="0,30 20,30 25,10 35,50 40,30 60,30 65,10 75,50 80,30 100,30 105,5 115,55 120,30 140,30 145,10 155,50 160,30 180,30 185,10 195,50 200,30"
          className="heart-rate-anim"
        />
      </svg>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes heartRate {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .heart-rate-anim {
          animation: heartRate 4s linear infinite;
        }
      `}} />
    </div>
  );
};

export const UnifiedBentoDashboard: React.FC<UnifiedBentoDashboardProps> = ({
  module,
  data,
  connectionStatus
}) => {
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [mainValue, setMainValue] = useState<number>(0);
  const [secondaryMetrics, setSecondaryMetrics] = useState<SecondaryMetric[]>([]);

  const config = moduleConfigs[module];
  const theme = getThemeColors(module);

  // 初始化图表模拟数据
  useEffect(() => {
    const initialData: ChartDataPoint[] = [];
    const now = new Date();
    for (let i = 20; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60000);
      initialData.push({
        time: time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        sleepScore: 75 + Math.random() * 15,
        remDensity: 0.15 + Math.random() * 0.2,
        fatigueScore: 45 + Math.random() * 25,
        blinkDuration: 180 + Math.random() * 80,
        blinkRate: 12 + Math.random() * 12,
        dryEyeRisk: 25 + Math.random() * 25,
      });
    }
    setChartData(initialData);
  }, []);

  // 处理实时数据更新
  useEffect(() => {
    if (data) {
      setMainValue(data.mainValue as number);
      setSecondaryMetrics(data.secondaryMetrics);

      setChartData(prev => {
        const newPoint: ChartDataPoint = {
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          sleepScore: module === 'sleep' ? data.mainValue as number : (prev[prev.length-1]?.sleepScore as number || 75),
          remDensity: module === 'sleep' ? parseFloat(data.secondaryMetrics[1]?.value as string) || 0 : (prev[prev.length-1]?.remDensity as number || 0.15),
          fatigueScore: module === 'fatigue' ? data.mainValue as number : (prev[prev.length-1]?.fatigueScore as number || 45),
          blinkDuration: module === 'fatigue' ? data.secondaryMetrics[1]?.value as number : (prev[prev.length-1]?.blinkDuration as number || 180),
          blinkRate: module === 'dry-eye' ? data.secondaryMetrics[0]?.value as number : (prev[prev.length-1]?.blinkRate as number || 12),
          dryEyeRisk: module === 'dry-eye' ? data.mainValue as number : (prev[prev.length-1]?.dryEyeRisk as number || 25),
        };
        return [...prev.slice(1), newPoint];
      });
    }
  }, [data, module]);

  const isConnected = connectionStatus === 'connected';

  return (
    <div className={`min-h-screen ${theme.bgGradient} text-white p-4 md:p-8 font-sans ${theme.selection}`}>
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* 1. 主评分区域 (3/4 width) */}
        <MemoizedGlassCard className={`md:col-span-3 md:row-span-2 ${theme.cardBg} ${theme.cardBorder} flex flex-col items-center justify-center p-10 relative overflow-hidden group`}>
          <div className="absolute top-6 left-8 text-white/30 text-xs font-bold uppercase tracking-[0.2em]">{config.mainMetricLabel}</div>
          <SemiCircularGauge value={mainValue} module={module} />
          <div className="mt-2 flex items-center gap-3 bg-white/5 px-6 py-2 rounded-full border border-white/5 backdrop-blur-md">
            <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' : 'bg-white/20'}`} />
            <span className="text-sm font-medium text-white/60">{isConnected ? '实时监测中' : '等待设备连接...'}</span>
          </div>
        </MemoizedGlassCard>

        {/* 2. 设备状态区域 (1/4 width) */}
        <MemoizedGlassCard className={`md:col-span-1 md:row-span-2 ${theme.cardBg} ${theme.cardBorder} p-8 flex flex-col justify-between group`}>
          <div className="space-y-8">
            <h3 className="text-sm font-bold text-white/30 uppercase tracking-[0.2em]">Device & Heart Rate</h3>
            <div className="flex items-start gap-4">
              <div className="p-4 bg-white/5 rounded-2xl border border-white/5 group-hover:border-white/10 transition-colors">
                <Smartphone size={24} className={theme.accent} />
              </div>
              <div>
                <p className="text-xs text-white/30 mb-1">Device</p>
                <p className="text-lg font-bold text-white/90">{config.device}</p>
                <p className={`text-xs mt-1 font-medium ${isConnected ? 'text-green-400' : 'text-white/20'}`}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>
          </div>
          <div className="space-y-6">
            <div className="flex items-center justify-between text-xs font-bold tracking-wider">
              <span className="text-white/30 uppercase">Signal Quality</span>
              <span className={theme.accent}>{isConnected ? '98%' : '--'}</span>
            </div>
            <HeartRateWave color={theme.primary} />
          </div>
        </MemoizedGlassCard>

        {/* 3-5. 次要指标卡片 */}
        {[0, 1, 2].map((idx) => {
          const metric = secondaryMetrics[idx];
          const Icon = config.envIcons[idx] || Activity;
          return (
            <MemoizedGlassCard key={idx} className={`${theme.cardBg} ${theme.cardBorder} p-6 flex flex-col justify-between group hover:translate-y-[-2px] transition-transform`}>
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                  <Icon size={20} className={theme.accent} />
                </div>
                <span className="text-xs font-bold text-white/40 uppercase tracking-wider">{metric?.label || '等待数据'}</span>
              </div>
              <div className="mt-6 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white/90 tracking-tight">{metric?.value || '--'}</span>
                <span className="text-xs font-medium text-white/30 uppercase">{metric?.unit}</span>
              </div>
              {metric?.progress !== undefined && (
                <div className="mt-4 w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-1000" 
                    style={{ width: `${metric.progress}%`, backgroundColor: theme.primary }}
                  />
                </div>
              )}
            </MemoizedGlassCard>
          );
        })}

        {/* 6. 环境指数卡片 */}
        <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} p-6 flex flex-col justify-between group hover:translate-y-[-2px] transition-transform`}>
          <h4 className="text-xs font-bold text-white/30 uppercase tracking-[0.2em] mb-4">Environment</h4>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs text-white/40 font-medium">Temperature</span>
              <span className="text-xs font-bold text-emerald-400">23°C (Comfort)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-white/40 font-medium">Humidity</span>
              <span className="text-xs font-bold text-blue-400">55% (Ideal)</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-white/40 font-medium">Noise Level</span>
              <span className="text-xs font-bold text-yellow-400">35dB (Quiet)</span>
            </div>
          </div>
        </MemoizedGlassCard>

        {/* 7. 趋势分析图表 */}
        <MemoizedGlassCard className={`md:col-span-4 ${theme.cardBg} ${theme.cardBorder} p-8 h-[420px] group`}>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-10">
            <div>
              <h3 className="text-xl font-bold text-white/90 tracking-tight mb-1">{config.chartTitle}</h3>
              <p className="text-xs text-white/30 font-medium">基于实时生理信号的连续趋势分析</p>
            </div>
            <div className="flex gap-6 bg-white/5 px-5 py-2.5 rounded-xl border border-white/5">
              {config.chartSeries.map(series => (
                <div key={series.key} className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: series.color }} />
                  <span className="text-xs font-bold text-white/50 uppercase tracking-wider">{series.name}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="w-full h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  {config.chartSeries.map(series => (
                    <linearGradient key={`grad-${series.key}`} id={`grad-${series.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={series.color} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={series.color} stopOpacity={0}/>
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="rgba(255,255,255,0.15)" 
                  fontSize={10} 
                  fontWeight="bold"
                  tickLine={false} 
                  axisLine={false} 
                  tick={{ dy: 10 }}
                />
                <YAxis 
                  stroke="rgba(255,255,255,0.15)" 
                  fontSize={10} 
                  fontWeight="bold"
                  tickLine={false} 
                  axisLine={false} 
                  domain={['auto', 'auto']}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(15, 7, 25, 0.95)', 
                    border: '1px solid rgba(255,255,255,0.1)', 
                    borderRadius: '16px',
                    boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)',
                    backdropFilter: 'blur(20px)'
                  }}
                  itemStyle={{ fontSize: '11px', fontWeight: 'bold', padding: '2px 0' }}
                  labelStyle={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', marginBottom: '8px', fontWeight: 'bold', textTransform: 'uppercase' }}
                />
                {config.chartSeries.map(series => (
                  <Area 
                    key={series.key}
                    type="monotone" 
                    dataKey={series.key} 
                    stroke={series.color} 
                    fillOpacity={1} 
                    fill={`url(#grad-${series.key})`}
                    strokeWidth={3}
                    animationDuration={1500}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </MemoizedGlassCard>

      </div>
    </div>
  );
};
