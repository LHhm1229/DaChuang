// 蓝牙服务 - 连接单片机并接收数据

// Web Bluetooth API 类型定义
declare global {
  interface Navigator {
    bluetooth: Bluetooth;
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
    name?: string;
    gatt?: BluetoothRemoteGATTServer;
    addEventListener(type: string, listener: EventListener): void;
  }
  
  interface BluetoothRemoteGATTServer {
    connect(): Promise<BluetoothRemoteGATTServer>;
    disconnect(): void;
    getPrimaryService(service: BluetoothServiceUUID): Promise<BluetoothRemoteGATTService>;
    connected: boolean;
  }
  
  interface BluetoothRemoteGATTService {
    getCharacteristic(characteristic: BluetoothCharacteristicUUID): Promise<BluetoothRemoteGATTCharacteristic>;
  }
  
  interface BluetoothRemoteGATTCharacteristic {
    startNotifications(): Promise<BluetoothRemoteGATTCharacteristic>;
    writeValue(value: BufferSource): Promise<void>;
    readValue(): Promise<DataView>;
    addEventListener(type: string, listener: EventListener): void;
    value?: DataView;
  }
}

// 原始传感器数据
export interface RawSensorData {
  timestamp: number;
  values: number[]; // float数组，来自模数转换
  signalQuality: number;
}

// 简化的数据接口 - 只包含原始数据
export interface BluetoothDryEyeData {
  rawData: RawSensorData;
  timestamp: number;
  // TODO: 在这里添加您的算法处理结果
  // 例如: eyeHealthScore?: number;
  // 例如: eyeStatus?: 'open' | 'closing' | 'closed';
}

// 蓝牙设备信息
interface BluetoothDeviceInfo {
  device: BluetoothDevice;
  server: BluetoothRemoteGATTServer;
  service: BluetoothRemoteGATTService;
  characteristic: BluetoothRemoteGATTCharacteristic;
}

class BluetoothService {
  private deviceInfo: BluetoothDeviceInfo | null = null;
  private listeners: ((data: BluetoothDryEyeData) => void)[] = [];
  private errorListeners: ((error: string) => void)[] = [];
  private isConnected = false;
  private reconnectInterval: any = null;
  private dataParseErrors = 0;
  private maxParseErrors = 10;
  private rawDataBuffer: number[] = []; // 存储原始数据
  private dataReceiveCount = 0; // 数据接收计数
  private lastDataTime = 0; // 上次数据接收时间
  // TODO: 在这里添加您的算法相关变量
  // 例如: private dryEyeAlgorithm: DryEyeDetectionAlgorithm;

  // 检查浏览器是否支持Web Bluetooth
  isSupported(): boolean {
    return 'bluetooth' in navigator;
  }

  // JavaScript版本的BytesToFloat函数
  private bytesToFloat(bytes: Uint8Array): number {
    // 创建ArrayBuffer和DataView来处理字节数据
    const buffer = new ArrayBuffer(4);
    const view = new DataView(buffer);
    
    // 按照小端序（little-endian）存储字节
    view.setUint8(0, bytes[0]);
    view.setUint8(1, bytes[1]);
    view.setUint8(2, bytes[2]);
    view.setUint8(3, bytes[3]);
    
    // 读取为float32
    return view.getFloat32(0, true); // true表示小端序
  }

  // 解析原始字节数据
  private parseRawData(buffer: DataView): RawSensorData | null {
    try {
      const dataArray = new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
      
      // 检查数据长度，应该是4的倍数（每个float占4字节）
      if (dataArray.length % 4 !== 0) {
        console.warn('数据长度不是4的倍数，可能数据不完整');
        return null;
      }

      const floatValues: number[] = [];
      
      // 每4个字节转换为一个float
      for (let i = 0; i < dataArray.length; i += 4) {
        const bytes = dataArray.slice(i, i + 4);
        const floatValue = this.bytesToFloat(bytes);
        floatValues.push(floatValue);
      }

      console.log('解析的原始float数据:', floatValues);

      return {
        timestamp: Date.now(),
        values: floatValues,
        signalQuality: this.calculateSignalQuality(floatValues)
      };
    } catch (error) {
      console.error('解析原始数据失败:', error);
      return null;
    }
  }

