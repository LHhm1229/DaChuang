import React from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Eye, Brain, Clock, AlertTriangle, CheckCircle, XCircle, Wifi, Battery, Activity, Zap } from 'lucide-react';
import { SleepData } from '../services/dataService';

interface MonitoringDashboardProps {
  data: SleepData;
}

const sleepStageLabels: Record<'awake' | 'light' | 'deep' | 'rem', string> = {
  awake: '清醒',
  light: '浅睡',
  deep: '深睡',
  rem: '快速眼动',
};

const sleepStageDescriptions: Record<'awake' | 'light' | 'deep' | 'rem', string> = {
  awake: '当前处于清醒状态',
  light: '当前处于浅层睡眠阶段',
  deep: '当前处于深度睡眠阶段',
  rem: '当前处于快速眼动睡眠阶段',
};

const eyeStateLabels: Record<'睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼' | '快速眼动', string> = {
  '睁眼': '睁眼',
  '闭眼': '闭眼',
  '频繁眨眼': '频繁眨眼',
  '慢速眨眼': '慢速眨眼',
  '正常眨眼': '正常眨眼',
  '快速眼动': '快速眼动',
};

const eyeStateDescriptions: Record<'睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼' | '快速眼动', string> = {
  '睁眼': '双眼睁开',
  '闭眼': '双眼闭合',
  '频繁眨眼': '眨眼频繁，可能在清醒状态',
  '慢速眨眼': '眨眼缓慢，可能进入睡眠',
  '正常眨眼': '眨眼频率正常',
  '快速眼动': 'REM睡眠阶段，眼球快速运动',
};

