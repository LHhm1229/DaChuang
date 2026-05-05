# 睡眠质量检测系统

本系统通过采集眼睑信号并分析眼部运动（SEM/REM），实现对睡眠质量的实时监测与分期。

---

## 一、系统架构

### 1.1 四层架构模型

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
│  │  前端 :5173  ──代理──▶  /ws/sleep ──▶ ws://localhost:3001/ws            │ │
│  │         ──代理──▶  /api/bluetooth-data-sleep ──▶ http://localhost:3001  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          服务层 (SleepQuality Backend)                        │
│  ┌───────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │  Flask Server      │  │  算法模块          │  │  WebSocket广播          │  │
│  │  app.py            │  │  sleep_quality.py │  │  (15秒心跳机制)         │  │
│  │  端口: 3001         │  │  run_sleep_quality│  │                        │  │
│  └───────────────────┘  └────────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        采集层 (Simulated Data)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  test.py - 模拟睡眠数据生成器                                             │ │
│  │  5种睡眠状态: 清醒(0) | 浅睡N1(1) | 浅睡N2(2) | 深睡(3) | REM(4)          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心文件清单

### 2.1 后端文件

| 文件路径 | 说明 | 关键函数/类 |
|---------|------|------------|
| `app.py` | Flask服务器入口，提供API和WebSocket服务 | `receive_bluetooth_data()`, `broadcast_sleep_quality()`, `ws_handler()` |
| `algorithm/sleep_quality.py` | 睡眠质量核心算法模块 | `run_sleep_quality_pipeline()`, `rule_based_sleep_staging()` |
| `algorithm/__init__.py` | Python包初始化，导出公共API | - |

### 2.2 配置文件

| 文件路径 | 说明 |
|---------|------|
| `requirements.txt` | Python后端依赖列表 |
| `venv/` | Python虚拟环境（已配置Flask等依赖） |

### 2.3 启动脚本

| 文件路径 | 说明 |
|---------|------|
| `start-flask-dev.bat` | 启动Flask开发服务器 |
| `start-backend.bat` | 启动Node.js备用后端 |

### 2.4 测试文件

| 文件路径 | 说明 |
|---------|------|
| `test.py` | 模拟数据注入脚本，生成睡眠信号测试算法 |

---

## 三、数据传输流程

### 3.1 数据流向

```
test.py (模拟数据)
       │
       │ HTTP POST /api/bluetooth-data
       │ {rawData: [...], timestamp: ms, signalQuality: 95}
       ▼
┌──────────────────────────────────────────────────────┐
│  vite.config.ts 代理配置                               │
│  '/api/bluetooth-data-sleep' ──rewrite──▶ '/api/bluetooth-data'│
│  target: 'http://localhost:3001'                              │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  app.py - /api/bluetooth-data (POST)                │
│                                                      │
│  1. 接收数据: body = request.get_json()              │
│  2. 存入bluetooth_data缓冲区 (最多1000条)            │
│  3. 提取rawData加入sleep_signal_buffer               │
│  4. 滑动窗口: 保持最多30秒数据                        │
│  5. 数据足够时(≥300样本)调用算法                    │
└──────────────────────────────────────────────────────┘
       │
       │ sleep_signal_buffer (滑动窗口, 最多3000个点)
       ▼
┌──────────────────────────────────────────────────────┐
│  sleep_quality.py - run_sleep_quality_pipeline()    │
│                                                      │
│  1. 预处理: preprocess_eyelid_signal()               │
│  2. 特征提取: extract_eye_movement_bands()          │
│  3. REM检测: detect_rem_events()                     │
│  4. SEM检测: detect_sem_events()                     │
│  5. 睡眠分期: rule_based_sleep_staging()            │
│  6. 质量评分: score = 50 + (n3*3 + rem*2 - wake*1) * 50 │
└──────────────────────────────────────────────────────┘
       │
       │ sleep_output dict
       │ {qualityScore, currentStage, currentStageName, ...}
       ▼
┌──────────────────────────────────────────────────────┐
│  app.py - broadcast_sleep_quality()                  │
│                                                      │
│  WebSocket广播: {"type": "sleepQuality", "data": {...}}│
│  发送给所有连接的ws客户端                             │
└──────────────────────────────────────────────────────┘
       │
       │ ws://localhost:3001/ws
       ▼
┌──────────────────────────────────────────────────────┐
│  vite.config.ts WebSocket代理                         │
│  '/ws/sleep' ──rewrite──▶ '/ws'                      │
│  target: 'ws://localhost:3001'                      │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  HealthMonitoringSystem 前端                         │
│  显示睡眠质量评分和状态                               │
└──────────────────────────────────────────────────────┘
```

### 3.2 API端点

| 端点 | 方法 | 说明 | 请求体 |
|------|------|------|--------|
| `/api/bluetooth-data` | POST | 接收蓝牙数据 | `{rawData: number[], timestamp: number, signalQuality: number}` |
| `/api/sleep-quality-latest` | GET | 获取最新睡眠质量 | - |
| `/api/stats` | GET | 获取数据统计 | - |
| `/api/clear-buffer` | POST | 清空数据缓冲区 | - |
| `/ws` | WebSocket | 实时数据推送 | `{"type": "sleepQuality", "data": {...}}` |

