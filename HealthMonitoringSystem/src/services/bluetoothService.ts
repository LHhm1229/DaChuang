interface NavigatorWithBluetooth extends Navigator {
  bluetooth?: Bluetooth;
}

interface Bluetooth {
  requestDevice(options: RequestDeviceOptions): Promise<BluetoothDevice>;
}

interface RequestDeviceOptions {
  filters?: BluetoothLEScanFilter[];
  optionalServices?: BluetoothServiceUUID[];
}

interface BluetoothLEScanFilter {
  services?: BluetoothServiceUUID[];
  namePrefix?: string;
}

type BluetoothServiceUUID = string;
type BluetoothCharacteristicUUID = string;

interface BluetoothDevice {
  name: string;
  gatt?: BluetoothRemoteGATTServer;
}

interface BluetoothRemoteGATTServer {
  connect(): Promise<BluetoothRemoteGATTServer>;
  disconnect(): void;
  getPrimaryService(service: BluetoothServiceUUID): Promise<BluetoothRemoteGATTService>;
}

interface BluetoothRemoteGATTService {
  getCharacteristic(characteristic: BluetoothCharacteristicUUID): Promise<BluetoothRemoteGATTCharacteristic>;
}

interface BluetoothRemoteGATTCharacteristic {
  startNotifications(): Promise<BluetoothRemoteGATTCharacteristic>;
  addEventListener(type: string, listener: (event: Event) => void): void;
  value?: DataView;
}

export interface BluetoothSensorData {
  values: number[];
  timestamp: number;
  signalQuality: number;
}

interface BluetoothDeviceInfo {
  device: BluetoothDevice;
  server: BluetoothRemoteGATTServer;
  service: BluetoothRemoteGATTService;
  characteristic: BluetoothRemoteGATTCharacteristic;
}

class BluetoothService {
  private deviceInfo: BluetoothDeviceInfo | null = null;
  private listeners: ((data: BluetoothSensorData) => void)[] = [];
  private errorListeners: ((error: Error) => void)[] = [];

  isSupported(): boolean {
    return 'bluetooth' in navigator;
  }

  isDeviceConnected(): boolean {
    return this.deviceInfo !== null;
  }

  getDeviceInfo() {
    if (!this.deviceInfo) return null;
    return {
      deviceName: this.deviceInfo.device.name,
      deviceId: this.deviceInfo.device.name
    };
  }

  addListener(callback: (data: BluetoothSensorData) => void): void {
    this.listeners.push(callback);
  }

  removeListener(callback: (data: BluetoothSensorData) => void): void {
    this.listeners = this.listeners.filter(l => l !== callback);
  }

  addErrorListener(callback: (error: Error) => void): void {
    this.errorListeners.push(callback);
  }

  removeErrorListener(callback: (error: Error) => void): void {
    this.errorListeners = this.errorListeners.filter(l => l !== callback);
  }

  private notifyListeners(data: BluetoothSensorData): void {
    console.log(`[BluetoothService] 通知 ${this.listeners.length} 个监听器`);
    this.listeners.forEach(listener => listener(data));
  }

  private notifyError(error: Error): void {
    this.errorListeners.forEach(listener => listener(error));
  }

  async connectDevice(): Promise<boolean> {
    try {
      const navigatorWithBt = navigator as NavigatorWithBluetooth;
      if (!navigatorWithBt.bluetooth) {
        throw new Error('浏览器不支持蓝牙功能');
      }

      const device = await navigatorWithBt.bluetooth.requestDevice({
        filters: [
          { services: ['0000fff0-0000-1000-8000-00805f9b34fb'] },
          { namePrefix: 'STM32' }
        ],
        optionalServices: ['0000fff1-0000-1000-8000-00805f9b34fb']
      });

      const server = await device.gatt?.connect();
      if (!server) {
        throw new Error('无法连接GATT服务器');
      }

      const service = await server.getPrimaryService('0000fff0-0000-1000-8000-00805f9b34fb');
      const characteristic = await service.getCharacteristic('0000fff1-0000-1000-8000-00805f9b34fb');

      characteristic.addEventListener('characteristicvaluechanged', (event) => {
        try {
          const target = event.target as unknown as BluetoothRemoteGATTCharacteristic;
          const value = target.value;
          if (!value) return;

          const dataArray = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
          
          // 调试：打印原始16进制数据
          const hexDebug: string[] = [];
          for (let i = 0; i < Math.min(dataArray.length, 20); i++) {
            hexDebug.push(dataArray[i].toString(16).padStart(2, '0').toUpperCase());
          }
          console.log(`[Bluetooth] 原始16进制数据 (前${hexDebug.length}字节): ${hexDebug.join(' ')}`);
          console.log(`[Bluetooth] 字节数组长度: ${dataArray.length}`);
          
          // 解析16进制字节数据为浮点数数组
          // 假设每4字节组成一个float32（小端序）
          const floatValues: number[] = [];
          
          if (dataArray.length >= 4) {
            for (let i = 0; i < dataArray.length; i += 4) {
              if (i + 4 <= dataArray.length) {
                const view = new DataView(dataArray.buffer, dataArray.byteOffset + i, 4);
                const floatVal = view.getFloat32(0, true);
                
                if (isFinite(floatVal)) {
                  floatValues.push(floatVal);
                } else {
                  console.warn(`[Bluetooth] 无效浮点数 at index ${i}: ${floatVal}, hex: ${hexDebug.slice(i, i+4).join(' ')}`);
                }
              }
            }
          }
          
          // 如果解析float32失败或数据不符合，尝试将每个字节作为0-255的原始值
          if (floatValues.length === 0 && dataArray.length > 0) {
            console.log('[Bluetooth] 使用原始字节值作为数据');
            for (let i = 0; i < dataArray.length; i++) {
              floatValues.push(dataArray[i] / 255.0);
            }
          }
          
          console.log(`[Bluetooth] 解析后数据: ${floatValues.slice(0, 5).map(v => v.toFixed(4)).join(', ')}...`);
          
          const sensorData: BluetoothSensorData = {
            values: floatValues,
            timestamp: Date.now(),
            signalQuality: 100
          };

          this.notifyListeners(sensorData);
        } catch (error) {
          console.error('[Bluetooth] 解析数据错误:', error);
          this.notifyError(error as Error);
        }
      });

      await characteristic.startNotifications();

      this.deviceInfo = { device, server, service, characteristic };
      return true;
    } catch (error) {
      this.notifyError(error as Error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    if (this.deviceInfo) {
      this.deviceInfo.server.disconnect();
      this.deviceInfo = null;
    }
  }

  clearDataBuffer(): void {
  }
}

export const bluetoothService = new BluetoothService();
