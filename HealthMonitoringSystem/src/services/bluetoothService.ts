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
  private connectionListeners: ((connected: boolean) => void)[] = [];

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

  addConnectionListener(callback: (connected: boolean) => void): void {
    this.connectionListeners.push(callback);
    // 立即通知当前状态
    callback(this.isDeviceConnected());
  }

  removeConnectionListener(callback: (connected: boolean) => void): void {
    this.connectionListeners = this.connectionListeners.filter(l => l !== callback);
  }

  private notifyListeners(data: BluetoothSensorData): void {
    this.listeners.forEach(listener => listener(data));
  }

  private notifyError(error: Error): void {
    this.errorListeners.forEach(listener => listener(error));
  }

  private notifyConnection(connected: boolean): void {
    this.connectionListeners.forEach(listener => listener(connected));
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

      // 监听 BLE 断连事件，避免 UI 一直显示 CONNECTED
      device.addEventListener('gattserverdisconnected', () => {
        console.log('[BluetoothService] BLE 连接断开');
        this.deviceInfo = null;
        this.notifyConnection(false);
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
          const floatValues: number[] = [];

          if (dataArray.length >= 4) {
            for (let i = 0; i < dataArray.length; i += 4) {
              if (i + 4 <= dataArray.length) {
                const view = new DataView(dataArray.buffer, dataArray.byteOffset + i, 4);
                const floatVal = view.getFloat32(0, true);
                if (isFinite(floatVal)) {
                  floatValues.push(floatVal);
                }
              }
            }
          }

          if (floatValues.length === 0 && dataArray.length > 0) {
            for (let i = 0; i < dataArray.length; i++) {
              floatValues.push(dataArray[i] / 255.0);
            }
          }
          
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
      
      // 成功连接后通知
      this.notifyConnection(true);
      
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
      // 断开连接后通知
      this.notifyConnection(false);
    }
  }

  clearDataBuffer(): void {
  }
}

export const bluetoothService = new BluetoothService();
