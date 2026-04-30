import { useState, useEffect } from 'react';
import { Gateway } from './components/Gateway';
import { UnifiedBentoDashboard } from './components/UnifiedBentoDashboard';
import { BluetoothControl } from './components/BluetoothControl';
import { GlassCard } from './components/ui/GlassCard';
import { Eye, Moon, Car, Home, Settings, HelpCircle, Bluetooth } from 'lucide-react';
import { BluetoothSensorData } from './services/bluetoothService';

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

  // 切换主题
  useEffect(() => {
    if (state.currentModule !== 'gateway') {
      document.documentElement.setAttribute('data-theme', state.currentModule);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [state.currentModule]);

  const handleModuleSelect = (module: 'dry-eye' | 'sleep' | 'fatigue') => {
    setState(prev => ({ ...prev, currentModule: module }));
  };

  const handleBackToGateway = () => {
    setState(prev => ({ ...prev, currentModule: 'gateway' }));
  };

  const toggleBluetoothModal = () => {
    setState(prev => ({ ...prev, isBluetoothModalOpen: !prev.isBluetoothModalOpen }));
  };

  const toggleSettingsModal = () => {
    setState(prev => ({ ...prev, isSettingsModalOpen: !prev.isSettingsModalOpen }));
  };

  const toggleHelpModal = () => {
    setState(prev => ({ ...prev, isHelpModalOpen: !prev.isHelpModalOpen }));
  };

  const handleBluetoothDataReceived = (data: BluetoothSensorData) => {
    console.log('蓝牙数据接收:', data);
    fetch(`/api/${state.currentModule}/bluetooth-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rawData: data.values,
        timestamp: data.timestamp,
        signalQuality: data.signalQuality
      })
    }).catch(err => console.error('发送蓝牙数据失败:', err));
  };

  // 模块配置
  const moduleConfig = {
    'dry-eye': {
      title: '干眼症监测',
      icon: Eye,
      color: 'primary-dryeye'
    },
    'sleep': {
      title: '睡眠质量检测',
      icon: Moon,
      color: 'primary-sleep'
    },
    'fatigue': {
      title: '疲劳驾驶预警',
      icon: Car,
      color: 'primary-fatigue'
    }
  };

  // 渲染网关页面
  if (state.currentModule === 'gateway') {
    return <Gateway onSelectModule={handleModuleSelect} />;
  }

  // 渲染模块页面
  const currentModuleConfig = moduleConfig[state.currentModule as 'dry-eye' | 'sleep' | 'fatigue'];
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
            <button
              onClick={toggleBluetoothModal}
              className="p-2 rounded-full hover:bg-white/10 transition-colors relative"
            >
              <Bluetooth size={20} />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full"></span>
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

      {/* 主内容区域 */}
      <main className="container mx-auto px-4 py-8">
        <UnifiedBentoDashboard module={state.currentModule as 'dry-eye' | 'sleep' | 'fatigue'} />
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
                <input type="checkbox" className="w-5 h-5 rounded" checked />
              </div>
              <div className="flex items-center justify-between">
                <span>实时数据推送</span>
                <input type="checkbox" className="w-5 h-5 rounded" checked />
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
