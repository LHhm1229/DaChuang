import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Slider } from './ui/slider';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { Play, Square, Settings, Wifi, Volume2, Save, Zap } from 'lucide-react';
import { dataService } from '../services/dataService';
import { bluetoothService } from '../services/bluetoothService';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface ControlPanelProps {
  isMonitoring: boolean;
  onToggleMonitoring: () => void;
  refreshInterval: number;
  onRefreshIntervalChange: (value: number) => void;
}

export function ControlPanel({ 
  isMonitoring, 
  onToggleMonitoring,
  refreshInterval,
  onRefreshIntervalChange
}: ControlPanelProps) {
  // 从本地存储加载设置，如果没有则使用默认值
  const [sensitivity, setSensitivity] = useState(() => {
    const saved = localStorage.getItem('dry-eye-monitor-sensitivity');
    return saved ? [parseInt(saved)] : [75];
  });
  
  const [audioAlerts, setAudioAlerts] = useState(() => {
    const saved = localStorage.getItem('dry-eye-monitor-audio-alerts');
    return saved ? JSON.parse(saved) : true;
  });
  
  const [autoSave, setAutoSave] = useState(() => {
    const saved = localStorage.getItem('dry-eye-monitor-auto-save');
    return saved ? JSON.parse(saved) : true;
  });
  
  const [sensorConnected, setSensorConnected] = useState(true);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibrationResult, setCalibrationResult] = useState<'success' | 'error' | null>(null);
  const [calibrationMessage, setCalibrationMessage] = useState<string>('');

  // 传感器配置对话框状态
  const [configOpen, setConfigOpen] = useState(false);
  const [configSampleRate, setConfigSampleRate] = useState(() => {
    const saved = localStorage.getItem('dry-eye-monitor-config-sampleRate');
    return saved ? parseInt(saved) : 50;
  });
  const [configThreshold, setConfigThreshold] = useState(() => {
    const saved = localStorage.getItem('dry-eye-monitor-config-threshold');
    return saved ? parseInt(saved) : 70;
  });
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  // 保存设置到本地存储并应用到数据服务
  useEffect(() => {
    localStorage.setItem('dry-eye-monitor-sensitivity', sensitivity[0].toString());
    dataService.setSensitivity(sensitivity[0]); // 应用到数据服务
  }, [sensitivity]);

  // 处理传感器校准
  const handleCalibration = async () => {
    if (isCalibrating) return; // 如果正在校准，不允许重复点击
    
    // 清除之前的校准结果
    setCalibrationResult(null);
    setCalibrationMessage('');
    
    setIsCalibrating(true);
    
    try {
      // 检查蓝牙连接状态
      if (!bluetoothService.isDeviceConnected()) {
        throw new Error('蓝牙设备未连接，无法进行校准');
      }

      // 发送校准命令到设备
      const commandSent = await bluetoothService.sendCalibrationCommand();
      if (!commandSent) {
        throw new Error('发送校准命令失败');
      }

      // 等待校准完成（最多等待10秒）
      let calibrationComplete = false;
      const maxWaitTime = 10000; // 10秒
      const checkInterval = 500; // 每500ms检查一次
      const startTime = Date.now();

      while (!calibrationComplete && (Date.now() - startTime) < maxWaitTime) {
        await new Promise(resolve => setTimeout(resolve, checkInterval));
        calibrationComplete = await bluetoothService.checkCalibrationStatus();
      }

      if (calibrationComplete) {
        console.log('传感器校准完成');
        setCalibrationResult('success');
        setCalibrationMessage('传感器校准成功完成！');
        
        // 5秒后自动清除成功消息
        setTimeout(() => {
          setCalibrationResult(null);
          setCalibrationMessage('');
        }, 5000);
      } else {
        throw new Error('校准超时，请检查设备状态');
      }
      
    } catch (error) {
      console.error('校准失败:', error);
      setCalibrationResult('error');
      setCalibrationMessage(error instanceof Error ? error.message : '校准失败，请重试');
      
      // 8秒后自动清除错误消息
      setTimeout(() => {
        setCalibrationResult(null);
        setCalibrationMessage('');
      }, 8000);
    } finally {
      setIsCalibrating(false);
    }
  };

  useEffect(() => {
    localStorage.setItem('dry-eye-monitor-audio-alerts', JSON.stringify(audioAlerts));
  }, [audioAlerts]);

  useEffect(() => {
    localStorage.setItem('dry-eye-monitor-auto-save', JSON.stringify(autoSave));
  }, [autoSave]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 监控控制 */}
      <Card className="p-6 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-6">
          <Play className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-lg">监控控制</h3>
        </div>
        <div className="space-y-6 flex-grow">
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div>
              <div className="text-sm font-medium mb-1 text-muted-foreground uppercase tracking-wider">当前状态</div>
              <Badge variant={isMonitoring ? "default" : "secondary"} className="px-3 py-1">
                {isMonitoring ? '正在监控中' : '监控已停止'}
              </Badge>
            </div>
            <Button
              onClick={onToggleMonitoring}
              variant={isMonitoring ? "destructive" : "default"}
              size="lg"
              className="flex items-center gap-2 shadow-md transition-all hover:scale-105"
            >
              {isMonitoring ? (
                <>
                  <Square className="h-4 w-4 fill-current" />
                  停止监控
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  开始监控
                </>
              )}
            </Button>
          </div>
          
          <div className="flex items-center justify-between px-4 py-2">
            <div className="flex items-center gap-2 font-medium">
              <Wifi className={`h-4 w-4 ${sensorConnected ? 'text-green-500' : 'text-red-500'}`} />
              <span>传感器连接</span>
            </div>
            <Badge variant={sensorConnected ? "outline" : "destructive"} className={sensorConnected ? "border-green-200 text-green-700 bg-green-50" : ""}>
              {sensorConnected ? '已建立连接' : '连接已断开'}
            </Badge>
          </div>
          
          <Button
            variant="outline"
            onClick={handleCalibration}
            disabled={!sensorConnected || isMonitoring || isCalibrating}
            className="w-full flex items-center gap-2 h-12 text-base font-medium transition-all hover:bg-muted"
          >
            <Zap className={`h-4 w-4 ${isCalibrating ? 'animate-pulse text-yellow-500' : ''}`} />
            {isCalibrating ? '正在校准传感器...' : '开始传感器校准'}
          </Button>

          {/* 校准结果显示 */}
          {calibrationResult && (
            <Alert className={`${calibrationResult === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'} animate-in fade-in slide-in-from-top-2`}>
              {calibrationResult === 'success' ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-600" />
              )}
              <AlertDescription className={`${calibrationResult === 'success' ? 'text-green-800' : 'text-red-800'} font-medium`}>
                {calibrationMessage}
              </AlertDescription>
            </Alert>
          )}
        </div>
      </Card>

      {/* 系统设置 */}
      <Card className="p-6 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="h-5 w-5 text-purple-600" />
          <h3 className="font-semibold text-lg">系统参数设置</h3>
        </div>
        <div className="space-y-8 flex-grow">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">检测灵敏度</label>
              <Badge variant="outline" className="text-purple-600 border-purple-200 bg-purple-50">{sensitivity[0]}%</Badge>
            </div>
            <Slider
              value={sensitivity}
              onValueChange={setSensitivity}
              max={100}
              min={1}
              step={1}
              className="w-full py-2"
            />
            <p className="text-[10px] text-muted-foreground">调整算法对眨眼动作的识别灵敏度，推荐值为 70%-85%</p>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">数据更新频率</label>
              <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50">{(refreshInterval / 1000).toFixed(1)}s</Badge>
            </div>
            <Slider
              value={[refreshInterval]}
              onValueChange={(val) => onRefreshIntervalChange(val[0])}
              max={5000}
              min={200}
              step={100}
              className="w-full py-2"
            />
            <p className="text-[10px] text-muted-foreground">设置模拟数据的刷新频率。较低的值意味着更频繁的更新，但会增加计算负担。</p>
          </div>
          
          <div className="space-y-4 pt-2 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-full">
                  <Volume2 className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <label className="text-sm font-semibold block">声音警报</label>
                  <span className="text-[10px] text-muted-foreground">当检测到干眼风险时播放提示音</span>
                </div>
              </div>
              <Switch
                checked={audioAlerts}
                onCheckedChange={setAudioAlerts}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-muted rounded-full">
                  <Save className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <label className="text-sm font-semibold block">自动保存</label>
                  <span className="text-[10px] text-muted-foreground">自动将监测数据保存至本地日志</span>
                </div>
              </div>
              <Switch
                checked={autoSave}
                onCheckedChange={setAutoSave}
              />
            </div>
          </div>
          
          <Button variant="secondary" className="w-full h-12 font-semibold mt-auto" onClick={() => setConfigOpen(true)}>
            <Settings className="h-4 w-4 mr-2" />
            高级传感器参数配置
          </Button>

          {/* 传感器配置对话框 */}
          <Dialog open={configOpen} onOpenChange={setConfigOpen}>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle className="text-xl">高级传感器配置</DialogTitle>
                <DialogDescription>
                  设置底层传感器参数。这些设置将通过蓝牙直接写入硬件固件。
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-6 py-4">
                <div className="space-y-2">
                  <Label htmlFor="sampleRate" className="text-sm font-bold">硬件采样率 (Hz)</Label>
                  <Input
                    id="sampleRate"
                    type="number"
                    min={1}
                    max={200}
                    value={configSampleRate}
                    onChange={(e) => setConfigSampleRate(parseInt(e.target.value || '0'))}
                    className="h-11"
                  />
                  <p className="text-[10px] text-muted-foreground">范围: 1-200 Hz。更高的采样率会增加功耗但提高精度。</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="threshold" className="text-sm font-bold">干眼判定阈值 (0-100)</Label>
                  <Input
                    id="threshold"
                    type="number"
                    min={0}
                    max={100}
                    value={configThreshold}
                    onChange={(e) => setConfigThreshold(parseInt(e.target.value || '0'))}
                    className="h-11"
                  />
                  <p className="text-[10px] text-muted-foreground">当稳定性低于此值时触发风险警报。</p>
                </div>
                {configError && (
                  <Alert variant="destructive" className="animate-in shake">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{configError}</AlertDescription>
                  </Alert>
                )}
              </div>
              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  variant="ghost"
                  onClick={() => setConfigOpen(false)}
                  disabled={configSaving}
                >
                  取消
                </Button>
                <Button
                  onClick={async () => {
                    setConfigError(null);
                    if (Number.isNaN(configSampleRate) || configSampleRate < 1 || configSampleRate > 200) {
                      setConfigError('采样率范围应为 1-200 Hz');
                      return;
                    }
                    if (Number.isNaN(configThreshold) || configThreshold < 0 || configThreshold > 100) {
                      setConfigError('干眼阈值范围应为 0-100');
                      return;
                    }
                    if (!bluetoothService.isDeviceConnected()) {
                      setConfigError('蓝牙设备未连接，无法下发配置');
                      return;
                    }
                    setConfigSaving(true);
                    try {
                      const ok = await bluetoothService.sendSensorConfig({
                        sampleRate: configSampleRate,
                        threshold: configThreshold,
                      });
                      if (!ok) throw new Error('蓝牙下发失败');
                      localStorage.setItem('dry-eye-monitor-config-sampleRate', String(configSampleRate));
                      localStorage.setItem('dry-eye-monitor-config-threshold', String(configThreshold));
                      setConfigOpen(false);
                    } catch (e) {
                      setConfigError(e instanceof Error ? e.message : '保存失败，请重试');
                    } finally {
                      setConfigSaving(false);
                    }
                  }}
                  disabled={configSaving}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {configSaving ? '正在下发...' : '保存并下发至硬件'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </Card>
    </div>
  );
}