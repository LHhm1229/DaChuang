/**
 * App.tsx - 健康监测系统主入口
 * 基于统一WebSocket通信层 + 数据映射层
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Gateway } from './components/Gateway';
import { UnifiedBentoDashboard } from './components/UnifiedBentoDashboard';
import { BluetoothControl } from './components/BluetoothControl';
import { GlassCard } from './components/ui/GlassCard';
import { Eye, Moon, Car, Home, Settings, HelpCircle, Bluetooth } from 'lucide-react';
import { useDynamicWebSocket, ModuleType } from './hooks/useDynamicWebSocket';
import { mapModuleData, UnifiedMetricData } from './services/dataMapper';
import { bluetoothService, BluetoothSensorData } from './services/bluetoothService';

// =========================
// 模块配置
// =========================
const MODULE_CONFIG = {
  'dry-eye': {
    title: '干眼症监测',
    icon: Eye,
    color: 'primary-dryeye',
    port: 3000,
    wsType: 'dryEye'
  },
  'sleep': {
    title: '睡眠质量检测',
    icon: Moon,
    color: 'primary-sleep',
    port: 3001,
    wsType: 'sleepQuality'
  },
  'fatigue': {
    title: '疲劳驾驶预警',
    icon: Car,
    color: 'primary-fatigue',
    port: 3002,
    wsType: 'fatigue'
  }
};

// =========================
// 端口映射
// =========================
const MODULE_PORT_MAP: Record<ModuleType, number> = {
  'dry-eye': 3000,
  'sleep': 3001,
  'fatigue': 3002
};

interface AppState {
  currentModule: 'gateway' | 'dry-eye' | 'sleep' | 'fatigue';
  isBluetoothModalOpen: boolean;
  isSettingsModalOpen: boolean;
  isHelpModalOpen: boolean;
  settings: {
    autoConnectBluetooth: boolean;
    realtimeDataPush: boolean;
    nightMode: boolean;
  };
}

export default function App() {
  const [state, setState] = useState<AppState>({
    currentModule: 'gateway',
    isBluetoothModalOpen: false,
    isSettingsModalOpen: false,
    isHelpModalOpen: false,
    settings: {
      autoConnectBluetooth: false,
      realtimeDataPush: true,
      nightMode: false
    }
  });

  // 当前模块数据
  const [moduleData, setModuleData] = useState<UnifiedMetricData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [isBluetoothConnected, setIsBluetoothConnected] = useState(false);

  // 节流控制引用
  const lastSendTimeRef = useRef<number>(0);

  // 当前模块（用于WebSocket）
  const currentModuleType: ModuleType = state.currentModule === 'gateway' ? 'fatigue' : state.currentModule as ModuleType;

  // WebSocket消息处理
  const handleMessage = useCallback((msg: any) => {
    if (!msg || !msg.type) {
      console.log('[App] 收到无效消息:', msg);
      return;
    }

    const moduleConfig = MODULE_CONFIG[currentModuleType];
    if (!moduleConfig) {
      console.log('[App] 未找到模块配置:', currentModuleType);
      return;
    }

    console.log(`[App] 收到消息 | 模块: ${currentModuleType} | 消息类型: ${msg.type} | 期望类型: ${moduleConfig.wsType}`);

    // 处理对应模块的数据
    if (msg.type === moduleConfig.wsType || msg.type === 'result') {
      console.log(`[App] 处理结果数据 | type=${msg.type}`);
      const mappedData = mapModuleData(currentModuleType, msg.data);
      if (mappedData) {
        setModuleData(mappedData);
      }
    } else if (msg.type === 'bluetooth_data') {
      // 只有当没有计算结果时，才使用原始蓝牙数据回显作为降级方案
      // 或者如果你的逻辑需要实时显示原始波形，可以保留，但这里为了稳定 UI 做节流
      console.log(`[App] 收到蓝牙回显，仅在无结果时更新`);
      const mappedData = mapModuleData(currentModuleType, msg.data);
      if (mappedData && (!moduleData || msg.type === 'bluetooth_data')) {
        // 如果是蓝牙数据，我们只在没有主数据时更新，或者你可以选择直接忽略它以减少抖动
        // setModuleData(mappedData); 
      }
    } else if (msg.type === 'hello') {
      console.log(`[App] 收到欢迎消息:`, msg.data);
    } else if (msg.type === 'stats') {
      console.log(`[App] 收到统计数据:`, msg.data);
    } else {
      console.log(`[App] 收到其他类型消息 | type=${msg.type}`);
    }
  }, [currentModuleType]);

  // 连接状态处理 - 仅记录日志，状态由useDynamicWebSocket同步
  const handleConnect = useCallback(() => {
    console.log(`[App] ${currentModuleType} 模块已连接`);
  }, [currentModuleType]);

  const handleDisconnect = useCallback(() => {
    console.log(`[App] ${currentModuleType} 模块已断开`);
  }, [currentModuleType]);

  const handleError = useCallback((error: Event) => {
    console.error(`[App] ${currentModuleType} 模块错误:`, error);
  }, [currentModuleType]);

  // 动态WebSocket Hook
  const {
    status,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    reconnect
  } = useDynamicWebSocket({
    module: currentModuleType,
    autoConnect: true,  // 自动连接
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  });

  // 同步状态
  useEffect(() => {
    setConnectionStatus(status);
  }, [status]);

  // 主题切换
  useEffect(() => {
    if (state.currentModule !== 'gateway') {
      document.documentElement.setAttribute('data-theme', state.currentModule);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [state.currentModule]);

  // 模块切换时重新连接
  useEffect(() => {
    if (state.currentModule !== 'gateway') {
      reconnect();
    } else {
      disconnect();
    }
  }, [state.currentModule]);

  // 切换模块
  const handleModuleSelect = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
    setState(prev => ({ ...prev, currentModule: module }));
    setModuleData(null);  // 清空旧数据
  };

  // 返回网关
  const handleBackToGateway = () => {
    setState(prev => ({ ...prev, currentModule: 'gateway' }));
    disconnect();
  };

  // 蓝牙模态框
  const toggleBluetoothModal = () => {
    setState(prev => ({ ...prev, isBluetoothModalOpen: !prev.isBluetoothModalOpen }));
  };

  // 设置模态框
  const toggleSettingsModal = () => {
    setState(prev => ({ ...prev, isSettingsModalOpen: !prev.isSettingsModalOpen }));
  };

  // 帮助模态框
  const toggleHelpModal = () => {
    setState(prev => ({ ...prev, isHelpModalOpen: !prev.isHelpModalOpen }));
  };

  // 处理设置变更
  const handleSettingChange = (key: keyof AppState['settings'], value: boolean) => {
    setState(prev => ({
      ...prev,
      settings: {
        ...prev.settings,
        [key]: value
      }
    }));
  };

  // 保存设置到 localStorage
  const saveSettings = () => {
    localStorage.setItem('health-monitor-settings', JSON.stringify(state.settings));
    console.log('[App] 设置已保存:', state.settings);
    toggleSettingsModal();
  };

  // 从 localStorage 加载设置
  useEffect(() => {
    const savedSettings = localStorage.getItem('health-monitor-settings');
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings);
        setState(prev => ({
          ...prev,
          settings: { ...prev.settings, ...parsedSettings }
        }));
        console.log('[App] 已加载保存的设置:', parsedSettings);
      } catch (e) {
        console.error('[App] 加载设置失败:', e);
      }
    }
  }, []);

  // 处理蓝牙数据接收 - 发送到后端（使用节流 Throttling）
  const handleBluetoothDataReceived = useCallback((data: any) => {
    console.log('[App] 蓝牙数据接收(原始):', data);
    
    const now = Date.now();
    // 节流处理：每 500ms 最多发送一次数据
    if (now - lastSendTimeRef.current < 500) {
      return;
    }

    lastSendTimeRef.current = now;
    console.log('[App] 节流后发送数据');

    const port = MODULE_PORT_MAP[currentModuleType] || 3002;
    const fullUrl = `http://localhost:${port}/api/bluetooth-data`;
    
    console.log(`[App] 发送数据到: ${fullUrl}`);

    const payload = {
      rawData: data.values || data.rawData?.values || [],
      timestamp: data.timestamp || Date.now(),
      signalQuality: data.signalQuality || data.rawData?.signalQuality || 100
    };
    
    console.log('[App] 发送数据内容:', payload);

    fetch(fullUrl, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }).then(response => {
      console.log('[App] 响应状态:', response.status);
      if (response.ok) {
        return response.json();
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    }).then(json => {
      console.log('[App] 数据发送成功，响应:', json);
    }).catch(err => {
      console.error('[App] 发送蓝牙数据失败:', err);
      console.error('[App] 错误详情:', err.message);
    });
  }, [currentModuleType]);

  // 注册蓝牙连接监听器
  useEffect(() => {
    const handleBluetoothConnection = (connected: boolean) => {
      console.log(`[App] 蓝牙连接状态变化: ${connected}`);
      setIsBluetoothConnected(connected);
    };

    bluetoothService.addConnectionListener(handleBluetoothConnection);
    
    return () => {
      bluetoothService.removeConnectionListener(handleBluetoothConnection);
    };
  }, []);

  // 在应用启动时注册蓝牙数据监听器
  useEffect(() => {
    const handleBluetoothData = (data: BluetoothSensorData) => {
      handleBluetoothDataReceived(data);
    };

    bluetoothService.addListener(handleBluetoothData);

    return () => {
      bluetoothService.removeListener(handleBluetoothData);
    };
  }, [handleBluetoothDataReceived]);

  // 渲染网关页面
  if (state.currentModule === 'gateway') {
    return <Gateway onSelectModule={handleModuleSelect} />;
  }

  // 渲染模块页面
  const currentModuleConfig = MODULE_CONFIG[currentModuleType];
  const Icon = currentModuleConfig.icon;

  // 根据模块获取头部背景色
  const getHeaderBg = () => {
    if (currentModuleType === 'dry-eye') return 'bg-[#122b25]/95';
    if (currentModuleType === 'sleep') return 'bg-[#1a1135]/95';
    return 'bg-[#2b1810]/95';
  };

  return (
    <div className="min-h-screen text-white">
      {/* 顶部状态栏 - 优化为更加深邃的一体化设计 */}
      <header className={`sticky top-0 z-50 backdrop-blur-xl border-b border-white/5 ${getHeaderBg()}`}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button
              onClick={handleBackToGateway}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5"
            >
              <Home size={18} className="text-white/70" />
            </button>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-white/5 text-white border border-white/10 shadow-lg`}>
                <Icon size={20} className={currentModuleType === 'sleep' ? 'text-purple-400' : currentModuleType === 'fatigue' ? 'text-orange-400' : 'text-emerald-400'} />
              </div>
              <h1 className="text-lg font-bold tracking-tight text-white/90">{currentModuleConfig.title}</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* 连接状态指示 - 严格按照要求显示颜色 */}
            <div className="flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-full border border-white/5">
              <div className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
                (connectionStatus === 'connected' && isBluetoothConnected) ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' :
                (connectionStatus === 'error') ? 'bg-red-500 shadow-[0_0_10px_#ef4444]' :
                'bg-yellow-500 animate-pulse shadow-[0_0_10px_#eab308]'
              }`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">
                {(connectionStatus === 'connected' && isBluetoothConnected) ? 'Connected' : 
                 (connectionStatus === 'error') ? 'Error' : 'Waiting'}
              </span>
            </div>

            <div className="h-8 w-[1px] bg-white/10 mx-2" />

            <button
              onClick={toggleBluetoothModal}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5 relative group"
            >
              <Bluetooth size={18} className="text-white/70 group-hover:text-white" />
              {connectionStatus === 'connected' && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-[#0A0514]"></span>
              )}
            </button>
            <button
              onClick={toggleSettingsModal}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5 group"
            >
              <Settings size={18} className="text-white/70 group-hover:text-white" />
            </button>
            <button
              onClick={toggleHelpModal}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-all border border-white/5 group"
            >
              <HelpCircle size={18} className="text-white/70 group-hover:text-white" />
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区域 */}
      <main className="w-full">
        <UnifiedBentoDashboard
          module={currentModuleType}
          data={moduleData}
          connectionStatus={
            (connectionStatus === 'connected' && isBluetoothConnected) 
              ? 'connected' 
              : (connectionStatus === 'error' ? 'error' : 'connecting')
          }
        />
      </main>

      {/* 蓝牙连接模态框 */}
      {state.isBluetoothModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="w-full max-w-md mx-4 relative">
            <button
              onClick={toggleBluetoothModal}
              className="absolute top-2 right-2 z-50 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              ×
            </button>
            <BluetoothControl onDataReceived={handleBluetoothDataReceived} />
          </div>
        </div>
      )}

 {/* 系统设置模态框 */}
      {state.isSettingsModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">系统设置</h2>
              <button onClick={toggleSettingsModal} className="p-2 rounded-full hover:bg-white/10">
                ×
              </button>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span>自动连接蓝牙</span>
                <input
                  type="checkbox"
                  className="w-5 h-5 rounded"
                  checked={state.settings.autoConnectBluetooth}
                  onChange={(e) => handleSettingChange('autoConnectBluetooth', e.target.checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <span>实时数据推送</span>
                <input
                  type="checkbox"
                  className="w-5 h-5 rounded"
                  checked={state.settings.realtimeDataPush}
                  onChange={(e) => handleSettingChange('realtimeDataPush', e.target.checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <span>夜间模式</span>
                <input
                  type="checkbox"
                  className="w-5 h-5 rounded"
                  checked={state.settings.nightMode}
                  onChange={(e) => handleSettingChange('nightMode', e.target.checked)}
                />
              </div>
              <div className="pt-4 border-t border-border-color">
                <button
                  onClick={saveSettings}
                  className="w-full py-2 bg-primary rounded-lg text-white hover:bg-primary/80 transition-colors"
                >
                  保存设置
                </button>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* 使用说明模态框 */}
      {state.isHelpModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-md p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">使用说明</h2>
              <button onClick={toggleHelpModal} className="p-2 rounded-full hover:bg-white/10">
                ×
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium mb-2">1. 设备连接</h3>
                <p className="text-sm opacity-80">点击顶部蓝牙图标，选择要连接的设备。</p>
              </div>
              <div>
                <h3 className="font-medium mb-2">2. 开始监测</h3>
                <p className="text-sm opacity-80">设备连接成功后，系统会自动开始监测。</p>
              </div>
              <div>
                <h3 className="font-medium mb-2">3. 查看数据</h3>
                <p className="text-sm opacity-80">仪表盘会实时显示监测数据和分析结果。</p>
              </div>
              <div>
                <h3 className="font-medium mb-2">4. 系统设置</h3>
                <p className="text-sm opacity-80">点击顶部设置图标，可调整系统参数。</p>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}