import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Bluetooth, Wifi, WifiOff, CheckCircle, AlertCircle, XCircle, Activity, Clock, Signal, Settings, Trash2, BarChart3 } from 'lucide-react';
import { bluetoothService, BluetoothFatigueData } from '../services/bluetoothService';

interface BluetoothControlProps {
  onDataReceived: (data: BluetoothFatigueData) => void;
}

export function BluetoothControl({ onDataReceived }: BluetoothControlProps) {
  const [isSupported, setIsSupported] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastDataReceived, setLastDataReceived] = useState<Date | null>(null);
  const [dataCount, setDataCount] = useState(0);
  const [connectionQuality, setConnectionQuality] = useState<number>(0);

  useEffect(() => {
    // 检查浏览器是否支持Web Bluetooth
    setIsSupported(bluetoothService.isSupported());
    
    // 检查当前连接状态
    setIsConnected(bluetoothService.isDeviceConnected());
    const deviceInfo = bluetoothService.getDeviceInfo();
    if (deviceInfo) {
      setDeviceName(deviceInfo.name);
    }

    // 添加数据监听器
    bluetoothService.addListener(handleDataReceived);
    
    // 添加错误监听器
    bluetoothService.addErrorListener(handleError);

    return () => {
      bluetoothService.removeListener(handleDataReceived);
      bluetoothService.removeErrorListener(handleError);
    };
  }, []);

  const handleDataReceived = (data: BluetoothFatigueData) => {
    setLastDataReceived(new Date());
    setDataCount(prev => prev + 1);
    setConnectionQuality(data.rawData.signalQuality);
    
    // 数据已在终端显示，这里只更新界面状态
    onDataReceived(data);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    console.error('蓝牙错误:', errorMessage);
  };

  const handleClearBuffer = () => {
    bluetoothService.clearDataBuffer();
    console.log('数据缓冲区已清空');
  };

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      const success = await bluetoothService.connectDevice();
      if (success) {
        setIsConnected(true);
        const deviceInfo = bluetoothService.getDeviceInfo();
        if (deviceInfo) {
          setDeviceName(deviceInfo.name);
        }
      } else {
        setError('连接失败，请检查设备是否可用');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '连接失败');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await bluetoothService.disconnect();
      setIsConnected(false);
      setDeviceName(null);
      setError(null);
    } catch (err) {
      setError('断开连接失败');
    }
  };

  if (!isSupported) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bluetooth className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold">蓝牙连接</h3>
        </div>
        <Alert className="border-yellow-200 bg-yellow-50">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="text-yellow-800">
            您的浏览器不支持Web Bluetooth API。请使用Chrome、Edge或Safari浏览器。
          </AlertDescription>
        </Alert>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-4">
        <Bluetooth className="h-6 w-6 text-blue-600" />
        <h3 className="text-lg font-semibold">蓝牙连接</h3>
      </div>

      {/* 连接状态 */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          {isConnected ? (
            <CheckCircle className="h-4 w-4 text-green-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600" />
          )}
          <span className="text-sm font-medium">
            状态: {isConnected ? '已连接' : '未连接'}
          </span>
        </div>
        
        {deviceName && (
          <div className="text-sm text-muted-foreground">
            设备: {deviceName}
          </div>
        )}
      </div>

      {/* 连接按钮 */}
      <div className="mb-4">
        {!isConnected ? (
          <Button 
            onClick={handleConnect} 
            disabled={isConnecting}
            className="w-full"
          >
            {isConnecting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                连接中...
              </>
            ) : (
              <>
                <Bluetooth className="h-4 w-4 mr-2" />
                连接蓝牙设备
              </>
            )}
          </Button>
        ) : (
          <Button 
            onClick={handleDisconnect}
            variant="outline"
            className="w-full"
          >
            <WifiOff className="h-4 w-4 mr-2" />
            断开连接
          </Button>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* 数据控制 */}
      {isConnected && (
        <div className="mt-4">
          <Card className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <Settings className="h-5 w-5 text-blue-600" />
              <h4 className="text-sm font-medium">数据控制</h4>
            </div>
            
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleClearBuffer}
                className="flex items-center gap-2"
              >
                <Trash2 className="h-3 w-3" />
                清空缓冲区
              </Button>
            </div>
            
            <div className="mt-3 text-xs text-gray-600">
              <p>• 原始数据会在浏览器控制台显示</p>
              <p>• 按F12打开开发者工具查看详细数据</p>
            </div>
          </Card>
        </div>
      )}

      {/* 数据接收状态 */}
      {isConnected && (
        <div className="mt-4 space-y-4">
          <Card className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <Activity className="h-5 w-5 text-green-600" />
              <h4 className="text-sm font-medium">数据接收状态</h4>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-3">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{dataCount}</div>
                <div className="text-xs text-gray-600">接收次数</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{connectionQuality}%</div>
                <div className="text-xs text-gray-600">信号质量</div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>信号强度</span>
                <span>{connectionQuality}%</span>
              </div>
              <Progress value={connectionQuality} className="h-2" />
            </div>

            {lastDataReceived && (
              <div className="mt-3 text-xs text-gray-600">
                <Clock className="h-3 w-3 inline mr-1" />
                最后接收: {lastDataReceived.toLocaleTimeString("zh-CN")}
              </div>
            )}
          </Card>

          {/* 数据接收提示 */}
          <Card className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              <h4 className="text-sm font-medium">数据接收状态</h4>
            </div>
            
            <div className="text-sm text-gray-600">
              <p>✅ 原始数据接收正常</p>
              <p>📊 数据在浏览器控制台显示</p>
              <p>🔧 算法处理位置已标记，等待您的实现</p>
            </div>
          </Card>
        </div>
      )}

      {/* 使用说明 */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium mb-2">使用说明</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• 确保单片机蓝牙模块已开启</li>
          <li>• 点击"连接蓝牙设备"开始搜索</li>
          <li>• 选择你的疲劳监测设备</li>
          <li>• 连接成功后原始数据会在控制台显示</li>
          <li>• 按F12打开开发者工具查看详细数据</li>
          <li>• 支持原始字节数据（4字节float）格式</li>
          <li>• 算法处理位置已标记，等待您的实现</li>
        </ul>
      </div>
    </Card>
  );
}
