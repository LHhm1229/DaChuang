import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "./components/ui/tabs";
import { MonitoringDashboard } from "./components/MonitoringDashboard";
import { FatigueChart } from "./components/FatigueChart";
import { UserGuide } from "./components/UserGuide";
import { ControlPanel } from "./components/ControlPanel";
import { BluetoothControl } from "./components/BluetoothControl";
import { dataService, FatigueData } from "./services/dataService";
import { bluetoothService, BluetoothFatigueData } from "./services/bluetoothService";
import { Monitor, BarChart3, BookOpen, Settings, Bluetooth } from "lucide-react";

// ==============================
// 图表数据接口
// ==============================
interface ChartData {
  time: string;
  fatigueScore: number;
  blinkRate: number;
  eyeMovementSpeed?: number;
  eyeMovement?: { speed: number };
  signalQuality: number;
  alertLevel: number | string;
}

// ==============================
// 生成历史数据（仅作为初始占位）
// ==============================
const generateHistoryData = (): ChartData[] => {
  const data: ChartData[] = [];
  for (let i = 24; i >= 0; i--) {
    const time = new Date();
    time.setMinutes(time.getMinutes() - i * 5);
    const fatigueScore = Math.floor(Math.random() * 80) + 10;
    data.push({
      time: time.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      fatigueScore,
      blinkRate: Math.floor(Math.random() * 20) + 15,
      eyeMovementSpeed: Math.floor(Math.random() * 8) + 3,
      signalQuality: Math.floor(Math.random() * 30) + 70,
      alertLevel: fatigueScore < 30 ? "normal" : fatigueScore < 70 ? "warning" : "danger",
    });
  }
  return data;
};

// ==============================
// WebSocket 消息类型
// ==============================
type WsMsg =
  | { type: "stats"; data: any }
  | { type: "bluetooth_data"; data: any }
  | { type: "fatigue"; data: any }
  | { type: "hello"; data?: any }
  | { type: "pong"; data?: any }
  | { type: string; data?: any };

// ==============================
// 把后端 fatigue_output 映射为前端 FatigueData（缺啥补啥）
// ==============================
function mapFatigueToFatigueData(fatigueOutput: any, fallback?: Partial<FatigueData>): FatigueData {
  // 你后端 run_fatigue_pipeline 的输出大概率含这些字段
  const fatigueScore = Number(fatigueOutput?.fatigueScore ?? fallback?.fatigueScore ?? 0);
  const blinkRate = Number(fatigueOutput?.blinkRate ?? fallback?.blinkRate ?? 0);

  const eyelidStatus = {
    ...(fallback?.eyelidStatus as any),
    ...(fatigueOutput?.eyelidStatus ?? {}),
  };

  const sensorStatus = {
    ...(fallback?.sensorStatus as any),
    signalQuality: Number(
      fatigueOutput?.sensorStatus?.signalQuality ??
        fallback?.sensorStatus?.signalQuality ??
        fatigueOutput?.signalQuality ?? // 有些实现把 signalQuality 放顶层
        0
    ),
    batteryLevel: Number(
        fatigueOutput?.sensorStatus?.batteryLevel ??
        fatigueOutput?.batteryLevel ??
        fallback?.sensorStatus?.batteryLevel ??
        0
    ),
    connected: Boolean(
        fatigueOutput?.sensorStatus?.connected ??
        fallback?.sensorStatus?.connected ??
        true
    ),
  };

  // alertLevel 统一为 normal/warning/danger
  let alertLevel: any = fatigueOutput?.alertLevel ?? fallback?.alertLevel;
  if (typeof alertLevel === "number") {
    alertLevel = alertLevel === 0 ? "normal" : alertLevel === 1 ? "warning" : "danger";
  }
  if (!alertLevel) {
    alertLevel = fatigueScore < 30 ? "normal" : fatigueScore < 70 ? "warning" : "danger";
  }

  const lastUpdate =
    fatigueOutput?.lastUpdate ??
    fatigueOutput?.timestamp ??
    new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const drivingTime = fatigueOutput?.drivingTime ?? fallback?.drivingTime ?? "--";

  // 组装 FatigueData：字段按你 App 里用到的来补齐
  return {
    ...(fallback as any),
    fatigueScore,
    blinkRate,
    eyelidStatus,
    sensorStatus,
    alertLevel,
    lastUpdate,
    drivingTime,
  } as FatigueData;
}

