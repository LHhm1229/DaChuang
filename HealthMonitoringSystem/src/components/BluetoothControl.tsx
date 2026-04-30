import { useState, useEffect } from 'react';
import { Bluetooth, Wifi, WifiOff, AlertCircle, XCircle, Trash2 } from 'lucide-react';
import { bluetoothService, BluetoothSensorData } from '../services/bluetoothService';

interface BluetoothControlProps {
  onDataReceived: (data: BluetoothSensorData) => void;
}

export function BluetoothControl({ onDataReceived }: BluetoothControlProps) {
  const [isSupported, setIsSupported] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [signalQuality, setSignalQuality] = useState(100);

  useEffect(() => {
    setIsSupported(bluetoothService.isSupported());
    setIsConnected(bluetoothService.isDeviceConnected());
    const deviceInfo = bluetoothService.getDeviceInfo();
    if (deviceInfo) {
      setDeviceName(deviceInfo.deviceName);
    }

    const handleDataReceived = (data: BluetoothSensorData) => {
      setSignalQuality(data.signalQuality);
      onDataReceived(data);
    };

    const handleError = (error: Error) => {
      setError(error.message);
      setIsConnected(false);
      setIsConnecting(false);
    };

    bluetoothService.addListener(handleDataReceived);
    bluetoothService.addErrorListener(handleError);

    return () => {
      bluetoothService.removeListener(handleDataReceived);
      bluetoothService.removeErrorListener(handleError);
    };
  }, [onDataReceived]);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);
    
    const success = await bluetoothService.connectDevice();
    
    if (success) {
      setIsConnected(true);
      const deviceInfo = bluetoothService.getDeviceInfo();
      if (deviceInfo) {
        setDeviceName(deviceInfo.deviceName);
      }
    } else {
      setError('连接失败，请检查设备是否可用');
    }
    
    setIsConnecting(false);
  };

  const handleDisconnect = async () => {
    await bluetoothService.disconnect();
    setIsConnected(false);
    setDeviceName(null);
    setError(null);
  };

  const handleClearBuffer = () => {
    bluetoothService.clearDataBuffer();
  };

  if (!isSupported) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bluetooth className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold">蓝牙连接</h3>
        </div>
        <div className="flex items-center gap-2 text-red-500">
          <AlertCircle className="h-5 w-5" />
          <span>您的浏览器不支持Web Bluetooth API。请使用Chrome、Edge或Safari浏览器。</span>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Bluetooth className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold">蓝牙连接</h3>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <span className="flex items-center gap-1 text-green-600 text-sm">
              <Wifi className="h-4 w-4" />
              已连接
            </span>
          ) : (
            <span className="flex items-center gap-1 text-gray-500 text-sm">
              <WifiOff className="h-4 w-4" />
              未连接
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <XCircle className="h-5 w-5 text-red-500" />
          <span className="text-sm text-red-600">{error}</span>
        </div>
      )}

      {isConnected && deviceName && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-green-800">{deviceName}</p>
              <p className="text-sm text-green-600">信号强度: {signalQuality}%</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleClearBuffer}
                className="p-2 rounded-lg hover:bg-green-100 transition-colors"
                title="清空数据缓冲区"
              >
                <Trash2 className="h-4 w-4 text-green-600" />
              </button>
            </div>
          </div>
        </div>
      )}

      <button
        onClick={isConnected ? handleDisconnect : handleConnect}
        disabled={isConnecting}
        className={`w-full py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
          isConnecting
            ? 'bg-gray-400 text-white cursor-not-allowed'
            : isConnected
            ? 'bg-red-500 hover:bg-red-600 text-white'
            : 'bg-primary hover:bg-primary/90 text-white'
        }`}
      >
        {isConnecting ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            连接中...
          </>
        ) : isConnected ? (
          <>
            <WifiOff className="h-5 w-5" />
            断开连接
          </>
        ) : (
          <>
            <Bluetooth className="h-5 w-5" />
            连接蓝牙设备
          </>
        )}
      </button>
    </div>
  );
}
