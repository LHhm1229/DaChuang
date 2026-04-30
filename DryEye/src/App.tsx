import React, { useState, useEffect } from "react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "./components/ui/tabs";
import { MonitoringDashboard } from "./components/MonitoringDashboard";
import { DryEyeChart } from "./components/DryEyeChart";
import { UserGuide } from "./components/UserGuide";
import { ControlPanel } from "./components/ControlPanel";
import { BluetoothControl } from "./components/BluetoothControl";
import { dataService, DryEyeData } from "./services/dataService";
import { bluetoothService, BluetoothDryEyeData } from "./services/bluetoothService";
// 导入WebSocket服务
import { websocketService, WSDryEyeData } from "./services/websocketService";
import { normalizeEyeState } from "./components/ui/eye-utils";
import {
  Monitor,
  BarChart3,
  BookOpen,
  Settings,
  Bluetooth,
  Activity,
  Wifi,
  Zap,
} from "lucide-react";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";

// 图表数据接口
interface ChartData {
  time: string;
  eyeHealthScore: number;
  blinkRate: number;
  eyeClosureRatio: number;
  signalQuality: number;
  alertLevel: number | string;
}

// 生成历史数据
const generateHistoryData = (): ChartData[] => {
  const data: ChartData[] = [];
  for (let i = 24; i >= 0; i--) {
    const time = new Date();
    time.setMinutes(time.getMinutes() - i * 15);
    const eyeHealthScore = Math.floor(Math.random() * 30) + 65;
    data.push({
      time: time.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      eyeHealthScore,
      blinkRate: Math.floor(Math.random() * 12) + (100 - eyeHealthScore) * 0.2,
      eyeClosureRatio: Math.max(30, Math.min(100, eyeHealthScore + Math.floor(Math.random() * 15 - 7))),
      signalQuality: Math.floor(Math.random() * 30) + 70,
      alertLevel: eyeHealthScore >= 60 ? "normal" : eyeHealthScore >= 40 ? "warning" : "danger",
    });
  }
  return data;
};