export function MonitoringDashboard({ data }: MonitoringDashboardProps) {
  if (!data || !data.sensorStatus) {
    return (
      <div className="flex items-center justify-center h-64 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
        <div className="text-center">
          <Activity className="h-8 w-8 text-slate-400 mx-auto mb-2 animate-pulse" />
          <p className="text-slate-500">正在等待数据接入...</p>
        </div>
      </div>
    );
  }

  const normalizeSleepStage = (
    stage: MonitoringDashboardProps['data']['sleepStage'] | string | undefined,
  ): 'awake' | 'light' | 'deep' | 'rem' => {
    if (typeof stage !== 'string') return 'awake';
    const s = stage.trim().toLowerCase();
    if (s === 'awake' || s === 'light' || s === 'deep' || s === 'rem') return s as 'awake' | 'light' | 'deep' | 'rem';
    
    // 中文映射
    if (s.includes('清醒')) return 'awake';
    if (s.includes('浅')) return 'light';
    if (s.includes('深')) return 'deep';
    if (s.includes('动')) return 'rem';
    
    // 默认回退
    return 'awake';
  };

  const normalizeEyeState = (
    state: MonitoringDashboardProps['data']['eyeState'] | string | undefined,
  ): '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼' | '快速眼动' => {
    if (typeof state !== 'string') return '正常眨眼';
    const s = state.trim();
    if (!s) return '正常眨眼';

    if (s === '睁眼' || s === '闭眼' || s === '频繁眨眼' || s === '慢速眨眼' || s === '正常眨眼' || s === '快速眼动') return s;

    const normalized = s.toLowerCase().replace(/\s+/g, '_');
    if (normalized === 'open' || normalized === 'opened' || normalized === 'eye_open') return '睁眼';
    if (normalized === 'close' || normalized === 'closed' || normalized === 'eye_close' || normalized === 'eye_closed') return '闭眼';
    if (
      normalized === 'fast_blink' ||
      normalized === 'frequent_blink' ||
      normalized === 'blink_fast' ||
      normalized === 'rapid_blink' ||
      normalized === 'closing'
    ) return '频繁眨眼';
    if (
      normalized === 'slow_blink' ||
      normalized === 'blink_slow' ||
      normalized === 'slowblink'
    ) return '慢速眨眼';
    if (
      normalized === 'normal' ||
      normalized === 'normal_blink' ||
      normalized === 'blink_normal'
    ) return '正常眨眼';
    if (
      normalized === 'rem' ||
      normalized === 'rapid_eye_movement' ||
      normalized === 'fast_eye_movement'
    ) return '快速眼动';

    return '正常眨眼';
  };

  const currentSleepStage = normalizeSleepStage(data.sleepStage);
  const currentEyeState = normalizeEyeState(data.eyeState);
  
  // 确保显示名称不为空，优先使用算法输出的阶段名称
  const displayStageName = (data.currentStageName && data.currentStageName.trim() !== '') 
    ? data.currentStageName 
    : (sleepStageLabels[currentSleepStage] || '清醒');

  // 获取描述文本
  const displayDescription = data.currentStageName 
    ? `当前检测为: ${data.currentStageName}` 
    : (sleepStageDescriptions[currentSleepStage] || '正在分析睡眠状态...');

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'normal': return 'text-green-600 bg-green-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      case 'danger': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'deep': return 'bg-blue-700';
      case 'rem': return 'bg-purple-600';
      case 'light': return 'bg-blue-400';
      case 'awake': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getEyeStateColor = (state: string) => {
    switch (state) {
      case '睁眼': return 'bg-green-500';
      case '闭眼': return 'bg-red-500';
      case '频繁眨眼': return 'bg-yellow-500';
      case '慢速眨眼': return 'bg-yellow-500';
      case '正常眨眼': return 'bg-green-500';
      case '快速眼动': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'normal': return <CheckCircle className="h-4 w-4" />;
      case 'warning': return <AlertTriangle className="h-4 w-4" />;
      case 'danger': return <XCircle className="h-4 w-4" />;
      default: return <AlertTriangle className="h-4 w-4" />;
    }
  };

  // 安全的百分比计算
  const safePercent = (val: number) => Math.min(100, Math.max(0, val || 0));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* 当前睡眠阶段 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Brain className="h-6 w-6 text-purple-600" />
          <h3>当前睡眠阶段</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span>当前状态</span>
            <Badge className={`${getStageColor(currentSleepStage)} text-white`}>
              {displayStageName}
            </Badge>
          </div>
          <div className="text-sm text-muted-foreground">
            {displayDescription}
          </div>
        </div>
      </Card>

      {/* 睡眠质量评分 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="h-6 w-6 text-green-600" />
          <h3>睡眠质量评分</h3>
        </div>
        <div className="space-y-3">
          <div className="text-center">
            <div className="text-3xl mb-2">{data.sleepScore}%</div>
            <Progress value={safePercent(data.sleepScore)} className="h-3" />
          </div>
          <div className="text-center text-sm text-muted-foreground">
            {data.sleepScore >= 80 ? '睡眠状态优秀' :
             data.sleepScore >= 60 ? '睡眠状态良好' : '睡眠质量欠佳'}
          </div>
        </div>
      </Card>

      {/* 睡眠效率 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="h-6 w-6 text-blue-600" />
          <h3>睡眠效率 (SE)</h3>
        </div>
        <div className="space-y-3">
          <div className="text-2xl">{data.sleepEfficiency ?? '0'}%</div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>睡眠效率</span>
              <span>{data.tstMinutes ?? 0} / {data.totalMinutes ?? 0} min</span>
            </div>
            <Progress value={safePercent(data.sleepEfficiency ?? 0)} className="h-2" />
          </div>
        </div>
      </Card>

      {/* 睡眠稳定性 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="h-6 w-6 text-orange-600" />
          <h3>睡眠稳定性</h3>
        </div>
        <div className="space-y-3">
          <div className="text-2xl">{data.sleepStability ?? data.eyelidStatus.eyeClosureRatio}%</div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>稳定性指数</span>
              <span>{data.sleepStability ?? data.eyelidStatus.eyeClosureRatio}%</span>
            </div>
            <Progress value={safePercent(data.sleepStability ?? data.eyelidStatus.eyeClosureRatio)} className="h-2" />
          </div>
        </div>
      </Card>

      {/* 体动频率 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="h-6 w-6 text-red-600" />
          <h3>体动频率</h3>
        </div>
        <div className="space-y-3">
          <div className="text-2xl">{data.movementIndex ?? data.movementRate}</div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>当前体动指数</span>
              <span>{data.movementIndex ?? data.movementRate} 次/min</span>
            </div>
            <Progress value={safePercent(((data.movementIndex ?? data.movementRate) / 40) * 100)} className="h-2" />
          </div>
        </div>
      </Card>

      {/* 累计监测时长 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Clock className="h-6 w-6 text-blue-600" />
          <h3>累计监测时长</h3>
        </div>
        <div className="space-y-3">
          <div className="text-2xl">{data.monitoringDuration}</div>
          <div className="text-sm text-muted-foreground">
            自启动以来已监测时间
          </div>
        </div>
      </Card>

      {/* 眼动特征监测 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Eye className="h-6 w-6 text-cyan-600" />
          <h3>眼动特征监测</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span>当前眼部状态</span>
            <Badge className={`${getEyeStateColor(currentEyeState)} text-white`}>
              {eyeStateLabels[currentEyeState]}
            </Badge>
          </div>
          <div className="text-sm text-muted-foreground">
            {eyeStateDescriptions[currentEyeState]}
          </div>
        </div>
      </Card>

      {/* 传感器状态 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Wifi className="h-6 w-6 text-emerald-600" />
          <h3>传感器状态</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span>连接状态</span>
            <Badge className={`${data.sensorStatus.connected ? 'bg-emerald-500' : 'bg-red-500'} text-white`}>
              {data.sensorStatus.connected ? '已连接' : '断开'}
            </Badge>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>信号质量</span>
              <span>{data.sensorStatus.signalQuality}%</span>
            </div>
            <Progress value={safePercent(data.sensorStatus.signalQuality)} className="h-2" />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Battery className="h-4 w-4" />
              <span>电池电量</span>
            </div>
            <span>{data.sensorStatus.batteryLevel}%</span>
          </div>
        </div>
      </Card>

      {/* 系统状态 */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold">系统状态</h3>
        </div>
        <Alert className={getAlertColor(data.alertLevel)}>
          <div className="flex items-center gap-2">
            {getAlertIcon(data.alertLevel)}
            <AlertDescription>
              {data.alertLevel === 'normal' ? '当前睡眠状态平稳' :
               data.alertLevel === 'warning' ? '监测到异常体动或苏醒' : '睡眠质量显著下降警告！'}
            </AlertDescription>
          </div>
        </Alert>
        <div className="mt-4 text-sm text-muted-foreground">
          <span>最近更新: {data.lastUpdate}</span>
        </div>
      </Card>
    </div>
  );
}