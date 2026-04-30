import React, { useState, useEffect } from "react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "./components/ui/tabs";
import { MonitoringDashboard } from "./components/MonitoringDashboard";
import { SleepChart } from "./components/SleepChart";
import { UserGuide } from "./components/UserGuide";
import { ControlPanel } from "./components/ControlPanel";
import { BluetoothControl } from "./components/BluetoothControl";
import { dataService, SleepData } from "./services/dataService";
import { bluetoothService, BluetoothSleepData } from "./services/bluetoothService";
// 导入WebSocket服务
import { websocketService, WSSleepData } from "./services/websocketService";
import {
  Monitor,
  BarChart3,
  BookOpen,
  Settings,
  Bluetooth,
} from "lucide-react";

// 图表数据接口
interface ChartData {
  time: string;
  sleepScore: number;
  movementIndex: number;
  sleepStability: number;
  sleepStageValue: number;
  sleepStageLabel: string;
  signalQuality: number;
  alertLevel: 'normal' | 'warning' | 'danger';
}

const stageLabels = ['深睡', '浅睡', 'REM', '清醒'];

const generateHistoryData = (): ChartData[] => {
  const data: ChartData[] = [];
  const now = new Date();
  for (let i = 24; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60 * 1000);
    const score = 70 + Math.floor(Math.random() * 25);
    const stageValue = Math.floor(Math.random() * 4);
    data.push({
      time: time.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      sleepScore: score,
      movementIndex: Math.floor(Math.random() * 10),
      sleepStability: 80 + Math.floor(Math.random() * 15),
      sleepStageValue: stageValue,
      sleepStageLabel: stageLabels[stageValue],
      signalQuality: 90 + Math.floor(Math.random() * 10),
      alertLevel: 'normal',
    });
  }
  return data;
};