  // 计算信号质量（基于数据稳定性）
  private calculateSignalQuality(values: number[]): number {
    if (values.length === 0) return 0;
    
    // 简单的信号质量计算：基于数据的方差
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);
    
    // 将标准差转换为0-100的质量分数（标准差越小，质量越高）
    const quality = Math.max(0, Math.min(100, 100 - (stdDev * 10)));
    return Math.round(quality);
  }

  // 将原始信号转换为眼部监测数据
  private processRawDataToDryEyeData(rawData: RawSensorData): BluetoothDryEyeData {
    // 将原始数据添加到缓冲区
    this.rawDataBuffer.push(...rawData.values);
    
    // 保持缓冲区大小（例如最近1000个数据点）
    const maxBufferSize = 1000;
    if (this.rawDataBuffer.length > maxBufferSize) {
      this.rawDataBuffer = this.rawDataBuffer.slice(-maxBufferSize);
    }

    // 更新统计信息
    this.dataReceiveCount++;
    const currentTime = Date.now();
    const timeDiff = this.lastDataTime > 0 ? currentTime - this.lastDataTime : 0;
    this.lastDataTime = currentTime;

    // 在终端显示原始数据
    const timestamp = new Date().toLocaleTimeString("zh-CN");
    const dataInfo = `=== 原始数据接收 ===
时间戳: ${timestamp}
数据点数量: ${rawData.values.length}
原始数据: [${rawData.values.map(v => v.toFixed(3)).join(', ')}]
信号质量: ${rawData.signalQuality}%
缓冲区大小: ${this.rawDataBuffer.length}
==================`;

    // 浏览器控制台显示
    console.log(dataInfo);
    
    // Cursor终端显示 - 结构化数据
    console.log('📡 蓝牙数据接收:', {
      timestamp,
      receiveCount: this.dataReceiveCount,
      dataCount: rawData.values.length,
      values: rawData.values,
      signalQuality: rawData.signalQuality,
      bufferSize: this.rawDataBuffer.length,
      timeDiff: timeDiff > 0 ? `${timeDiff}ms` : '首次接收'
    });

    // 每10次接收显示一次统计信息
    if (this.dataReceiveCount % 10 === 0) {
      const stats = this.getBufferStats();
      console.log('📊 数据统计 (每10次):', {
        totalReceived: this.dataReceiveCount,
        bufferStats: stats,
        averageInterval: timeDiff > 0 ? `${Math.round(timeDiff)}ms` : 'N/A'
      });
    }
    // TODO: 在这里调用您的算法
    // 例如: const eyeHealthScore = this.yourDryEyeAlgorithm(rawData.values);
    // 例如: const eyeStatus = this.yourEyeDetectionAlgorithm(rawData.values);

    return {
      rawData,
      timestamp: rawData.timestamp
      // TODO: 在这里添加您的算法处理结果
      // 例如: eyeHealthScore,
      // 例如: eyeStatus
    };
  }

  // TODO: 在这里添加您的算法函数
  // 例如: private yourDryEyeAlgorithm(values: number[]): number { ... }
  // 例如: private yourEyeDetectionAlgorithm(values: number[]): string { ... }

  // 连接蓝牙设备
  async connectDevice(): Promise<boolean> {
    try {
      console.log('正在搜索蓝牙设备...');
      
      // 请求蓝牙设备
      const device = await navigator.bluetooth.requestDevice({
        // 根据你的单片机蓝牙服务UUID进行配置
        filters: [
          {
            services: ['0000fff0-0000-1000-8000-00805f9b34fb'] // 服务UUID: fff0
          },
          {
            namePrefix: 'DryEye' // 新设备名称前缀
          }
        ],
        optionalServices: [
          '0000fff1-0000-1000-8000-00805f9b34fb', // 特征UUID: fff1
          '0000fff2-0000-1000-8000-00805f9b34fb'  // 特征UUID: fff2
        ]
      });

      console.log('设备已选择:', device.name);

      // 连接到GATT服务器
      const server = await device.gatt?.connect();
      if (!server) {
        throw new Error('无法连接到GATT服务器');
      }

      // 获取服务 (fff0)
      const service = await server.getPrimaryService('0000fff0-0000-1000-8000-00805f9b34fb');
      
      // 获取特征 (fff1 - 用于数据接收)
      const characteristic = await service.getCharacteristic('0000fff1-0000-1000-8000-00805f9b34fb');

      this.deviceInfo = { device, server, service, characteristic };
      this.isConnected = true;

      // 监听数据变化
      await this.startDataListener();

      // 监听设备断开连接
      device.addEventListener('gattserverdisconnected', () => {
        console.log('蓝牙设备已断开连接');
        this.isConnected = false;
        this.handleDisconnection();
      });

      console.log('蓝牙设备连接成功');
      console.log('🔗 蓝牙连接成功:', {
        deviceName: device.name,
        timestamp: new Date().toLocaleTimeString("zh-CN"),
        status: 'connected'
      });
      return true;

    } catch (error) {
      console.error('蓝牙连接失败:', error);
      console.log('❌ 蓝牙连接失败:', {
        error: error instanceof Error ? error.message : '未知错误',
        timestamp: new Date().toLocaleTimeString("zh-CN"),
        status: 'failed'
      });
      this.isConnected = false;
      return false;
    }
  }

  // 开始监听数据
  private async startDataListener() {
    if (!this.deviceInfo) return;

    try {
      // 启用通知
      await this.deviceInfo.characteristic.startNotifications();
      
      this.deviceInfo.characteristic.addEventListener('characteristicvaluechanged', (event) => {
        const value = (event.target as unknown as BluetoothRemoteGATTCharacteristic).value;
        if (value) {
          // 解析原始字节数据
          const rawData = this.parseRawData(value);
          if (rawData) {
            // 处理原始数据（在终端显示）
            const processedData = this.processRawDataToDryEyeData(rawData);
            this.notifyListeners(processedData);
          } else {
            // 如果原始数据解析失败，尝试JSON格式
            const jsonData = this.parseDataFromBuffer(value);
            if (jsonData) {
              this.notifyListeners(jsonData);
            }
          }
        }
      });

      console.log('数据监听已启动');
      console.log('👂 数据监听启动:', {
        timestamp: new Date().toLocaleTimeString("zh-CN"),
        status: 'listening'
      });
    } catch (error) {
      console.error('启动数据监听失败:', error);
    }
  }

  // 解析从单片机接收的数据
  private parseDataFromBuffer(buffer: DataView): BluetoothDryEyeData | null {
    try {
      const decoder = new TextDecoder('utf-8');
      const jsonString = decoder.decode(buffer).trim();
      
      // 检查是否为空数据
      if (!jsonString) {
        console.warn('接收到空数据');
        return null;
      }

      console.log('接收到原始数据:', jsonString);
      
      // 解析JSON数据
      const rawData = JSON.parse(jsonString);
      
      // 验证必要字段
      if (!this.validateData(rawData)) {
        this.handleParseError('数据验证失败: 缺少必要字段');
        return null;
      }
      
      // 转换为标准格式（JSON数据解析）
      const processedData: BluetoothDryEyeData = {
        rawData: {
          timestamp: Date.now(),
          values: [rawData.eyeHealthScore || 0, rawData.blinkRate || 0],
          signalQuality: this.validateNumber(rawData.signalQuality, 0, 100) || 100
        },
        timestamp: Date.now()
      };

      // 重置解析错误计数
      this.dataParseErrors = 0;
      console.log('解析后的数据:', processedData);
      return processedData;
    } catch (error) {
      this.handleParseError(`数据解析失败: ${error instanceof Error ? error.message : '未知错误'}`);
      return null;
    }
  }

  // 处理解析错误
  private handleParseError(errorMessage: string) {
    this.dataParseErrors++;
    console.error(`数据解析错误 (${this.dataParseErrors}/${this.maxParseErrors}):`, errorMessage);
    
    // 通知错误监听器
    this.notifyErrorListeners(errorMessage);
    
    // 如果解析错误过多，可能需要重新连接
    if (this.dataParseErrors >= this.maxParseErrors) {
      console.error('数据解析错误过多，可能需要检查设备连接');
      this.notifyErrorListeners('数据解析错误过多，请检查设备连接状态');
    }
  }

  // 验证数据格式
  private validateData(data: any): boolean {
    return data && typeof data === 'object';
  }

  // 验证眼部状态
  private validateEyeStatus(status: any): 'open' | 'closing' | 'closed' | null {
    if (typeof status === 'string') {
      const validStatuses = ['open', 'closing', 'closed'];
      return validStatuses.includes(status) ? status as 'open' | 'closing' | 'closed' : null;
    }
    return null;
  }

  // 验证数字范围
  private validateNumber(value: any, min: number, max: number): number | null {
    const num = Number(value);
    if (isNaN(num) || num < min || num > max) {
      return null;
    }
    return num;
  }

  // 计算警报级别
  private calculateAlertLevel(eyeHealthScore: number): 'normal' | 'warning' | 'danger' {
    if (eyeHealthScore > 70) return 'normal';
    if (eyeHealthScore > 30) return 'warning';
    return 'danger';
  }

  // 处理断开连接
  private handleDisconnection() {
    // 尝试自动重连
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
    }

    this.reconnectInterval = setInterval(async () => {
      console.log('尝试重新连接...');
      const success = await this.connectDevice();
      if (success) {
        clearInterval(this.reconnectInterval!);
        this.reconnectInterval = null;
      }
    }, 5000); // 每5秒尝试重连
  }

  // 断开连接
  async disconnect() {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }

    if (this.deviceInfo?.server?.connected) {
      await this.deviceInfo.server.disconnect();
    }

    this.deviceInfo = null;
    this.isConnected = false;
    console.log('蓝牙连接已断开');
    console.log('🔌 蓝牙连接断开:', {
      timestamp: new Date().toLocaleTimeString("zh-CN"),
      status: 'disconnected',
      totalDataReceived: this.dataReceiveCount
    });
  }

  // 添加数据监听器
  addListener(callback: (data: BluetoothDryEyeData) => void) {
    this.listeners.push(callback);
  }

  // 移除数据监听器
  removeListener(callback: (data: BluetoothDryEyeData) => void) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  // 添加错误监听器
  addErrorListener(callback: (error: string) => void) {
    this.errorListeners.push(callback);
  }

  // 移除错误监听器
  removeErrorListener(callback: (error: string) => void) {
    const index = this.errorListeners.indexOf(callback);
    if (index > -1) {
      this.errorListeners.splice(index, 1);
    }
  }

  // 通知所有监听器
  private notifyListeners(data: BluetoothDryEyeData) {
    this.listeners.forEach(listener => listener(data));
  }

  // 通知所有错误监听器
  private notifyErrorListeners(error: string) {
    this.errorListeners.forEach(listener => listener(error));
  }

  // 检查连接状态
  isDeviceConnected(): boolean {
    return this.isConnected;
  }

  // 获取设备信息
  getDeviceInfo() {
    return this.deviceInfo ? {
      name: this.deviceInfo.device.name,
      connected: this.isConnected
    } : null;
  }

  // 发送校准命令到设备
  async sendCalibrationCommand(): Promise<boolean> {
    if (!this.deviceInfo || !this.isConnected) {
      throw new Error('设备未连接');
    }

    try {
      // 发送校准命令 - 使用JSON格式
      const calibrationCommand = {
        command: 'calibrate',
        timestamp: Date.now()
      };
      
      const commandString = JSON.stringify(calibrationCommand) + '\n';
      const encoder = new TextEncoder();
      const commandBuffer = encoder.encode(commandString);
      
      await this.deviceInfo.characteristic.writeValue(commandBuffer);
      
      console.log('校准命令已发送:', calibrationCommand);
      return true;
    } catch (error) {
      console.error('发送校准命令失败:', error);
      return false;
    }
  }

  // 下发传感器配置
  async sendSensorConfig(config: { sampleRate: number; threshold: number }): Promise<boolean> {
    if (!this.deviceInfo || !this.isConnected) {
      throw new Error('设备未连接');
    }

    try {
      const payload = {
        command: 'sensor_config',
        data: {
          sampleRate: config.sampleRate,
          threshold: config.threshold,
        },
        timestamp: Date.now(),
      };

      const encoder = new TextEncoder();
      const buffer = encoder.encode(JSON.stringify(payload) + '\n');
      await this.deviceInfo.characteristic.writeValue(buffer);
      console.log('传感器配置已下发:', payload);
      return true;
    } catch (error) {
      console.error('下发传感器配置失败:', error);
      return false;
    }
  }

  // 检查校准状态
  async checkCalibrationStatus(): Promise<boolean> {
    if (!this.deviceInfo || !this.isConnected) {
      return false;
    }

    try {
      // 读取校准状态
      const value = await this.deviceInfo.characteristic.readValue();
      const decoder = new TextDecoder();
      const status = decoder.decode(value);
      
      // 尝试解析JSON格式的状态
      try {
        const statusData = JSON.parse(status);
        return statusData.status === 'calibration_complete' || 
               statusData.calibrationStatus === 'success';
      } catch {
        // 如果不是JSON格式，检查是否包含成功标识
        return status.includes('calibration_complete') || 
               status.includes('CALIB_OK') || 
               status.includes('success');
      }
    } catch (error) {
      console.error('检查校准状态失败:', error);
      return false;
    }
  }

  // TODO: 在这里添加您的算法控制方法
  // 例如: setAlgorithmEnabled(enabled: boolean) { ... }
  // 例如: getAlgorithmStatus(): boolean { ... }

  // 清空数据缓冲区
  clearDataBuffer() {
    const bufferSize = this.rawDataBuffer.length;
    this.rawDataBuffer = [];
    console.log('数据缓冲区已清空');
    console.log('🗑️ 缓冲区已清空:', {
      timestamp: new Date().toLocaleTimeString("zh-CN"),
      clearedDataPoints: bufferSize,
      status: 'cleared'
    });
  }

  // 获取缓冲区数据
  getBufferData(): number[] {
    return [...this.rawDataBuffer];
  }

  // 获取缓冲区统计信息
  getBufferStats() {
    if (this.rawDataBuffer.length === 0) {
      return {
        count: 0,
        mean: 0,
        variance: 0,
        min: 0,
        max: 0
      };
    }

    const mean = this.rawDataBuffer.reduce((sum, val) => sum + val, 0) / this.rawDataBuffer.length;
    const variance = this.rawDataBuffer.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / this.rawDataBuffer.length;
    const min = Math.min(...this.rawDataBuffer);
    const max = Math.max(...this.rawDataBuffer);

    return {
      count: this.rawDataBuffer.length,
      mean: Math.round(mean * 1000) / 1000,
      variance: Math.round(variance * 1000) / 1000,
      min: Math.round(min * 1000) / 1000,
      max: Math.round(max * 1000) / 1000
    };
  }
}

// 导出单例实例
export const bluetoothService = new BluetoothService();
