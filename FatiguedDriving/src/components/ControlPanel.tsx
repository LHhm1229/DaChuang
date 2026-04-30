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
}

export function ControlPanel({ isMonitoring, onToggleMonitoring }: ControlPanelProps) {
  // 从本地存储加载设置，如果没有则使用默认值
  const [sensitivity, setSensitivity] = useState(() => {
    const saved = localStorage.getItem('fatigue-monitor-sensitivity');
    return saved ? [parseInt(saved)] : [75];
  });
  
  const [audioAlerts, setAudioAlerts] = useState(() => {
    const saved = localStorage.getItem('fatigue-monitor-audio-alerts');
    return saved ? JSON.parse(saved) : true;
  });
  
  const [autoSave, setAutoSave] = useState(() => {
    const saved = localStorage.getItem('fatigue-monitor-auto-save');
    return saved ? JSON.parse(saved) : true;
  });
  
  const [sensorConnected, setSensorConnected] = useState(true);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibrationResult, setCalibrationResult] = useState<'success' | 'error' | null>(null);
  const [calibrationMessage, setCalibrationMessage] = useState<string>('');

  // 传感器配置对话框状态
  const [configOpen, setConfigOpen] = useState(false);
  const [configSampleRate, setConfigSampleRate] = useState(() => {
    const saved = localStorage.getItem('fatigue-monitor-config-sampleRate');
    return saved ? parseInt(saved) : 50;
  });
  const [configThreshold, setConfigThreshold] = useState(() => {
    const saved = localStorage.getItem('fatigue-monitor-config-threshold');
    return saved ? parseInt(saved) : 70;
  });
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  // 保存设置到本地存储并应用到数据服务
  useEffect(() => {
    localStorage.setItem('fatigue-monitor-sensitivity', sensitivity[0].toString());
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
    localStorage.setItem('fatigue-monitor-audio-alerts', JSON.stringify(audioAlerts));
  }, [audioAlerts]);

  useEffect(() => {
    localStorage.setItem('fatigue-monitor-auto-save', JSON.stringify(autoSave));
  }, [autoSave]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 监控控制 */}
      <Card className="p-6">
        <h3 className="mb-6">监控控制</h3>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm mb-1">监控状态</div>
              <Badge variant={isMonitoring ? "default" : "secondary"}>
                {isMonitoring ? '监控中' : '已停止'}
              </Badge>
            </div>
            <Button
              onClick={onToggleMonitoring}
              variant={isMonitoring ? "destructive" : "default"}
              size="lg"
              className="flex items-center gap-2"
            >
              {isMonitoring ? (
                <>
                  <Square className="h-4 w-4" />
                  停止监控
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  开始监控
                </>
              )}
            </Button>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wifi className="h-4 w-4" />
              <span>传感器连接</span>
            </div>
            <Badge variant={sensorConnected ? "default" : "destructive"}>
              {sensorConnected ? '已连接' : '未连接'}
            </Badge>
          </div>
          
          <Button
            variant="outline"
            onClick={handleCalibration}
            disabled={!sensorConnected || isMonitoring || isCalibrating}
            className="w-full flex items-center gap-2"
          >
            <Zap className="h-4 w-4" />
            {isCalibrating ? '校准中...' : '传感器校准'}
          </Button>

          {/* 校准结果显示 */}
          {calibrationResult && (
            <Alert className={calibrationResult === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
              {calibrationResult === 'success' ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-600" />
              )}
              <AlertDescription className={calibrationResult === 'success' ? 'text-green-800' : 'text-red-800'}>
                {calibrationMessage}
              </AlertDescription>
            </Alert>
          )}
        </div>
      </Card>

      {/* 系统设置 */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="h-4 w-4" />
          <h3>系统设置</h3>
        </div>
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label>检测灵敏度</label>
              <span className="text-sm text-muted-foreground">{sensitivity[0]}%</span>
            </div>
            <Slider
              value={sensitivity}
              onValueChange={setSensitivity}
              max={100}
              min={1}
              step={1}
              className="w-full"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 className="h-4 w-4" />
              <label>声音警报</label>
            </div>
            <Switch
              checked={audioAlerts}
              onCheckedChange={setAudioAlerts}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Save className="h-4 w-4" />
              <label>自动保存</label>
            </div>
            <Switch
              checked={autoSave}
              onCheckedChange={setAutoSave}
            />
          </div>
          
          <Button variant="outline" className="w-full" onClick={() => setConfigOpen(true)}>
            <Settings className="h-4 w-4 mr-2" />
            传感器配置
          </Button>

          {/* 传感器配置对话框 */}
          <Dialog open={configOpen} onOpenChange={setConfigOpen}>
            <DialogTrigger asChild>
              <span></span>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>传感器配置</DialogTitle>
                <DialogDescription>设置采样率与阈值，保存后将通过蓝牙下发到设备。</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="sampleRate">采样率 (Hz)</Label>
                  <Input
                    id="sampleRate"
                    type="number"
                    min={1}
                    max={200}
                    value={configSampleRate}
                    onChange={(e) => setConfigSampleRate(parseInt(e.target.value || '0'))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="threshold">疲劳阈值 (0-100)</Label>
                  <Input
                    id="threshold"
                    type="number"
                    min={0}
                    max={100}
                    value={configThreshold}
                    onChange={(e) => setConfigThreshold(parseInt(e.target.value || '0'))}
                  />
                </div>
                {configError && (
                  <Alert className="border-red-200 bg-red-50">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <AlertDescription className="text-red-800">{configError}</AlertDescription>
                  </Alert>
                )}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setConfigOpen(false)}
                  disabled={configSaving}
                >
                  取消
                </Button>
                <Button
                  onClick={async () => {
                    setConfigError(null);
                    // 基础校验
                    if (Number.isNaN(configSampleRate) || configSampleRate < 1 || configSampleRate > 200) {
                      setConfigError('采样率范围应为 1-200 Hz');
                      return;
                    }
                    if (Number.isNaN(configThreshold) || configThreshold < 0 || configThreshold > 100) {
                      setConfigError('疲劳阈值范围应为 0-100');
                      return;
                    }
                    if (!bluetoothService.isDeviceConnected()) {
                      setConfigError('蓝牙设备未连接，无法下发配置');
                      return;
                    }
                    setConfigSaving(true);
                    try {
                      // 下发设备配置
                      const ok = await bluetoothService.sendSensorConfig({
                        sampleRate: configSampleRate,
                        threshold: configThreshold,
                      });
                      if (!ok) {
                        throw new Error('蓝牙下发失败');
                      }

                      // 持久化本地
                      localStorage.setItem('fatigue-monitor-config-sampleRate', String(configSampleRate));
                      localStorage.setItem('fatigue-monitor-config-threshold', String(configThreshold));
                      setConfigOpen(false);
                    } catch (e) {
                      setConfigError(e instanceof Error ? e.message : '保存失败，请重试');
                    } finally {
                      setConfigSaving(false);
                    }
                  }}
                  disabled={configSaving}
                >
                  保存并下发
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </Card>
    </div>
  );
}