// ==============================
// 从 bluetooth_data 更新部分状态（信号质量、最后更新时间等）
// ==============================
function patchFromBluetooth(current: FatigueData, bt: any): FatigueData {
  const lastUpdate =
    bt?.receivedAt ||
    bt?.timestamp ||
    new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const signalQuality = Number(bt?.signalQuality ?? current?.sensorStatus?.signalQuality ?? 0);

  return {
    ...current,
    lastUpdate,
    sensorStatus: {
      ...(current.sensorStatus as any),
      signalQuality,
    },
  } as FatigueData;
}

// ==============================
// 专门处理 BluetoothControl 组件传来的 BluetoothFatigueData
// ==============================
function patchFromBluetoothControl(current: FatigueData, btData: BluetoothFatigueData): FatigueData {
  const lastUpdate = new Date(btData.timestamp || Date.now()).toLocaleTimeString("zh-CN", { 
    hour: "2-digit", minute: "2-digit", second: "2-digit" 
  });

  const signalQuality = Number(btData.rawData?.signalQuality ?? current?.sensorStatus?.signalQuality ?? 0);

  return {
    ...current,
    lastUpdate,
    sensorStatus: {
      ...(current.sensorStatus as any),
      connected: true,
      signalQuality,
    },
  } as FatigueData;
}