export default function App() {
  const [currentData, setCurrentData] = useState<SleepData>(
    dataService.getCurrentData(),
  );
  const [historyData, setHistoryData] = useState<ChartData[]>(generateHistoryData());
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [useBluetoothData, setUseBluetoothData] = useState(false);
  const [useWebSocketData, setUseWebSocketData] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [monitoringStartTime, setMonitoringStartTime] = useState<Date | null>(null);

  const formatDuration = (startTime: Date | null) => {
    if (!startTime) return "0小时0分钟";
    const diffMs = new Date().getTime() - startTime.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${diffHours}小时${diffMinutes}分钟`;
  };

  // 实时数据更新
  useEffect(() => {
    // 处理模拟数据更新
    const handleDataUpdate = (data: SleepData) => {
      const updatedData = {
        ...data,
        monitoringDuration: monitoringStartTime ? formatDuration(monitoringStartTime) : data.monitoringDuration,
      };
      setCurrentData(updatedData);
      
      const newHistoryItem: ChartData = {
        time: updatedData.lastUpdate,
        sleepScore: updatedData.sleepScore,
        movementIndex: updatedData.movementIndex ?? updatedData.movementRate,
        sleepStability: updatedData.sleepStability ?? updatedData.eyelidStatus.eyeClosureRatio,
        sleepStageValue: updatedData.sleepStage === 'deep' ? 0 : updatedData.sleepStage === 'light' ? 1 : updatedData.sleepStage === 'rem' ? 2 : 3,
        sleepStageLabel: updatedData.sleepStage === 'deep' ? '深睡' : updatedData.sleepStage === 'light' ? '浅睡' : updatedData.sleepStage === 'rem' ? 'REM' : '清醒',
        signalQuality: updatedData.sensorStatus.signalQuality,
        alertLevel: updatedData.alertLevel,
      };
      
      setHistoryData(prev => [...prev.slice(-24), newHistoryItem]);
    };

    // 处理WebSocket数据
    const handleWebSocketData = (wsMsg: WSSleepData) => {
      if (wsMsg.type === 'sleepQuality') {
        const data = wsMsg.data;
        const normalizeEyeState = (state: string | undefined): SleepData['eyeState'] => {
          if (typeof state !== "string") return "正常眨眼";
          const s = state.trim();
          if (!s) return "正常眨眼";
          if (s === "睁眼" || s === "闭眼" || s === "频繁眨眼" || s === "慢速眨眼" || s === "正常眨眼" || s === "快速眼动") return s;
          const normalized = s.toLowerCase().replace(/\s+/g, "_");
          if (normalized.includes("open")) return "睁眼";
          if (normalized.includes("close")) return "闭眼";
          if (normalized.includes("fast") || normalized.includes("frequent")) return "频繁眨眼";
          if (normalized.includes("slow")) return "慢速眨眼";
          if (normalized.includes("rem") || normalized.includes("rapid") || normalized.includes("fast")) return "快速眼动";
          return "正常眨眼";
        };

        // 构建基础睡眠数据
        let sleepData: SleepData = {
          eyeStatus: data.eyeStatus || 'closed',
          sleepScore: data.qualityScore || data.sleepScore || 0,
          movementRate: data.movementIndex || 0,
          eyelidStatus: {
            leftEye: data.leftEyeStatus || 'closed',
            rightEye: data.rightEyeStatus || 'closed',
            blinkDuration: data.blinkDuration || 0,
            eyeClosureRatio: data.eyeClosureRatio || 0,
          },
          sensorStatus: {
            connected: true,
            signalQuality: data.signalQuality || 100,
            batteryLevel: data.batteryLevel || 100,
          },
          alertLevel: (data.qualityScore || data.sleepScore) >= 60 ? "normal" : "warning",
          monitoringDuration: formatDuration(monitoringStartTime),
          lastUpdate: new Date().toLocaleTimeString("zh-CN"),
          sleepStage: data.currentStageName || data.sleepStage,
          movementIndex: data.movementIndex,
          sleepStability: data.sleepStability || data.eyeClosureRatio,
          eyeState: normalizeEyeState(data.eyeState),
          remDensity: data.rem_density,
          semCount: data.sem_count,
          remEnergy: data.rem_energy,
          semEnergy: data.sem_energy,
          remSemRatio: data.rem_sem_ratio,
          signalStd: data.signal_std,
          totalMinutes: data.total_minutes,
          tstMinutes: data.tst_minutes,
          sleepEfficiency: data.sleep_efficiency,
          currentStageName: data.sleep_stage
        };

        // 根据睡眠阶段和体动指数调整眼部状态，确保逻辑一致性
        const movementIndex = sleepData.movementIndex || sleepData.movementRate;
        if (sleepData.sleepStage === 'awake') {
          // 清醒状态：应该是睁眼或频繁眨眼
          if (sleepData.eyeState === '闭眼') {
            sleepData.eyeState = movementIndex > 20 ? '频繁眨眼' : '正常眨眼';
          }
        } else if (sleepData.sleepStage === 'light') {
          // 浅睡状态：应该是慢速眨眼或闭眼
          if (sleepData.eyeState === '睁眼' || sleepData.eyeState === '频繁眨眼' || sleepData.eyeState === '快速眼动') {
            sleepData.eyeState = movementIndex > 15 ? '慢速眨眼' : '闭眼';
          }
        } else if (sleepData.sleepStage === 'deep') {
          // 深睡状态：应该是闭眼
          if (sleepData.eyeState !== '闭眼') {
            sleepData.eyeState = '闭眼';
          }
        } else if (sleepData.sleepStage === 'rem') {
          // REM状态：应该是快速眼动
          if (sleepData.eyeState !== '快速眼动') {
            sleepData.eyeState = '快速眼动';
          }
        }
        setCurrentData(sleepData);

        const newHistoryItem: ChartData = {
          time: sleepData.lastUpdate,
          sleepScore: sleepData.sleepScore,
          movementIndex: sleepData.movementIndex ?? sleepData.movementRate,
          sleepStability: sleepData.sleepStability ?? sleepData.eyelidStatus.eyeClosureRatio,
          sleepStageValue: sleepData.sleepStage === 'deep' ? 0 : sleepData.sleepStage === 'light' ? 1 : sleepData.sleepStage === 'rem' ? 2 : 3,
          sleepStageLabel: sleepData.sleepStage === 'deep' ? '深睡' : sleepData.sleepStage === 'light' ? '浅睡' : sleepData.sleepStage === 'rem' ? 'REM' : '清醒',
          signalQuality: sleepData.sensorStatus.signalQuality,
          alertLevel: sleepData.alertLevel,
        };
        setHistoryData(prev => [...prev.slice(-24), newHistoryItem]);
      }
    };

    // 处理蓝牙数据
    const handleBluetoothData = (data: BluetoothSleepData) => {
      setUseBluetoothData(true);
      console.log('蓝牙数据已接收，时间戳:', data.timestamp);
    };

    // 控制逻辑
    if (useWebSocketData) {
      websocketService.connect();
      websocketService.addListener(handleWebSocketData);
      dataService.stopRealTimeData();
      bluetoothService.removeListener(handleBluetoothData);
    } else if (isMonitoring && !useBluetoothData) {
      dataService.addListener(handleDataUpdate);
      dataService.startRealTimeData(2000);
      websocketService.disconnect();
      websocketService.removeListener(handleWebSocketData);
    } else if (useBluetoothData) {
      bluetoothService.addListener(handleBluetoothData);
      dataService.stopRealTimeData();
      websocketService.disconnect();
      websocketService.removeListener(handleWebSocketData);
    } else {
      dataService.stopRealTimeData();
      websocketService.disconnect();
      dataService.removeListener(handleDataUpdate);
      bluetoothService.removeListener(handleBluetoothData);
      websocketService.removeListener(handleWebSocketData);
    }

    const checkWsStatus = setInterval(() => {
      setWsConnected(websocketService.isConnected());
    }, 1000);

    return () => {
      dataService.removeListener(handleDataUpdate);
      bluetoothService.removeListener(handleBluetoothData);
      websocketService.removeListener(handleWebSocketData);
      clearInterval(checkWsStatus);
    };
  }, [isMonitoring, useBluetoothData, useWebSocketData, monitoringStartTime]);

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
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl mb-2">睡眠质量检测系统</h1>
          <p className="text-muted-foreground">
            实时监测眼部状态与体动，评估睡眠阶段与质量
          </p>
        </div>

        {/* 数据来源控制区 */}
        <div className="mb-6 flex flex-wrap gap-4">
          <button
            onClick={handleToggleMonitoring}
            className={`px-4 py-2 rounded-md ${
              isMonitoring 
                ? "bg-red-500 text-white" 
                : "bg-green-500 text-white"
            }`}
          >
            {isMonitoring ? "停止模拟数据" : "启动模拟数据"}
          </button>
          <button
            onClick={handleToggleWebSocket}
            className={`px-4 py-2 rounded-md ${
              useWebSocketData 
                ? "bg-blue-600 text-white" 
                : "bg-blue-500 text-white"
            }`}
          >
            {useWebSocketData 
              ? `停止WebSocket (${wsConnected ? "已连接" : "连接中"})` 
              : "启动WebSocket连接"}
          </button>
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
            <MonitoringDashboard data={currentData} />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <SleepChart data={historyData} />
          </TabsContent>

          <TabsContent value="bluetooth" className="space-y-6">
            <BluetoothControl onDataReceived={(data) => {
              setCurrentData(data);
              setUseBluetoothData(true);
              setUseWebSocketData(false);
              setIsMonitoring(false);
            }} />
          </TabsContent>

          <TabsContent value="settings">
            <ControlPanel
              isMonitoring={isMonitoring}
              onToggleMonitoring={handleToggleMonitoring}
            />
          </TabsContent>

          <TabsContent value="guide">
            <UserGuide />
          </TabsContent>
        </Tabs>

        {/* 状态栏 */}
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4">
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