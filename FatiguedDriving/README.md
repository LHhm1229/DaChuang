# 疲劳驾驶监测系统

本系统通过采集眼睑信号并分析眨眼特征，实现对驾驶员疲劳状态的实时监测与预警。

---

## 一、项目背景与核心目标

本项目旨在开发一套**软硬件结合的实时疲劳驾驶监测系统**。其核心目标是通过可穿戴硬件（如智能眼镜或头带）采集驾驶员的眼睑电压（或类似生理电信号），利用前端的 Web Bluetooth 技术将信号接入系统，交由后端的数字信号处理（DSP）算法进行分析，最终在前端大屏上实时呈现驾驶员的疲劳状态、眨眼特征以及危险预警，从而达到预防交通事故的目的。

---

## 二、系统架构

### 2.1 四层架构模型

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           显示层 (HealthMonitoringSystem)                      │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │  Gateway    │  │ UnifiedDashboard │  │  BluetoothControl              │  │
│  │  (模块选择)  │  │   (数据可视化)    │  │  (蓝牙数据注入)                  │  │
│  └─────────────┘  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ WebSocket / HTTP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        通信层 (Vite Proxy)                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  前端 :5173  ──代理──▶  /ws/fatigue ──▶ ws://localhost:3002/ws        │ │
│  │         ──代理──▶  /api/bluetooth-data-fatigue ──▶ http://localhost:3002│ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        服务层 (FatiguedDriving Backend)                       │
│  ┌───────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │  Flask Server      │  │  算法模块          │  │  WebSocket广播          │  │
│  │  app.py            │  │  blink_fatigue.py │  │  (15秒心跳机制)         │  │
│  │  端口: 3002        │  │  data_buffer.py   │  │                        │  │
│  └───────────────────┘  └────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        采集层 (Simulated Data)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  test.py - 疲劳驾驶数据模拟器                                             │ │
│  │  5种状态: 清醒 | 轻微疲劳 | 中度疲劳 | 重度疲劳 | 正常                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心文件清单

### 3.1 后端文件

| 文件路径 | 说明 | 关键函数/类 |
|---------|------|------------|
| `app.py` | Flask服务器入口，提供API和WebSocket服务 | `receive_bluetooth_data()`, `broadcast_fatigue()`, `ws_handler()` |
| `algorithm/blink_fatigue.py` | 疲劳检测核心算法 | `run_fatigue_pipeline()`, `assess_fatigue()`, `detect_blink_events()` |
| `algorithm/data_buffer.py` | 数据缓冲区管理模块 | `DataBuffer`, `DataBroadcaster` |
| `algorithm/__init__.py` | Python包初始化 | - |

### 3.2 配置文件

| 文件路径 | 说明 |
|---------|------|
| `requirements.txt` | Python后端依赖列表 |
| `server.js` | Node.js备用后端服务 |

### 3.3 启动脚本

| 文件路径 | 说明 |
|---------|------|
| `start-flask-dev.bat` | 启动Flask开发服务器 |
| `start-backend.bat` | 启动Node.js备用后端 |

### 3.4 测试文件

| 文件路径 | 说明 |
|---------|------|
| `test.py` | 模拟数据注入脚本，生成疲劳驾驶信号测试算法 |

---

## 四、数据传输流程

### 4.1 数据流向

