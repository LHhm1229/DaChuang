import React, { useState, useEffect, memo } from 'react';
import { GlassCard, GlassCardContainer, GlassProgress, GlassBadge } from './ui';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { bluetoothService } from '../services/bluetoothService';
import { useDataService } from '../services/dataService';

// 性能优化：使用React.memo包装玻璃态卡片组件
const MemoizedGlassCard = memo(GlassCard);
const MemoizedGlassCardContainer = memo(GlassCardContainer);
const MemoizedGlassProgress = memo(GlassProgress);
const MemoizedGlassBadge = memo(GlassBadge);

interface UnifiedBentoDashboardProps {
  module: 'dry-eye' | 'sleep' | 'fatigue';
}

// 模拟数据
const generateMockData = (module: 'dry-eye' | 'sleep' | 'fatigue', count: number = 24) => {
  const data = [];
  for (let i = 0; i < count; i++) {
    const timestamp = new Date();
    timestamp.setHours(timestamp.getHours() - (count - i));
    
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
    } else if (module === 'fatigue') {
      data.push({
        time: timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        fatigueScore: Math.random() * 40 + 30,
        blinkDuration: Math.random() * 100 + 200
      });
    }
  }
  return data;
};

// 模块配置
const moduleConfigs = {
  'dry-eye': {
    title: '干眼症监测',
    mainMetric: 'dryEyeRisk',
    mainMetricLabel: '干眼风险',
    mainMetricUnit: '%',
    secondaryMetrics: [
      { key: 'blinkRate', label: '眨眼频率', unit: '次/分钟', value: 15.5 },
      { key: 'avgBlinkDuration', label: '平均眨眼持续时间', unit: 'ms', value: 250 },
      { key: 'eyeClosureRatio', label: '眼睛闭合比例', unit: '%', value: 3.5 }
    ],
    chartData: generateMockData('dry-eye'),
    chartConfig: {
      yAxis: '数值',
      series: [
        { key: 'blinkRate', name: '眨眼频率', color: '#16C79E' },
        { key: 'dryEyeRisk', name: '干眼风险', color: '#E86830' }
      ]
    }
  },
  'sleep': {
    title: '睡眠质量检测',
    mainMetric: 'sleepScore',
    mainMetricLabel: '睡眠质量',
    mainMetricUnit: '分',
    secondaryMetrics: [
      { key: 'currentStage', label: '当前睡眠阶段', unit: '', value: '浅睡N2' },
      { key: 'remDensity', label: 'REM密度', unit: '', value: 0.2 },
      { key: 'sleepEfficiency', label: '睡眠效率', unit: '%', value: 90.0 }
    ],
    chartData: generateMockData('sleep'),
    chartConfig: {
      yAxis: '数值',
      series: [
        { key: 'sleepScore', name: '睡眠质量', color: '#4F1091' },
        { key: 'remDensity', name: 'REM密度', color: '#8A2BE2' }
      ]
    }
  },
  'fatigue': {
    title: '疲劳驾驶预警',
    mainMetric: 'fatigueScore',
    mainMetricLabel: '疲劳评分',
    mainMetricUnit: '分',
    secondaryMetrics: [
      { key: 'blinkRate', label: '眨眼频率', unit: '次/分钟', value: 12.0 },
      { key: 'avgBlinkDuration', label: '平均眨眼持续时间', unit: 'ms', value: 300 },
      { key: 'alertLevel', label: '预警等级', unit: '', value: '警告' }
    ],
    chartData: generateMockData('fatigue'),
    chartConfig: {
      yAxis: '数值',
      series: [
        { key: 'fatigueScore', name: '疲劳评分', color: '#E86830' },
        { key: 'blinkDuration', name: '眨眼持续时间', color: '#FFA500' }
      ]
    }
  }
};

