import React from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { Eye, Brain, Clock, AlertTriangle, CheckCircle, XCircle, Wifi, Battery, Activity, Play, Square, Loader2 } from 'lucide-react';

interface MonitoringDashboardProps {
  data: {
    eyeStatus: 'open' | 'closing' | 'closed';
    fatigueScore: number;
    blinkRate: number;
    eyelidStatus: {
      leftEye: 'open' | 'closing' | 'closed';
      rightEye: 'open' | 'closing' | 'closed';
      blinkDuration: number;
      eyeClosureRatio: number;
    };
    sensorStatus: { connected: boolean; signalQuality: number; batteryLevel: number };
    alertLevel: 'normal' | 'warning' | 'danger';
    drivingTime: string;
    lastUpdate: string;
  };
  isMonitoring: boolean;
  wsStatus: "disconnected" | "connecting" | "connected" | "error";
  onToggleMonitoring: () => void;
}

export function MonitoringDashboard({ data, isMonitoring, wsStatus, onToggleMonitoring }: MonitoringDashboardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-green-500';
      case 'closing': return 'bg-yellow-500';
      case 'closed': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'normal': return 'text-green-600 bg-green-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      case 'danger': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
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
    <div className="relative">
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 transition-opacity duration-300`}>
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

      {/* 疲劳评分 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Brain className="h-6 w-6 text-purple-600" />
          <h3>疲劳评分</h3>
        </div>
        <div className="space-y-3">
          <div className="text-center">
            <div className="text-3xl mb-2">{data.fatigueScore}%</div>
            <Progress value={safePercent(data.fatigueScore)} className="h-3" />
          </div>
          <div className="text-center text-sm text-muted-foreground">
            {data.fatigueScore < 30 ? '状态良好' :
             data.fatigueScore < 70 ? '轻度疲劳' : '重度疲劳'}
          </div>
        </div>
      </Card>

      {/* 驾驶时间 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Clock className="h-6 w-6 text-orange-600" />
          <h3>驾驶时间</h3>
        </div>
        <div className="space-y-3">
          <div className="text-2xl">{data.drivingTime || "--"}</div>
          <div className="text-sm text-muted-foreground">
            持续驾驶时间
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

      {/* 传感器状态 */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Wifi className="h-6 w-6 text-blue-600" />
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

      {/* 警报状态 */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold">系统状态</h3>
          <div className="flex items-center gap-2">
            {wsStatus === 'connecting' && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            <Button 
              variant={isMonitoring ? "destructive" : "default"}
              size="sm"
              onClick={onToggleMonitoring}
              disabled={wsStatus === 'connecting'}
              className="flex items-center gap-2"
            >
              {isMonitoring ? <Square className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
              {isMonitoring ? "停止监控" : (wsStatus === 'connecting' ? "连接中..." : "开始监控")}
            </Button>
          </div>
        </div>
        <Alert className={getAlertColor(data.alertLevel)}>
          <div className="flex items-center gap-2">
            {getAlertIcon(data.alertLevel)}
            <AlertDescription>
              {data.alertLevel === 'normal' ? '正常监控中' :
               data.alertLevel === 'warning' ? '检测到疲劳迹象' : '疲劳驾驶警告！'}
            </AlertDescription>
          </div>
        </Alert>
        <div className="mt-4 text-sm text-muted-foreground">
          {wsStatus === 'disconnected' && !isMonitoring ? (
             <span className="text-gray-500">系统待机中，点击上方按钮开始监控</span>
          ) : wsStatus === 'connecting' ? (
             <span className="text-blue-500">正在连接服务器...</span>
          ) : wsStatus === 'error' ? (
             <span className="text-red-500">连接异常，请检查网络</span>
          ) : (
             <span>最近更新: {data.lastUpdate}</span>
          )}
        </div>
      </Card>
    </div>
    </div>
  );
}