```
test.py (信号生成器)
        │
        │ HTTP POST /api/bluetooth-data
        │ {rawData: [...], timestamp: ms, signalQuality: 95}
        ▼
┌──────────────────────────────────────────────────────┐
│  vite.config.ts 代理配置                              │
│  '/api/bluetooth-data-fatigue' ──rewrite──▶ '/api/bluetooth-data'│
│  target: 'http://localhost:3002'                    │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  app.py - /api/bluetooth-data (POST)                │
│                                                      │
│  1. 接收数据: body = request.get_json()              │
│  2. 存入bluetooth_data缓冲区 (最多1000条)             │
│  3. 提取rawData加入fatigue_signal_buffer            │
│  4. 滑动窗口: 保持最多30秒数据                       │
│  5. 数据足够时(≥300样本)调用算法                     │
└──────────────────────────────────────────────────────┘
        │
        │ fatigue_signal_buffer (滑动窗口, 最多3000个点)
        ▼
┌──────────────────────────────────────────────────────┐
│  blink_fatigue.py - run_fatigue_pipeline()          │
│                                                      │
│  1. 预处理: adaptive_preprocess_eyelid_signal()      │
│     - 形态学滤波去基线漂移                           │
│     - 低通滤波 (6.5Hz)                              │
│     - 归一化到 [0,1]                                │
│  2. 特征提取: extract_blink_features()               │
│     - 峰值检测 (height=0.55)                        │
│     - 谷值检测 (找 -x 的峰)                         │
│     - 计算: 频率, 时长, 幅度, 闭合比例                │
│  3. 事件检测: detect_blink_events()                  │
│     - normal: 正常眨眼                               │
│     - long: 长时间眨眼 (>1.5倍平均)                  │
│     - incomplete: 凝视区间 (间隔过长+波动小)          │
│  4. 疲劳评估: assess_fatigue()                       │
│     - 5维度评分加权融合                              │
│     - 输出: 疲劳分数 (0-100) + 等级                  │
└──────────────────────────────────────────────────────┘
        │
        │ fatigue_output dict
        │ {fatigueScore, fatigueLevel, blinkRate, ...}
        ▼
┌──────────────────────────────────────────────────────┐
│  app.py - broadcast_fatigue()                       │
│                                                      │
│  WebSocket广播: {"type": "fatigue", "data": {...}}  │
└──────────────────────────────────────────────────────┘
        │
        │ ws://localhost:3002/ws
        ▼
┌──────────────────────────────────────────────────────┐
│  HealthMonitoringSystem 前端                         │
│  显示疲劳评分和状态                                  │
└──────────────────────────────────────────────────────┘
```

### 4.2 API端点

| 端点 | 方法 | 说明 | 请求体 |
|------|------|------|--------|
| `/api/bluetooth-data` | POST | 接收蓝牙数据 | `{rawData: number[], timestamp: number, signalQuality: number}` |
| `/api/fatigue-latest` | GET | 获取最新疲劳结果 | - |
| `/api/stats` | GET | 获取数据统计 | - |
| `/api/clear-buffer` | POST | 清空数据缓冲区 | - |
| `/ws` | WebSocket | 实时数据推送 | `{"type": "fatigue", "data": {...}}` |

---

## 五、算法核心

### 5.1 预处理 (adaptive_preprocess_eyelid_signal)

```python
def adaptive_preprocess_eyelid_signal(raw_signal, sampling_rate=100):
    # 1) 去直流
    centered_signal = x - np.mean(x)

    # 2) 形态学滤波估计基线漂移 (2秒窗口)
    size_drift = int(drift_window_sec * sampling_rate)
    trend_open = grey_opening(centered_signal, size=size_drift)
    trend_base = grey_closing(trend_open, size=size_drift)
    baseline_removed = centered_signal - trend_base

    # 3) 低通滤波 (6.5Hz)
    b, a = signal.butter(8, 6.5/nyquist, "lowpass")
    filtered_signal = signal.filtfilt(b, a, baseline_removed)

    # 4) 归一化到 [0,1]
    normalized_signal = (filtered_signal - min) / (max - min)
```

### 5.2 眨眼特征提取 (extract_blink_features)

```python
# 关键特征计算：
features = {
    "avg_blink_amplitude": 平均眨眼幅度,
    "max_blink_amplitude": 最大眨眼幅度,
    "avg_blink_interval": 平均眨眼间隔 (峰间距),
    "blink_frequency": 眨眼频率 (次/秒),
    "blink_rate_per_min": 眨眼频率 (次/分钟),
    "avg_blink_duration": 平均眨眼时长 (谷到谷),
    "eye_closure_ratio": 眼闭合比例 (%),
    "eye_status": "open" / "closed" (最近1秒均值判断),
    "signal_quality": 信号质量 (0~1),
}
```

### 5.3 事件分类 (detect_blink_events)

```python
# 分类规则：
if e["duration"] > avg_dur * 1.5:
    classified_blinks["long"].append(e)      # 长眨眼
else:
    classified_blinks["normal"].append(e)   # 正常眨眼

# 不完全眨眼（凝视区间）：
if (interval_duration > normal_interval * 1.5 and
    max_variation < 0.02):
    classified_blinks["incomplete"].append(e)  # 凝视
```

### 5.4 疲劳评分算法 (assess_fatigue)

```python
# 5维度评分：
weights = {
    "blink_frequency_score": 0.20,      # 眨眼频率
    "blink_duration_score": 0.25,       # 眨眼时长
    "long_blink_ratio_score": 0.15,     # 长眨眼比例
    "incomplete_blink_ratio_score": 0.10, # 不完全眨眼比例
    "eye_closure_score": 0.35,          # 眼闭合比例（权重最高）
}

# 疲劳等级：
if fatigue_score < 20:   fatigue_level = "清醒"
elif fatigue_score < 40: fatigue_level = "轻度疲劳"
elif fatigue_score < 60: fatigue_level = "中度疲劳"
elif fatigue_score < 80: fatigue_level = "重度疲劳"
else:                    fatigue_level = "危险"
```