export const UnifiedBentoDashboard: React.FC<UnifiedBentoDashboardProps> = ({ module }) => {
  const [chartData, setChartData] = useState(moduleConfigs[module].chartData);
  const [mainValue, setMainValue] = useState<number | string>(0);
  const [bluetoothConnected, setBluetoothConnected] = useState(false);
  const [signalQuality, setSignalQuality] = useState(85);
  const config = moduleConfigs[module];
  
  // 使用数据服务获取后端数据
  const { data: backendData } = useDataService(module);

  useEffect(() => {
    setBluetoothConnected(bluetoothService.isDeviceConnected());
    
    const handleDataReceived = (data: any) => {
      setBluetoothConnected(true);
      if (data.signalQuality !== undefined) {
        setSignalQuality(data.signalQuality);
      }
    };

    const handleError = () => {
      setBluetoothConnected(false);
    };

    bluetoothService.addListener(handleDataReceived);
    bluetoothService.addErrorListener(handleError);

    return () => {
      bluetoothService.removeListener(handleDataReceived);
      bluetoothService.removeErrorListener(handleError);
    };
  }, []);

  // 处理后端数据更新
  useEffect(() => {
    if (backendData) {
      console.log('后端数据更新:', backendData);
      
      if (module === 'dry-eye') {
        if (backendData.dryEyeRiskScore !== undefined) {
          setMainValue(Math.round(backendData.dryEyeRiskScore));
        }
        if (backendData.blinkRate !== undefined) {
          config.secondaryMetrics[0].value = backendData.blinkRate;
        }
        if (backendData.avgBlinkDuration !== undefined) {
          config.secondaryMetrics[1].value = backendData.avgBlinkDuration;
        }
        if (backendData.eyeClosureRatio !== undefined) {
          config.secondaryMetrics[2].value = backendData.eyeClosureRatio;
        }
      } else if (module === 'sleep') {
        if (backendData.qualityScore !== undefined) {
          setMainValue(Math.round(backendData.qualityScore));
        }
        if (backendData.currentStageName !== undefined) {
          config.secondaryMetrics[0].value = backendData.currentStageName;
        }
        if (backendData.remDensity !== undefined) {
          config.secondaryMetrics[1].value = backendData.remDensity;
        }
        if (backendData.sleepEfficiency !== undefined) {
          config.secondaryMetrics[2].value = backendData.sleepEfficiency;
        }
      } else if (module === 'fatigue') {
        if (backendData.fatigueScore !== undefined) {
          setMainValue(Math.round(backendData.fatigueScore));
        }
        if (backendData.blinkRate !== undefined) {
          config.secondaryMetrics[0].value = backendData.blinkRate;
        }
        if (backendData.avgBlinkDuration !== undefined) {
          config.secondaryMetrics[1].value = backendData.avgBlinkDuration;
        }
        if (backendData.alertLevel !== undefined) {
          config.secondaryMetrics[2].value = backendData.alertLevel;
        }
      }
    }
  }, [backendData, module]);

  useEffect(() => {
    const interval = setInterval(() => {
      setChartData(generateMockData(module));
      
      // 如果没有后端数据，使用模拟数据更新主值
      if (!backendData) {
        if (module === 'dry-eye') {
          setMainValue(Math.round(Math.random() * 50 + 20));
        } else if (module === 'sleep') {
          setMainValue(Math.round(Math.random() * 30 + 70));
        } else if (module === 'fatigue') {
          setMainValue(Math.round(Math.random() * 40 + 30));
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [module, backendData]);

  const getThemeColors = () => {
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

  const theme = getThemeColors();

  const getMainValueColor = (value: number | string): string => {
    if (typeof value === 'string') return `text-${module === 'dry-eye' ? 'emerald' : module === 'sleep' ? 'purple' : 'orange'}-400`;
    
    if (module === 'dry-eye') {
      if (value < 30) return 'text-emerald-400';
      if (value < 60) return 'text-yellow-400';
      return 'text-red-400';
    } else if (module === 'sleep') {
      if (value > 80) return 'text-emerald-400';
      if (value > 60) return 'text-yellow-400';
      return 'text-red-400';
    } else if (module === 'fatigue') {
      if (value < 40) return 'text-emerald-400';
      if (value < 70) return 'text-yellow-400';
      return 'text-red-400';
    }
    return 'text-white';
  };

  return (
    <div className={`bento-grid min-h-screen bg-gradient-to-br ${theme.bgGradient} p-4 md:p-8`}>
      {/* 主指标卡片 */}
      <MemoizedGlassCardContainer layout="large">
        <MemoizedGlassCard variant="large" className={`${theme.cardBg} ${theme.cardBorder} border flex flex-col justify-center items-center`}>
          <h2 className="text-2xl font-bold mb-4 text-white">{config.mainMetricLabel}</h2>
          <div className={`text-6xl font-bold mb-4 ${getMainValueColor(mainValue)}`}>
            {mainValue}{config.mainMetricUnit}
          </div>
          <MemoizedGlassBadge className={`text-lg px-6 py-2 text-white bg-[${theme.badgeColor}]`}>
            {module === 'dry-eye' ? '实时监测中' : 
             module === 'sleep' ? '睡眠分析中' : '驾驶监测中'}
          </MemoizedGlassBadge>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>

      {/* 辅助指标卡片 */}
      {config.secondaryMetrics.map((metric) => (
        <MemoizedGlassCardContainer key={metric.key}>
          <MemoizedGlassCard className={`${theme.cardBg} ${theme.cardBorder} border`}>
            <h3 className="text-sm opacity-70 mb-2 text-white/70">{metric.label}</h3>
            <div className="text-2xl font-bold mb-2 text-white">
              {metric.value}{metric.unit}
            </div>
            {typeof metric.value === 'number' && (
              <MemoizedGlassProgress
                value={metric.value as number}
                max={module === 'dry-eye' ? 100 : module === 'sleep' ? 100 : 100}
                className={`mt-2`}
                style={{ backgroundColor: theme.primary }}
              />
            )}
          </MemoizedGlassCard>
        </MemoizedGlassCardContainer>
      ))}

      {/* 图表卡片 */}
      <MemoizedGlassCardContainer layout="wide">
        <MemoizedGlassCard variant="large" className={`${theme.cardBg} ${theme.cardBorder} border`}>
          <h3 className="text-lg font-bold mb-4 text-white">{module === 'dry-eye' ? '眨眼频率与干眼风险趋势' : 
             module === 'sleep' ? '睡眠质量与REM密度趋势' : '疲劳评分与眨眼持续时间趋势'}</h3>
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
                {config.chartConfig.series.map((series) => (
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
              <span className="text-white/80">蓝牙连接</span>
              <MemoizedGlassBadge 
                className={`text-white ${bluetoothConnected ? 'bg-green-500' : 'bg-gray-500'}`}
              >
                {bluetoothConnected ? '已连接' : '未连接'}
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
              <span className="text-white">v1.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">数据更新</span>
              <span className="text-white">实时</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/80">监测时长</span>
              <span className="text-white">01:23:45</span>
            </div>
          </div>
        </MemoizedGlassCard>
      </MemoizedGlassCardContainer>
    </div>
  );
};
