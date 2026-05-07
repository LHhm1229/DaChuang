/**
 * App.tsx - 健康监测系统主入口
 * 基于统一WebSocket通信层 + 数据映射层
 */

import { useState, useEffect, useCallback } from 'react';
import { Gateway } from './components/Gateway';
import { UnifiedBentoDashboard } from './components/UnifiedBentoDashboard';
import { BluetoothControl } from './components/BluetoothControl';
import { GlassCard } from './components/ui/GlassCard';
import { Eye, Moon, Car, Home, Settings, HelpCircle, Bluetooth } from 'lucide-react';
import { useDynamicWebSocket, ModuleType } from './hooks/useDynamicWebSocket';
import { mapModuleData, UnifiedMetricData } from './services/dataMapper';

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
}

export default function App() {
  const [state, setState] = useState<AppState>({
    currentModule: 'gateway',
    isBluetoothModalOpen: false,
    isSettingsModalOpen: false,
    isHelpModalOpen: false
  });

  // 当前模块数据
  const [moduleData, setModuleData] = useState<UnifiedMetricData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');

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
    if (msg.type === moduleConfig.wsType || msg.type === 'result' || msg.type === 'bluetooth_data') {
      console.log(`[App] 处理数据 | type=${msg.type} | data keys:`, msg.data ? Object.keys(msg.data) : '无数据');
      const mappedData = mapModuleData(currentModuleType, msg.data);
      if (mappedData) {
        console.log(`[App] 映射后数据 | mainValue=${mappedData.mainValue} | status=${mappedData.status.connected}`);
        setModuleData(mappedData);
      } else {
        console.log('[App] 数据映射返回null');
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

  // 处理蓝牙数据接收 - 发送到后端
  const handleBluetoothDataReceived = useCallback((data: any) => {
    console.log('[App] 蓝牙数据接收:', data);

    const apiPaths: Record<ModuleType, string> = {
      'dry-eye': '/api/bluetooth-data',
      'sleep': '/api/bluetooth-data-sleep',
      'fatigue': '/api/bluetooth-data-fatigue'
    };
    
    const url = apiPaths[currentModuleType] || '/api/bluetooth-data';
    console.log(`[App] 发送数据到: ${url}`);

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rawData: data.values || data.rawData?.values || [],
        timestamp: data.timestamp || Date.now(),
        signalQuality: data.signalQuality || data.rawData?.signalQuality || 100
      })
    }).then(response => {
      if (response.ok) {
        console.log('[App] 数据发送成功:', response.status);
      } else {
        console.error('[App] 数据发送失败:', response.status, response.statusText);
      }
    }).catch(err => console.error('[App] 发送蓝牙数据失败:', err));
  }, [currentModuleType]);

  // 渲染网关页面
  if (state.currentModule === 'gateway') {
    return <Gateway onSelectModule={handleModuleSelect} />;
  }

  // 渲染模块页面
  const currentModuleConfig = MODULE_CONFIG[currentModuleType];
  const Icon = currentModuleConfig.icon;

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部状态栏 */}
      <header className="glass-card sticky top-0 z-50 backdrop-blur-lg border-b border-border-color">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBackToGateway}
              className="p-2 rounded-full hover:bg-white/10 transition-colors"
            >
              <Home size={20} />
            </button>
            <div className="flex items-center gap-2">
              <div className={`p-2 rounded-full bg-${currentModuleConfig.color} text-white`}>
                <Icon size={20} />
              </div>
              <h1 className="text-xl font-bold">{currentModuleConfig.title}</h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* 连接状态指示 */}
            <div className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-green-500' :
              connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
              connectionStatus === 'error' ? 'bg-red-500' : 'bg-gray-500'
            }`} />

            <button
              onClick={toggleBluetoothModal}
              className="p-2 rounded-full hover:bg-white/10 transition-colors relative"
            >
              <Bluetooth size={20} />
              {connectionStatus === 'connected' && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full"></span>
              )}
            </button>
            <button
              onClick={toggleSettingsModal}
              className="p-2 rounded-full hover:bg-white/10 transition-colors"
            >
              <Settings size={20} />
            </button>
            <button
              onClick={toggleHelpModal}
              className="p-2 rounded-full hover:bg-white/10 transition-colors"
            >
              <HelpCircle size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区域 - 传递实时数据 */}
      <main className="container mx-auto px-4 py-8">
        <UnifiedBentoDashboard
          module={currentModuleType}
          data={moduleData}
          connectionStatus={connectionStatus}
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
                <input type="checkbox" className="w-5 h-5 rounded" />
              </div>
              <div className="flex items-center justify-between">
                <span>实时数据推送</span>
                <input type="checkbox" className="w-5 h-5 rounded" defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <span>夜间模式</span>
                <input type="checkbox" className="w-5 h-5 rounded" />
              </div>
              <div className="pt-4 border-t border-border-color">
                <button className="w-full py-2 bg-primary rounded-lg text-white">
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