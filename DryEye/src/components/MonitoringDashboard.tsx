import React from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Eye, Brain, Clock, AlertTriangle, CheckCircle, XCircle, Activity, AlertCircle, Info, Signal, Battery, Zap, Loader2 } from 'lucide-react';
import { EyeState, eyeStateLabels, eyeStateDescriptions, normalizeEyeState } from './ui/eye-utils';

interface MonitoringDashboardProps {
  data: {
    eyeStatus: 'open' | 'closing' | 'closed';
    eyeHealthScore: number;
    dryEyeRiskScore?: number;
    dryEyeRiskLevel?: '低风险' | '中风险' | '高风险';
    blinkRate: number;
    avgBlinkDuration?: number;
    incompleteBlinkRatio?: number;
    longBlinkRatio?: number;
    totalBlinks?: number;
    incompleteBlinks?: number;
    longBlinks?: number;
    eyelidStatus: {
      leftEye: 'open' | 'closing' | 'closed';
      rightEye: 'open' | 'closing' | 'closed';
      blinkDuration: number;
      eyeClosureRatio: number;
    };
    sensorStatus: {
      connected: boolean;
      signalQuality: number;
      batteryLevel: number;
    };
    alertLevel: 'normal' | 'warning' | 'danger';
    monitoringTime: string;
    lastUpdate: string;
    refreshInterval?: number;
    // 眼部状态检测
    eyeState?: EyeState | string;
  };
}

export function MonitoringDashboard({ data }: MonitoringDashboardProps) {
  const currentEyeState = normalizeEyeState(data.eyeState);

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'normal': return 'text-green-600 bg-green-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      case 'danger': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getEyeStatusBadge = (status: 'open' | 'closing' | 'closed') => {
    switch (status) {
      case 'open': return <Badge className="bg-green-500 text-white">睁开</Badge>;
      case 'closing': return <Badge className="bg-yellow-500 text-white">正在闭合</Badge>;
      case 'closed': return <Badge className="bg-red-500 text-white">闭合</Badge>;
      default: return <Badge variant="secondary">未知</Badge>;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-green-500';
      case 'closing': return 'bg-yellow-500';
      case 'closed': return 'bg-red-500';
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
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* 干眼风险评估 */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Brain className="h-6 w-6 text-purple-600" />
            <h3>干眼风险评估</h3>
          </div>
          <div className="space-y-3">
            <div className="text-center">
              <div className="text-3xl mb-2">{data.dryEyeRiskScore || 0}%</div>
              <Progress value={safePercent(data.dryEyeRiskScore || 0)} className="h-3" />
            </div>
            <div className="text-center">
              <Badge variant="outline" className={`text-sm py-1 px-4 font-bold border-2 ${
                data.dryEyeRiskLevel === '高风险' ? 'border-red-200 text-red-700 bg-red-50' : 
                data.dryEyeRiskLevel === '中风险' ? 'border-yellow-200 text-yellow-700 bg-yellow-50' : 
                'border-green-200 text-green-700 bg-green-50'
              }`}>
                {data.dryEyeRiskLevel || '检测中'}
              </Badge>
            </div>
          </div>
        </Card>

        {/* 眼部状态 */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Eye className="h-6 w-6 text-blue-600" />
            <h3>眼部状态</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span>当前状态</span>
              <Badge className={`${getStatusColor(data.eyeStatus)} text-white`}>
                {data.eyeStatus === 'open' ? '睁开' : 
                 data.eyeStatus === 'closing' ? '半闭' : '闭合'}
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>眨眼频率</span>
                <span>{data.blinkRate} 次/分钟</span>
              </div>
              <Progress value={safePercent((data.blinkRate / 30) * 100)} className="h-2" />
            </div>
          </div>
        </Card>

        {/* 传感器状态 */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Signal className="h-6 w-6 text-blue-600" />
            <h3>传感器状态</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span>连接状态</span>
              <Badge className={`${data.sensorStatus.connected ? 'bg-green-500' : 'bg-red-500'} text-white`}>
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

        {/* 眼睑状态 */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="h-6 w-6 text-green-600" />
            <h3>眼睑状态</h3>
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-lg mb-1">
                  <Badge className={`${getStatusColor(data.eyelidStatus.leftEye)} text-white`}>
                    {data.eyelidStatus.leftEye === 'open' ? '睁开' : 
                     data.eyelidStatus.leftEye === 'closing' ? '半闭' : '闭合'}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">左眼</div>
              </div>
              <div className="text-center">
                <div className="text-lg mb-1">
                  <Badge className={`${getStatusColor(data.eyelidStatus.rightEye)} text-white`}>
                    {data.eyelidStatus.rightEye === 'open' ? '睁开' : 
                     data.eyelidStatus.rightEye === 'closing' ? '半闭' : '闭合'}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">右眼</div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>眨眼持续时间</span>
                <span>{data.eyelidStatus.blinkDuration} ms</span>
              </div>
              <Progress value={safePercent((data.eyelidStatus.blinkDuration / 500) * 100)} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>眼睑闭合比例</span>
                <span>{data.eyelidStatus.eyeClosureRatio}%</span>
              </div>
              <Progress value={safePercent(data.eyelidStatus.eyeClosureRatio)} className="h-2" />
            </div>
          </div>
        </Card>

        {/* 眨眼分析 */}
        <Card className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="h-6 w-6 text-orange-600" />
            <h3>眨眼分析</h3>
          </div>
          <div className="space-y-3">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>平均眨眼时长</span>
                <span>{data.avgBlinkDuration || data.eyelidStatus.blinkDuration} ms</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>不完全眨眼占比</span>
                <span>{data.incompleteBlinkRatio || 0}%</span>
              </div>
              <Progress value={safePercent(data.incompleteBlinkRatio || 0)} className="h-2" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>长眨眼率</span>
                <span>{data.longBlinkRatio || 0}%</span>
              </div>
              <Progress value={safePercent(data.longBlinkRatio || 0)} className="h-2" />
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
                {data.alertLevel === 'normal' ? '正常监控中' :
                 data.alertLevel === 'warning' ? '检测到干眼迹象' : '干眼风险警告！'}
              </AlertDescription>
            </div>
          </Alert>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">监控时间</span>
              <span>{data.monitoringTime}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">最近更新</span>
              <span>{data.lastUpdate}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">采样频率</span>
              <span>{data.refreshInterval ? `${(1000 / data.refreshInterval).toFixed(1)} Hz` : '自动'}</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