---

## 四、算法核心

### 4.1 睡眠分期规则

| 阶段 | 值 | 判断条件 |
|------|-----|---------|
| 深睡 | 3 | signal_std < 0.05（低变异性） |
| REM | 4 | rem_density > 0.3 && rem_sem_ratio > 2.0 |
| 浅睡N1 | 1 | sem_count >= 1 && rem_density < 0.2 |
| 清醒 | 0 | rem_density > 0.5 || sem_count > 2 |
| 浅睡N2 | 2 | 默认（其他情况） |

### 4.2 质量评分计算

```python
score = (n3_epochs * 3 + rem_epochs * 2 - wake_epochs * 1) / max(n_epochs, 1)
score = max(0, min(100, 50 + score * 50))
```

- 深睡(3)每epoch加3分
- REM(4)每epoch加2分
- 清醒(0)每epoch减1分
- 基础分50分

### 4.3 模拟数据特征

| 状态 | signal_std | rem_density | sem_count | 生成方式 |
|------|-----------|-------------|-----------|---------|
| 清醒 | >0.5 | >0.5 | >2 | 高频眨眼, 基线0.15 |
| 深睡 | <0.05 | 低 | 低 | 稳定在0.5 |
| 浅睡N1 | 中 | <0.2 | ≥1 | 中等变异 |
| 浅睡N2 | 中低 | 低 | 低 | 0.5±0.1 |
| REM | 高频振荡 | >0.3 | 中 | 1.5Hz正弦波 |

---

## 五、启动方式

### 5.1 后端服务

```bash
cd d:\MyProject\DC\DaChuang\SleepQuality
call venv\Scripts\activate.bat
python app.py
```

输出:
```
[SERVER] 睡眠质量后端服务已启动
   HTTP:      http://localhost:3001
   WebSocket: ws://localhost:3001/ws
   POST BT:   http://localhost:3001/api/bluetooth-data
```

### 5.2 前端服务（健康监测系统）

```bash
cd d:\MyProject\DC\DaChuang\HealthMonitoringSystem
npm run dev
```

### 5.3 模拟数据注入

```bash
cd d:\MyProject\DC\DaChuang\SleepQuality
python test.py
```

---

## 六、关键配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 端口 | 3001 | 后端服务端口 |
| SLEEP_WINDOW_SECONDS | 30 | 滑动窗口时长(秒) |
| SAMPLING_RATE | 100 | 采样率(Hz) |
| SLEEP_MIN_SAMPLES | 300 | 最小样本数(3秒) |
| BLUETOOTH_DATA_MAX | 1000 | 原始数据缓冲区大小 |

---

## 七、调试日志

### 后端日志（终端）

| 日志标记 | 含义 |
|---------|------|
| `[API] 收到数据请求` | 收到HTTP请求 |
| `[DATA] 蓝牙数据接收` | 数据接收详情 |
| `[ALGO] SLEEP computed` | 算法计算结果 |
| `[METRICS] 睡眠指标` | 核心指标输出 |
| `[WS] 前端客户端已连接/断开` | WebSocket连接状态 |

### 前端日志（浏览器控制台）

| 日志标记 | 含义 |
|---------|------|
| `[App] 收到消息` | WebSocket消息接收 |
| `[DataMapper] Raw sleep quality data received` | 原始数据 |

---

## 八、常见问题排查

### 8.1 前端显示0或卡在某个值
1. 检查后端是否发送数据: 终端是否有`[ALGO] SLEEP computed`日志
2. 检查WebSocket连接: 前端是否显示"实时检测中"
3. 检查数据映射: 浏览器控制台是否有`[DataMapper] Validation failed`错误

### 8.2 分数和阶段不匹配
1. 检查模拟数据: 不同状态生成的信号特征是否符合算法预期
2. 检查算法阈值: signal_std, rem_density等阈值是否合理
3. 对比终端日志: 查看实际计算出的特征值

### 8.3 数据传输中断
1. 检查代理配置: vite.config.ts中`/api/bluetooth-data-sleep`是否正确
2. 检查CORS: Flask的CORS配置是否包含前端地址
3. 检查心跳: WebSocket是否15秒内有心跳消息

---

## 九、与其他系统对比

| 对比项 | 疲劳驾驶 | 睡眠质量 |
|--------|---------|---------|
| 端口 | 3002 | 3001 |
| 算法文件 | blink_fatigue.py | sleep_quality.py |
| 测试脚本 | test.py | test.py |
| 数据类型 | 疲劳评分(0-100) | 睡眠阶段(0-4)+质量评分 |
| 核心指标 | 眨眼频率, 时长 | signal_std, rem_density |
| 分期数量 | 3级 | 5级(清醒/浅睡N1/浅睡N2/深睡/REM) |