export default function App() {
  const [currentData, setCurrentData] = useState<FatigueData>(dataService.getCurrentData());
  const [historyData, setHistoryData] = useState<ChartData[]>(generateHistoryData());
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [useBluetoothData, setUseBluetoothData] = useState(false);

  // WS 连接状态
  const [wsStatus, setWsStatus] = useState<"disconnected" | "connecting" | "connected" | "error">("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const wsPingTimerRef = useRef<number | null>(null);

  const WS_URL = useMemo(() => {
    // 支持 https 场景（wss），本地一般是 ws
    const isHttps = window.location.protocol === "https:";
    const proto = isHttps ? "wss" : "ws";
    // 后端疲劳算法服务运行在端口 3002
    return `${proto}://localhost:3002/ws`;
  }, []);

  // ==============================
  // 1) WebSocket：真正驱动 UI 的关键补齐点 ✅
  // ==============================
  useEffect(() => {
    // 你可以选择：只在 isMonitoring 时连接；或永远连接
    if (!isMonitoring) {
      // 停止监控时也断开 WS：保持逻辑清晰
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
        wsRef.current = null;
      }
      if (wsPingTimerRef.current) {
        window.clearInterval(wsPingTimerRef.current);
        wsPingTimerRef.current = null;
      }
      setWsStatus("disconnected");
      return;
    }

    setWsStatus("connecting");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("connected");

      // 心跳：避免中间设备/浏览器把空闲 ws 断掉
      if (wsPingTimerRef.current) {
        window.clearInterval(wsPingTimerRef.current);
      }
      wsPingTimerRef.current = window.setInterval(() => {
        try {
          ws.send(JSON.stringify({ type: "ping", ts: Date.now() }));
        } catch {}
      }, 15000);
    };

    ws.onerror = () => {
      setWsStatus("error");
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
      if (wsPingTimerRef.current) {
        window.clearInterval(wsPingTimerRef.current);
        wsPingTimerRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      let msg: WsMsg | null = null;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!msg || !msg.type) return;

      // 核心：fatigue -> setCurrentData -> UI 自动刷新 ✅
      if (msg.type === "fatigue") {
        setUseBluetoothData(true); // 既然收到算法结果，就说明链路走的是“真实数据路径”
        setCurrentData((prev: FatigueData) => {
          const next = mapFatigueToFatigueData(msg!.data, prev);
          console.log("🔥 接收到疲劳数据更新:", next); // 调试日志
          
          // 同步写入历史曲线
          const newHistoryData: ChartData = {
            time: next.lastUpdate,
            fatigueScore: next.fatigueScore,
            blinkRate: next.blinkRate,
            eyeMovementSpeed: (next as any)?.eyelidStatus?.eyeClosureRatio ?? 0,
            signalQuality: (next as any)?.sensorStatus?.signalQuality ?? 0,
            alertLevel: next.alertLevel === "normal" ? 0 : next.alertLevel === "warning" ? 1 : 2,
          };
          setHistoryData((h: ChartData[]) => [...h, newHistoryData].slice(-25));
          return next;
        });
        return;
      }

      // bluetooth_data：更新信号质量、最后更新时间（用于状态栏/体验）
      if (msg.type === "bluetooth_data") {
        setUseBluetoothData(true);
        setCurrentData((prev: FatigueData) => {
            const updated = patchFromBluetooth(prev, msg!.data);
            
            // 同时更新历史数据（仅更新信号质量和时间，保持其他值不变，避免图表断裂）
            setHistoryData((h: ChartData[]) => {
                const last = h[h.length - 1];
                if (!last) return h;
                
                // 这里简化处理：直接新增一个点，携带最新的信号质量
                const newPoint: ChartData = {
                    ...last,
                    time: updated.lastUpdate,
                    signalQuality: updated.sensorStatus.signalQuality,
                };
                return [...h, newPoint].slice(-25);
            });

            return updated;
        });
        return;
      }

      // stats：如你需要可用于页面展示或调试，这里先留着
      if (msg.type === "stats") {
        // console.log("WS stats:", msg.data);
        return;
      }

      if (msg.type === "pong") return;
    };

    return () => {
      try { ws.close(); } catch {}
      wsRef.current = null;
      if (wsPingTimerRef.current) {
        window.clearInterval(wsPingTimerRef.current);
        wsPingTimerRef.current = null;
      }
    };
  }, [isMonitoring, WS_URL]);

  // ==============================
  // 2) 模拟数据：当 WS 正常工作时，必须关闭（否则会覆盖真实数据）✅
  // ==============================
  useEffect(() => {
    const handleDataUpdate = (data: FatigueData) => {
      setCurrentData(data);

      const newHistoryData: ChartData = {
        time: data.lastUpdate,
        fatigueScore: data.fatigueScore,
        blinkRate: data.blinkRate,
        eyeMovementSpeed: data.eyelidStatus.eyeClosureRatio,
        signalQuality: data.sensorStatus.signalQuality,
        alertLevel: data.alertLevel === "normal" ? 0 : data.alertLevel === "warning" ? 1 : 2,
      };

      setHistoryData((prev: ChartData[]) => [...prev, newHistoryData].slice(-25));
    };

    // 蓝牙 service：你原本逻辑保留（不改变整体链路）
    const handleBluetoothData = (data: BluetoothFatigueData) => {
      setUseBluetoothData(true);
      console.log("蓝牙数据已接收，时间戳:", data.timestamp);
    };

    bluetoothService.addListener(handleBluetoothData);

    // 仅当：在监控 + WS 未连接（或出错）时，才启用模拟数据兜底
    const shouldUseMock = isMonitoring && (wsStatus !== "connected") && !useBluetoothData;

    if (shouldUseMock) {
      console.log("⚠️启用模拟数据 (Reason: Monitoring=ON, WS!=Connected, NoBT)");
      dataService.addListener(handleDataUpdate);
      dataService.startRealTimeData(2000);
    } else {
      dataService.stopRealTimeData();
      dataService.removeListener(handleDataUpdate);
    }

    return () => {
      dataService.removeListener(handleDataUpdate);
      bluetoothService.removeListener(handleBluetoothData);
    };
  }, [isMonitoring, wsStatus, useBluetoothData]);

  const handleToggleMonitoring = () => setIsMonitoring((v) => !v);

  const statusText = useMemo(() => {
    if (!isMonitoring) return "待机";
    if (wsStatus === "connecting") return "连接后端中...";
    if (wsStatus === "error") return "WebSocket 异常（已自动回退）";
    if (wsStatus === "connected") return useBluetoothData ? "实时数据接收中（WS）" : "实时连接已建立（等待数据）";
    return "监控中（未连接）";
  }, [isMonitoring, wsStatus, useBluetoothData]);

  const sourceText = useMemo(() => {
    if (!isMonitoring) return "无";
    if (wsStatus === "connected") return "后端 WebSocket（真实链路）";
    return useBluetoothData ? "单片机蓝牙（本地）" : "模拟数据（兜底）";
  }, [isMonitoring, wsStatus, useBluetoothData]);

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl mb-2">疲劳驾驶监测系统</h1>

          <p className="text-muted-foreground">实时监测驾驶员状态，预防疲劳驾驶风险</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="flex w-full justify-center mb-8 flex-wrap">
            <TabsTrigger value="dashboard" className="flex items-center gap-2 px-3 py-2 min-w-fit">
              <Monitor className="h-4 w-4" />
              实时监控
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2 px-3 py-2 min-w-fit">
              <BarChart3 className="h-4 w-4" />
              数据分析
            </TabsTrigger>
            <TabsTrigger value="bluetooth" className="flex items-center gap-2 px-3 py-2 min-w-fit">
              <Bluetooth className="h-4 w-4" />
              蓝牙连接
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2 px-3 py-2 min-w-fit">
              <Settings className="h-4 w-4" />
              系统设置
            </TabsTrigger>
            <TabsTrigger value="guide" className="flex items-center gap-2 px-3 py-2 min-w-fit">
              <BookOpen className="h-4 w-4" />
              使用说明
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <MonitoringDashboard 
              data={currentData} 
              isMonitoring={isMonitoring}
              wsStatus={wsStatus}
              onToggleMonitoring={handleToggleMonitoring}
            />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <FatigueChart data={historyData} />
          </TabsContent>

          <TabsContent value="bluetooth" className="space-y-6">
            <BluetoothControl
              onDataReceived={(data) => {
                // 使用专门的 patch 函数来合并数据，防止覆盖掉 fatigueScore 等其他字段导致白屏
                setCurrentData((prev) => patchFromBluetoothControl(prev, data));
                setUseBluetoothData(true);
              }}
            />
          </TabsContent>

          <TabsContent value="settings">
            <ControlPanel isMonitoring={isMonitoring} onToggleMonitoring={handleToggleMonitoring} />
          </TabsContent>

          <TabsContent value="guide">
            <UserGuide />
          </TabsContent>
        </Tabs>

        {/* 状态栏 */}
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>系统状态: {statusText}</span>
              <span>•</span>
              <span>数据来源: {sourceText}</span>
              <span>•</span>
              <span>最后更新: {currentData.lastUpdate}</span>
            </div>

            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  !isMonitoring
                    ? "bg-gray-400"
                    : wsStatus === "connected"
                      ? "bg-green-500"
                      : wsStatus === "connecting"
                        ? "bg-yellow-500"
                        : "bg-red-500"
                }`}
              />
              <span className="text-sm text-muted-foreground">
                {wsStatus === "connected" ? "WS 已连接" : wsStatus === "connecting" ? "WS 连接中" : wsStatus === "error" ? "WS 异常" : "WS 未连接"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