export default function App() {
  const [currentData, setCurrentData] = useState<DryEyeData>(
    dataService.getCurrentData(),
  );
  const [historyData, setHistoryData] = useState<ChartData[]>(generateHistoryData());
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [useBluetoothData, setUseBluetoothData] = useState(false);
  // 新增：WebSocket相关状态
  const [useWebSocketData, setUseWebSocketData] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [monitoringStartTime, setMonitoringStartTime] = useState<Date | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(() => {
    const saved = localStorage.getItem("dry-eye-monitor-refresh-interval");
    return saved ? parseInt(saved) : 2000;
  });

  const formatDuration = (startTime: Date | null) => {
    if (!startTime) return "0小时0分钟";
    const diffMs = new Date().getTime() - startTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${diffHours}小时${diffMinutes}分钟`;
  };

  // 实时数据更新
  useEffect(() => {
    // 处理WebSocket数据
    const handleWebSocketData = (data: WSDryEyeData) => {
      const updatedData: DryEyeData = {
        eyeStatus: data.eyeState === 'closed' ? 'closed' : 'open',
        eyeHealthScore: 100 - data.dryEyeRiskScore,
        dryEyeRiskScore: data.dryEyeRiskScore,
        dryEyeRiskLevel: data.dryEyeRiskLevel,
        blinkRate: data.blinkRate,
        avgBlinkDuration: data.avgBlinkDuration,
        incompleteBlinkRatio: data.incompleteBlinkRatio,
        longBlinkRatio: data.longBlinkRatio,
        totalBlinks: data.totalBlinks,
        incompleteBlinks: data.incompleteBlinks,
        longBlinks: data.longBlinks,
        eyelidStatus: {
          leftEye: data.eyeState === 'closed' ? 'closed' : 'open',
          rightEye: data.eyeState === 'closed' ? 'closed' : 'open',
          blinkDuration: data.avgBlinkDuration,
          eyeClosureRatio: data.eyeClosureRatio,
        },
        sensorStatus: {
          ...data.sensorStatus,
          connected: true,
          batteryLevel: 100,
        },
        alertLevel: data.dryEyeRiskScore < 30 ? 'normal' : data.dryEyeRiskScore < 60 ? 'warning' : 'danger',
        monitoringTime: monitoringStartTime ? formatDuration(monitoringStartTime) : data.lastUpdate,
        lastUpdate: data.lastUpdate,
        eyeState: normalizeEyeState(data.eyeState) as any,
      };
      setCurrentData(updatedData);
      setWsConnected(true);

      const newHistoryData = {
        time: data.lastUpdate,
        eyeHealthScore: updatedData.eyeHealthScore,
        blinkRate: data.blinkRate,
        eyeClosureRatio: data.eyeClosureRatio,
        signalQuality: data.sensorStatus.signalQuality,
        alertLevel: updatedData.alertLevel === 'normal' ? 0 : updatedData.alertLevel === 'warning' ? 1 : 2,
      };

      setHistoryData(prev => {
        const updated = [...prev, newHistoryData];
        return updated.slice(-25);
      });
    };

    // 处理模拟数据更新
    const handleDataUpdate = (data: DryEyeData) => {
      const updatedData = {
        ...data,
        monitoringTime: monitoringStartTime ? formatDuration(monitoringStartTime) : data.monitoringTime,
      };
      setCurrentData(updatedData);
      
      const newHistoryData = {
        time: data.lastUpdate,
        eyeHealthScore: data.eyeHealthScore,
        blinkRate: data.blinkRate,
        eyeClosureRatio: data.eyelidStatus.eyeClosureRatio,
        signalQuality: data.sensorStatus.signalQuality,
        alertLevel: data.alertLevel === 'normal' ? 0 : data.alertLevel === 'warning' ? 1 : 2,
      };
      
      setHistoryData(prev => {
        const updated = [...prev, newHistoryData];
        return updated.slice(-25);
      });
    };

    // 处理蓝牙数据
    const handleBluetoothData = (data: BluetoothDryEyeData) => {
      setUseBluetoothData(true);
      
      // 将蓝牙原始数据映射到仪表盘所需的数据格式
      // 注意：这里是一个简化的映射，实际应用中应该由算法处理
      const updatedData: DryEyeData = {
        eyeStatus: data.rawData.values[0] > 0.5 ? 'open' : 'closed', // 假设第一个值与眼部状态相关
        eyeHealthScore: Math.round(70 + Math.random() * 20), // 模拟评分
        blinkRate: Math.round(10 + Math.random() * 10), // 模拟频率
        eyelidStatus: {
          leftEye: data.rawData.values[0] > 0.5 ? 'open' : 'closed',
          rightEye: data.rawData.values[1] > 0.5 ? 'open' : 'closed',
          blinkDuration: 200,
          eyeClosureRatio: 85,
        },
        sensorStatus: {
          connected: true,
          signalQuality: data.rawData.signalQuality,
          batteryLevel: 100,
        },
        alertLevel: 'normal',
        monitoringTime: monitoringStartTime ? formatDuration(monitoringStartTime) : '0小时0分钟',
        lastUpdate: new Date().toLocaleTimeString("zh-CN"),
        eyeState: data.rawData.values[0] > 0.5 ? '睁眼' : '闭眼',
      };
      
      setCurrentData(updatedData);
      
      const newHistoryData = {
        time: updatedData.lastUpdate,
        eyeHealthScore: updatedData.eyeHealthScore,
        blinkRate: updatedData.blinkRate,
        eyeClosureRatio: updatedData.eyelidStatus.eyeClosureRatio,
        signalQuality: updatedData.sensorStatus.signalQuality,
        alertLevel: 0,
      };
      
      setHistoryData(prev => {
        const updated = [...prev, newHistoryData];
        return updated.slice(-25);
      });
    };

    // WebSocket连接逻辑
    if (useWebSocketData) {
      // 连接WebSocket并添加监听器
      websocketService.connect();
      websocketService.addListener(handleWebSocketData);
      
      // 停止其他数据服务
      dataService.stopRealTimeData();
      bluetoothService.removeListener(handleBluetoothData);
    } else if (isMonitoring && !useBluetoothData) {
      // 使用模拟数据
      dataService.addListener(handleDataUpdate);
      dataService.startRealTimeData(refreshInterval);
      
      // 断开WebSocket
      websocketService.disconnect();
      websocketService.removeListener(handleWebSocketData);
    } else if (useBluetoothData) {
      // 使用蓝牙数据
      bluetoothService.addListener(handleBluetoothData);
      dataService.stopRealTimeData();
      websocketService.disconnect();
      websocketService.removeListener(handleWebSocketData);
    } else {
      // 全部停止
      dataService.stopRealTimeData();
      websocketService.disconnect();
      dataService.removeListener(handleDataUpdate);
      bluetoothService.removeListener(handleBluetoothData);
      websocketService.removeListener(handleWebSocketData);
    }

    // 监听WebSocket连接状态
    const checkWsStatus = setInterval(() => {
      setWsConnected(websocketService.isConnected());
    }, 1000);

    return () => {
      // 清理所有监听器和连接
      dataService.removeListener(handleDataUpdate);
      bluetoothService.removeListener(handleBluetoothData);
      websocketService.removeListener(handleWebSocketData);
      websocketService.disconnect();
      clearInterval(checkWsStatus);
    };
  }, [isMonitoring, useBluetoothData, useWebSocketData, monitoringStartTime, refreshInterval]);

  const handleToggleMonitoring = () => {
    setIsMonitoring(prev => {
      const next = !prev;
      if (next) {
        setMonitoringStartTime(new Date());
      }
      return next;
    });
    // 切换模拟数据时关闭WebSocket和蓝牙
    setUseWebSocketData(false);
    setUseBluetoothData(false);
  };

  // 切换WebSocket数据
  const handleToggleWebSocket = () => {
    setUseWebSocketData(!useWebSocketData);
    // 切换WebSocket时关闭模拟和蓝牙
    setIsMonitoring(false);
    setUseBluetoothData(false);
    if (!useWebSocketData) {
        setMonitoringStartTime(new Date());
    }
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <div className="container mx-auto p-6">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl mb-2 font-bold">干眼症监测系统</h1>
          <p className="text-muted-foreground">
            实时监测眼部状态，通过眨眼频率和眼部稳定性评估干眼风险
          </p>
        </div>

        {/* 数据来源控制区 */}
        <div className="mb-8 p-4 bg-muted/30 rounded-xl border border-border/50 flex flex-wrap items-center gap-6">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">数据源切换</span>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleToggleMonitoring}
                variant={isMonitoring ? "default" : "outline"}
                size="sm"
                className={`flex items-center gap-2 ${isMonitoring ? "bg-green-600 hover:bg-green-700" : ""}`}
              >
                <Activity className={`h-4 w-4 ${isMonitoring ? "animate-pulse" : ""}`} />
                模拟数据
              </Button>
              <Button
                onClick={handleToggleWebSocket}
                variant={useWebSocketData ? "default" : "outline"}
                size="sm"
                className={`flex items-center gap-2 ${useWebSocketData ? "bg-blue-600 hover:bg-blue-700" : ""}`}
              >
                <Wifi className={`h-4 w-4 ${wsConnected ? "text-white" : ""}`} />
                WebSocket
              </Button>
              <Button
                onClick={() => setActiveTab("bluetooth")}
                variant={useBluetoothData ? "default" : "outline"}
                size="sm"
                className={`flex items-center gap-2 ${useBluetoothData ? "bg-purple-600 hover:bg-purple-700" : ""}`}
              >
                <Bluetooth className="h-4 w-4" />
                蓝牙连接
              </Button>
            </div>
          </div>

          <div className="h-10 w-[1px] bg-border/50 hidden md:block"></div>

          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">当前工作模式</span>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={`h-6 ${
                isMonitoring ? "border-green-200 text-green-700 bg-green-50" :
                useWebSocketData ? "border-blue-200 text-blue-700 bg-blue-50" :
                useBluetoothData ? "border-purple-200 text-purple-700 bg-purple-50" :
                "bg-secondary"
              }`}>
                {isMonitoring ? "模拟模式" : useWebSocketData ? "WS 实时模式" : useBluetoothData ? "蓝牙模式" : "待机中"}
              </Badge>
              {useWebSocketData && (
                <Badge variant={wsConnected ? "default" : "destructive"} className="h-6">
                  {wsConnected ? "WS 已连接" : "WS 已断开"}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* 主要内容区域 */}
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full"
        >
          <TabsList className="flex w-full justify-center mb-8 flex-wrap">
            <TabsTrigger
              value="dashboard"
              className="flex items-center gap-2 px-3 py-2 min-w-fit"
            >
              <Monitor className="h-4 w-4" />
              实时监控
            </TabsTrigger>
            <TabsTrigger
              value="analytics"
              className="flex items-center gap-2 px-3 py-2 min-w-fit"
            >
              <BarChart3 className="h-4 w-4" />
              数据分析
            </TabsTrigger>
            <TabsTrigger
              value="bluetooth"
              className="flex items-center gap-2 px-3 py-2 min-w-fit"
            >
              <Bluetooth className="h-4 w-4" />
              蓝牙连接
            </TabsTrigger>
            <TabsTrigger
              value="settings"
              className="flex items-center gap-2 px-3 py-2 min-w-fit"
            >
              <Settings className="h-4 w-4" />
              系统设置
            </TabsTrigger>
            <TabsTrigger
              value="guide"
              className="flex items-center gap-2 px-3 py-2 min-w-fit"
            >
              <BookOpen className="h-4 w-4" />
              使用说明
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <MonitoringDashboard data={{
              ...currentData,
              refreshInterval: useWebSocketData ? undefined : refreshInterval
            }} />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <DryEyeChart data={historyData} />
          </TabsContent>

          <TabsContent value="bluetooth" className="space-y-6">
            <BluetoothControl onDataReceived={(data: BluetoothDryEyeData) => {
              // 处理蓝牙接收到的数据并更新 currentData
              setUseBluetoothData(true);
              setUseWebSocketData(false);
              setIsMonitoring(false);
            }} />
          </TabsContent>

          <TabsContent value="settings">
            <ControlPanel
              isMonitoring={isMonitoring}
              onToggleMonitoring={handleToggleMonitoring}
              refreshInterval={refreshInterval}
              onRefreshIntervalChange={(val) => {
                setRefreshInterval(val);
                localStorage.setItem("dry-eye-monitor-refresh-interval", val.toString());
              }}
            />
          </TabsContent>

          <TabsContent value="guide">
            <UserGuide />
          </TabsContent>
        </Tabs>

        {/* 状态栏 */}
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 z-50">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
              <span>
                系统状态: {
                  useWebSocketData ? (wsConnected ? "WebSocket数据接收中" : "WebSocket连接中") : 
                  useBluetoothData ? "蓝牙数据接收中" : 
                  (isMonitoring ? "模拟数据监控中" : "待机")
                }
              </span>
              <span>•</span>
              <span>数据来源: {
                useWebSocketData ? "WebSocket后端" : 
                useBluetoothData ? "单片机蓝牙" : 
                "模拟数据"
              }</span>
              <span>•</span>
              <span>最后更新: {currentData.lastUpdate}</span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  useWebSocketData ? (wsConnected ? "bg-blue-500" : "bg-yellow-500") :
                  useBluetoothData ? "bg-blue-500" : 
                  (isMonitoring ? "bg-green-500" : "bg-gray-400")
                }`}
              ></div>
              <span className="text-sm text-muted-foreground">
                {
                  useWebSocketData ? (wsConnected ? "WS已连接" : "WS连接中") :
                  useBluetoothData ? "蓝牙连接" : 
                  (isMonitoring ? "正在监控" : "已停止")
                }
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