### 5.5 眼闭合比例计分规则

```python
# 更敏感的计分：
if eye_closure_ratio >= 25: score = 100.0    # 严重疲劳
elif eye_closure_ratio >= 18: score = 85.0   # 重度
elif eye_closure_ratio >= 12: score = 65.0   # 中度
elif eye_closure_ratio >= 8: score = 45.0    # 轻度
elif eye_closure_ratio >= 4: score = (ratio - 4) * 15  # 轻微
else: score = 0.0
```

### 5.6 模拟数据特征

| 状态 | 眨眼频率 | 眨眼类型 | 基线特征 | 疲劳分预期 |
|------|---------|---------|---------|-----------|
| 清醒 | ~12次/分钟 | 短眨眼 (100ms) | 稳定低基线 (0.05) | < 30 |
| 疲劳状态 | 低频 | 长眨眼 + 长时间闭眼 (2s+) | 高基线 (0.55) | > 70 |
| 信号不稳定 | 随机 | 无规律 | 大幅波动 | 数据波动 |

---

## 六、启动方式

### 6.1 后端服务

```bash
cd d:\MyProject\DC\DaChuang\FatiguedDriving
python app.py
```

输出:
```
[服务器] 疲劳驾驶后端服务启动中...
   访问地址: http://localhost:3002
   WebSocket: ws://localhost:3002/ws
   API (POST 数据): http://localhost:3002/api/bluetooth-data
```

### 6.2 前端服务（健康监测系统）

```bash
cd d:\MyProject\DC\DaChuang\HealthMonitoringSystem
npm run dev
```

### 6.3 模拟数据注入

```bash
cd d:\MyProject\DC\DaChuang\FatiguedDriving
python test.py
```

---

## 七、调试日志

### 后端日志（终端）

| 日志标记 | 含义 |
|---------|------|
| `[DATA] 蓝牙数据接收` | 收到HTTP数据 |
| `[STATS] 数据统计` | 每10次的数据统计 |
| `[ALGO] FATIGUE computed` | 算法计算结果 |
| `[WS] 前端客户端已连接/断开` | WebSocket连接状态 |

### 前端日志（浏览器控制台）

| 日志标记 | 含义 |
|---------|------|
| `[App] 收到消息` | WebSocket消息接收 |
| `[App] 处理数据` | 数据处理开始 |
| `[App] 映射后数据` | 数据映射结果 |

---

## 八、关键配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 端口 | 3002 | 后端服务端口 |
| FATIGUE_WINDOW_SECONDS | 30 | 滑动窗口时长(秒) |
| SAMPLING_RATE | 100 | 采样率(Hz) |
| MIN_SAMPLES | 300 | 最小样本数(3秒) |
| BLUETOOTH_DATA_MAX | 1000 | 原始数据缓冲区大小 |

---

## 九、核心技术栈

### 算法与后端（Python 生态）
- **Flask & Flask-SocketIO**：轻量级Web框架，原生WebSocket支持
- **NumPy**：高效的C语言级矩阵运算
- **SciPy**：信号处理（低通滤波、寻峰、形态学运算）

### 前端展示（现代 Web 生态）
- **React 18 & Vite**：组件化状态管理，极速冷启动和HMR
- **Web Bluetooth API**：网页直接获取蓝牙权限
- **Tailwind CSS & Radix UI**：原子化CSS，无头可访问组件
- **Recharts**：基于D3和SVG的实时折线图渲染

---

## 十、与其他系统对比

| 对比项 | 疲劳驾驶 | 睡眠质量 | 干眼症 |
|--------|---------|---------|--------|
| 端口 | 3002 | 3001 | 3000 |
| 算法文件 | blink_fatigue.py | sleep_quality.py | dry_eye.py |
| 测试脚本 | test.py | test.py | test.py |
| 数据类型 | 疲劳评分(0-100) | 睡眠阶段(0-4)+质量评分 | 干眼风险(0-100%) |
| 核心指标 | 眨眼频率, 时长 | signal_std, rem_density | blink_rate, incomplete_ratio |
| 分期数量 | 4级(清醒/轻度/中度/重度) | 5级(清醒/浅睡N1/浅睡N2/深睡/REM) | 3级(正常/干眼/严重) |
