# 健康监测系统项目开发规范 (Project Rules)

本规范旨在确保多人协作及 Trae AI 参与开发时，项目架构清晰、逻辑一致，避免功能冲突。任何开发者或 AI 助手在修改代码前，必须完整阅读并遵守本规范。

## 一、 环境配置与运行规范 (协作必备)

### 1. 软件环境
*   **前端**: Node.js v18+ (推荐使用 LTS 版本)。
*   **后端**: Python 3.8+。
*   **浏览器**: 必须使用 **Chrome** 或 **Edge** (Web Bluetooth API 依赖项)，且必须通过 `localhost` 访问以保证安全上下文。

### 2. 依赖安装
*   **前端**: 在 `HealthMonitoringSystem` 目录下运行 `npm install`。
*   **后端**: 在各后端目录下（如 `FatiguedDriving`）运行 `pip install flask flask-cors flask-socketio eventlet numpy`。
    *   *注意*: `eventlet` 在 Windows 下是 WebSocket 稳定的核心，不可缺失。

### 3. 标准启动流程
1.  **启动后端**: 进入对应目录（如 `FatiguedDriving`），运行 `python app.py`。
2.  **启动前端**: 在 `HealthMonitoringSystem` 运行 `npm run dev`。
3.  **连接蓝牙**: 开启电脑蓝牙，在前端界面点击蓝牙图标配对。
4.  **状态校验**: 确认右上角状态圆点为 **绿色**。若为红色，说明 WebSocket 未连通。

## 二、 核心架构与修改规范 (防乱逻辑)

### 1. 通信协议 (上行/下行)
*   **上行 (采集)**: 前端采集 -> **节流 (500ms)** -> POST `/api/bluetooth-data`。
*   **下行 (反馈)**: 后端计算 -> WebSocket 推送 (带 `type` 字段) -> 前端监听。
*   **禁止硬编码**: 严禁硬编码端口（如 `3002`），必须使用 `MODULE_PORT_MAP` 获取。

### 2. 数据映射层 (Data Mapping) - **修改禁区**
*   **原则**: UI 组件严禁解析原始 JSON。
*   **规范**: 任何后端字段变动，必须先在 `src/services/dataMapper.ts` 中更新映射逻辑。
*   **AI 指令**: Trae 在修改 UI 时，若发现数据结构不匹配，应主动检查并修改 `dataMapper.ts`。

### 3. 高频数据处理 (Throttling)
*   **禁止防抖 (Debounce)**: 蓝牙数据连续性极强，防抖会导致请求被无限推迟。
*   **必须节流 (Throttle)**: 前端发送频率固定为 `500ms`。

### 4. UI 渲染与优先级
*   **结果优先**: 优先渲染 `type: "fatigue"` 等算法结果消息。
*   **降级渲染**: 仅在无算法结果时，使用 `type: "bluetooth_data"` 原始回显进行 UI 更新。

## 三、 Trae AI 修改指令 (给 AI 的特别说明)

### 1. 代码风格
*   **Python**: `eventlet.monkey_patch()` 必须置于 `app.py` 文件最顶端。
*   **TypeScript**: 保持严格类型定义，避免使用 `any`（除非在数据映射初期处理原始 JSON）。

### 2. 修改安全性
*   在修改 `App.tsx` 的 `useEffect` 或 `useCallback` 时，确保蓝牙监听器 (`bluetoothService.addListener`) 是全局注册的，且包含正确的清理函数 (`removeListener`)。

## 四、 端口与模块分配

| 模块名称 | 目录 | 后端端口 | WebSocket 类型 |
| :--- | :--- | :--- | :--- |
| 睡眠质量检测 | `SleepQuality` | 3001 | `sleepQuality` |
| 疲劳驾驶预警 | `FatiguedDriving` | 3002 | `fatigue` |
| 干眼症监测 | `DryEye` | 3000 | `dryEye` |
| 前端系统 | `HealthMonitoringSystem` | 5173 (Vite) | - |

---
**提示**: 若在调试中发现数据不实时，请优先检查浏览器控制台 (Console) 是否有 `[DataMapper]` 报错，以及网络 (Network) 标签中 WebSocket 消息是否正常。
