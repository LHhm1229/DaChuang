# 项目架构与数据流体验报告

## 1. 干眼症监测系统

### 1.1 核心技术栈与依赖清单

**前端技术栈**：
- React 18.3.1
- Vite 6.3.5
- TypeScript
- Radix UI 组件库
- recharts 图表库
- WebSocket 通信
- Tailwind CSS

**后端技术栈**：
- Python 3.8+
- Flask 3.0.3
- Flask-CORS 5.0.0
- Flask-Sock 0.7.0
- NumPy 2.4.4
- SciPy 1.17.1

**核心依赖**：
| 依赖 | 版本 | 用途 | 来源 |
|------|------|------|------|
| react | ^18.3.1 | 前端框架 | package.json |
| @radix-ui/react-* | ^1.1.2 - ^1.2.6 | UI组件库 | package.json |
| recharts | ^2.15.2 | 数据可视化 | package.json |
| Flask | 3.0.3 | 后端框架 | requirements.txt |
| NumPy | 2.4.4 | 科学计算 | site-packages |
| SciPy | 1.17.1 | 信号处理 | site-packages |

### 1.2 精确的模块职责划分

**目录结构**：
```
DryEye/
├── src/
│   ├── components/          # 前端组件
│   │   ├── ui/             # Radix UI组件
│   │   ├── BluetoothControl.tsx  # 蓝牙控制组件
│   │   ├── ControlPanel.tsx      # 控制面板
│   │   ├── DryEyeChart.tsx       # 干眼症数据图表
│   │   └── MonitoringDashboard.tsx  # 监测仪表盘
│   ├── services/           # 服务层
│   │   ├── bluetoothService.ts   # 蓝牙服务
│   │   ├── dataService.ts        # 数据服务
│   │   └── websocketService.ts   # WebSocket服务
│   ├── App.tsx             # 前端入口
│   └── main.tsx            # 应用入口
├── algorithm/              # 算法模块
│   └── dry_eye.py          # 干眼症算法实现
├── app.py                  # 后端服务入口
├── package.json            # 前端依赖
└── requirements.txt        # 后端依赖
```

**模块职责**：
| 模块 | 主要职责 | 文件位置 | 关键功能 |
|------|----------|----------|----------|
| 前端入口 | 应用初始化与路由 | src/App.tsx | WebSocket连接管理 |
| 监测仪表盘 | 数据可视化与用户交互 | src/components/MonitoringDashboard.tsx | 展示干眼症风险评估结果 |
| 数据服务 | 数据处理与状态管理 | src/services/dataService.ts | 模拟数据生成与状态管理 |
| WebSocket服务 | 实时数据通信 | src/services/websocketService.ts | 接收后端推送的实时数据 |
| 后端服务 | API与WebSocket处理 | app.py | 接收蓝牙数据，调用算法，推送结果 |
| 干眼症算法 | 信号处理与风险评估 | algorithm/dry_eye.py | 眨眼检测与干眼症风险评估 |

### 1.3 实时数据流与通信协议

**数据流**：
1. **数据采集**：通过蓝牙从硬件设备获取原始信号数据
2. **数据传输**：蓝牙数据 → 后端API（/api/bluetooth-data）
3. **数据处理**：后端接收数据 → 存储到缓冲区 → 调用算法处理
4. **结果计算**：算法处理原始信号 → 生成干眼症风险评估结果
5. **实时推送**：后端通过WebSocket推送评估结果到前端
6. **前端展示**：前端接收数据 → 更新UI展示

**通信协议**：
- **HTTP API**：
  - POST /api/bluetooth-data：接收蓝牙数据
  - GET /api/dry-eye-latest：获取最新干眼症评估结果
  - GET /api/stats：获取数据统计信息
  - POST /api/clear-buffer：清空数据缓冲区
- **WebSocket**：
  - 路径：/ws
  - 消息类型：
    - hello：连接握手
    - ping/pong：心跳
    - bluetooth_data：原始蓝牙数据
    - dryEye：干眼症评估结果
    - stats：数据统计信息

**数据格式**：
- 蓝牙数据：`{rawData: number[], timestamp: number, signalQuality: number}`
- 干眼症评估结果：`{blinkRate: number, avgBlinkDuration: number, dryEyeRiskScore: number, dryEyeRiskLevel: string, ...}`

### 1.4 算法黑盒的输入输出映射

**算法函数**：`run_dry_eye_pipeline`

**输入参数**：
| 参数 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| raw_signal | np.ndarray | 原始信号数据 | [0.1, 0.2, 0.3, ...] |
| sampling_rate | int | 采样率 | 100 |
| duration_sec | float | 信号持续时间 | 10.0 |

**输出结果**：
| 字段 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| blinkRate | number | 眨眼频率（次/分钟） | 15.5 |
| avgBlinkDuration | number | 平均眨眼持续时间（毫秒） | 250.0 |
| eyeClosureRatio | number | 眼睛闭合比例（%） | 3.5 |
| incompleteBlinkRatio | number | 不完全眨眼比例（%） | 10.0 |
| longBlinkRatio | number | 长眨眼比例（%） | 5.0 |
| dryEyeRiskScore | number | 干眼症风险评分（0-100） | 45.0 |
| dryEyeRiskLevel | string | 干眼症风险等级 | "中风险" |
| totalBlinks | number | 总眨眼次数 | 15 |
| incompleteBlinks | number | 不完全眨眼次数 | 2 |
| longBlinks | number | 长眨眼次数 | 1 |

**算法流程**：
1. 信号预处理：中心化、低通滤波、归一化
2. 眨眼事件检测：基于小波变换的眨眼检测
3. 计算干眼症指标：眨眼频率、持续时间、闭合比例等
4. 风险评估：基于多维度指标的综合评分

### 1.5 启动流程与运行环境诊断

**启动流程**：
1. 前端：`npm run dev` → 启动Vite开发服务器
2. 后端：`python app.py` → 启动Flask服务

**运行环境**：
- **前端**：
  - Node.js 16+
  - npm 7+
  - 浏览器支持：Chrome, Firefox, Safari, Edge
- **后端**：
  - Python 3.8+
  - 依赖：Flask, Flask-CORS, Flask-Sock, NumPy, SciPy

**端口配置**：
- 前端：默认3000端口（Vite开发服务器）
- 后端：3000端口（Flask服务）
- WebSocket：ws://localhost:3000/ws

**诊断命令**：
- 检查前端依赖：`npm install`
- 检查后端依赖：`pip install -r requirements.txt`
- 测试API：`curl http://localhost:3000/`
- 测试WebSocket：使用WebSocket客户端连接ws://localhost:3000/ws

## 2. 睡眠质量检测系统

### 2.1 核心技术栈与依赖清单

**前端技术栈**：
- React 18.3.1
- Vite 6.3.5
- TypeScript
- Radix UI 组件库
- recharts 图表库
- WebSocket 通信
- Tailwind CSS

**后端技术栈**：
- Python 3.8+
- Flask 3.0.3
- Flask-CORS 5.0.0
- Flask-Sock 0.7.0
- NumPy 2.4.4

**核心依赖**：
| 依赖 | 版本 | 用途 | 来源 |
|------|------|------|------|
| react | ^18.3.1 | 前端框架 | package.json |
| @radix-ui/react-* | ^1.1.2 - ^1.2.6 | UI组件库 | package.json |
| recharts | ^2.15.2 | 数据可视化 | package.json |
| Flask | 3.0.3 | 后端框架 | requirements.txt |
| NumPy | 2.4.4 | 科学计算 | venv/site-packages |

### 2.2 精确的模块职责划分

**目录结构**：
```
SleepQuality/
├── src/
│   ├── components/          # 前端组件
│   │   ├── ui/             # Radix UI组件
│   │   ├── BluetoothControl.tsx  # 蓝牙控制组件
│   │   ├── ControlPanel.tsx      # 控制面板
│   │   ├── MonitoringDashboard.tsx  # 监测仪表盘
│   │   └── SleepChart.tsx        # 睡眠数据图表
│   ├── services/           # 服务层
│   │   ├── bluetoothService.ts   # 蓝牙服务
│   │   ├── dataService.ts        # 数据服务
│   │   └── websocketService.ts   # WebSocket服务
│   ├── App.tsx             # 前端入口
│   └── main.tsx            # 应用入口
├── algorithm/              # 算法模块
│   └── sleep_quality.py    # 睡眠质量算法实现
├── app.py                  # 后端服务入口
├── package.json            # 前端依赖
└── requirements.txt        # 后端依赖
```

**模块职责**：
| 模块 | 主要职责 | 文件位置 | 关键功能 |
|------|----------|----------|----------|
| 前端入口 | 应用初始化与路由 | src/App.tsx | WebSocket连接管理 |
| 监测仪表盘 | 数据可视化与用户交互 | src/components/MonitoringDashboard.tsx | 展示睡眠阶段和质量评估 |
| 数据服务 | 数据处理与状态管理 | src/services/dataService.ts | 模拟数据生成与状态管理 |
| WebSocket服务 | 实时数据通信 | src/services/websocketService.ts | 接收后端推送的实时数据 |
| 后端服务 | API与WebSocket处理 | app.py | 接收蓝牙数据，调用算法，推送结果 |
| 睡眠质量算法 | 信号处理与睡眠分期 | algorithm/sleep_quality.py | 眼动检测与睡眠阶段评估 |

### 2.3 实时数据流与通信协议

**数据流**：
1. **数据采集**：通过蓝牙从硬件设备获取原始信号数据
2. **数据传输**：蓝牙数据 → 后端API（/api/bluetooth-data）
3. **数据处理**：后端接收数据 → 存储到缓冲区 → 调用算法处理
4. **结果计算**：算法处理原始信号 → 生成睡眠质量评估结果
5. **实时推送**：后端通过WebSocket推送评估结果到前端
6. **前端展示**：前端接收数据 → 更新UI展示

**通信协议**：
- **HTTP API**：
  - POST /api/bluetooth-data：接收蓝牙数据
  - GET /api/sleep-quality-latest：获取最新睡眠质量评估结果
  - GET /api/stats：获取数据统计信息
  - POST /api/clear-buffer：清空数据缓冲区
- **WebSocket**：
  - 路径：/ws
  - 消息类型：
    - hello：连接握手
    - ping/pong：心跳
    - bluetooth_data：原始蓝牙数据
    - sleepQuality：睡眠质量评估结果
    - stats：数据统计信息

**数据格式**：
- 蓝牙数据：`{rawData: number[], timestamp: number, signalQuality: number}`
- 睡眠质量评估结果：`{qualityScore: number, currentStage: number, currentStageName: string, rem_density: number, sem_count: number, ...}`

### 2.4 算法黑盒的输入输出映射

**算法函数**：`run_sleep_quality_pipeline`

**输入参数**：
| 参数 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| raw_signal | np.ndarray | 原始信号数据 | [0.1, 0.2, 0.3, ...] |
| sampling_rate | int | 采样率 | 100 |

**输出结果**：
| 字段 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| totalMinutes | number | 总监测时间（分钟） | 5.0 |
| tstMinutes | number | 总睡眠时间（分钟） | 4.5 |
| sleepEfficiency | number | 睡眠效率（%） | 90.0 |
| qualityScore | number | 睡眠质量评分（0-100） | 75.0 |
| currentStage | number | 当前睡眠阶段 | 2 |
| currentStageName | string | 当前睡眠阶段名称 | "浅睡N2" |
| stageSequence | number[] | 睡眠阶段序列 | [0, 1, 2, 3, 2, 4, ...] |
| stageDurations | object | 各阶段持续时间 | {wake: 0.5, n1: 0.5, n2: 2.0, n3: 1.0, rem: 0.5} |
| stagePercentages | object | 各阶段占比 | {wake: 10.0, n1: 10.0, n2: 40.0, n3: 20.0, rem: 20.0} |
| rem_density | number | REM密度 | 0.2 |
| sem_count | number | SEM事件数量 | 1 |
| rem_energy | number | REM能量 | 1.5 |
| sem_energy | number | SEM能量 | 0.8 |
| rem_sem_ratio | number | REM/SEM能量比 | 1.875 |
| signal_std | number | 信号标准差 | 0.08 |

**算法流程**：
1. 信号预处理：滤波、基线移除、归一化
2. 特征提取：提取REM（快速眼动）和SEM（慢速眼动）特征
3. 睡眠分期：基于规则的睡眠阶段判断
4. 质量评估：计算睡眠质量评分和各阶段占比

### 2.5 启动流程与运行环境诊断

**启动流程**：
1. 前端：`npm run dev` → 启动Vite开发服务器
2. 后端：`python app.py` → 启动Flask服务

**运行环境**：
- **前端**：
  - Node.js 16+
  - npm 7+
  - 浏览器支持：Chrome, Firefox, Safari, Edge
- **后端**：
  - Python 3.8+
  - 依赖：Flask, Flask-CORS, Flask-Sock, NumPy

**端口配置**：
- 前端：默认3000端口（Vite开发服务器）
- 后端：3001端口（Flask服务）
- WebSocket：ws://localhost:3001/ws

**诊断命令**：
- 检查前端依赖：`npm install`
- 检查后端依赖：`pip install -r requirements.txt`
- 测试API：`curl http://localhost:3001/`
- 测试WebSocket：使用WebSocket客户端连接ws://localhost:3001/ws

## 3. 疲劳驾驶监测系统

### 3.1 核心技术栈与依赖清单

**前端技术栈**：
- React 18.3.1
- Vite 6.3.5
- TypeScript
- Radix UI 组件库
- recharts 图表库
- WebSocket 通信
- Tailwind CSS

**后端技术栈**：
- Python 3.8+
- Flask 3.0.3
- Flask-CORS 5.0.0
- Flask-Sock 0.7.0
- NumPy 2.4.4

**核心依赖**：
| 依赖 | 版本 | 用途 | 来源 |
|------|------|------|------|
| react | ^18.3.1 | 前端框架 | package.json |
| @radix-ui/react-* | ^1.1.2 - ^1.2.6 | UI组件库 | package.json |
| recharts | ^2.15.2 | 数据可视化 | package.json |
| Flask | 3.0.3 | 后端框架 | requirements.txt |
| NumPy | 2.4.4 | 科学计算 | env/site-packages |

### 3.2 精确的模块职责划分

**目录结构**：
```
FatiguedDriving/
├── src/
│   ├── components/          # 前端组件
│   │   ├── ui/             # Radix UI组件
│   │   ├── BluetoothControl.tsx  # 蓝牙控制组件
│   │   ├── ControlPanel.tsx      # 控制面板
│   │   ├── FatigueChart.tsx      # 疲劳数据图表
│   │   └── MonitoringDashboard.tsx  # 监测仪表盘
│   ├── services/           # 服务层
│   │   ├── bluetoothService.ts   # 蓝牙服务
│   │   ├── dataService.ts        # 数据服务
│   │   └── websocketService.ts   # WebSocket服务
│   ├── App.tsx             # 前端入口
│   └── main.tsx            # 应用入口
├── algorithm/              # 算法模块
│   └── blink_fatigue.py    # 疲劳检测算法实现
├── app.py                  # 后端服务入口
├── package.json            # 前端依赖
└── requirements.txt        # 后端依赖
```

**模块职责**：
| 模块 | 主要职责 | 文件位置 | 关键功能 |
|------|----------|----------|----------|
| 前端入口 | 应用初始化与路由 | src/App.tsx | WebSocket连接管理 |
| 监测仪表盘 | 数据可视化与用户交互 | src/components/MonitoringDashboard.tsx | 展示疲劳状态和预警信息 |
| 数据服务 | 数据处理与状态管理 | src/services/dataService.ts | 模拟数据生成与状态管理 |
| WebSocket服务 | 实时数据通信 | src/services/websocketService.ts | 接收后端推送的实时数据 |
| 后端服务 | API与WebSocket处理 | app.py | 接收蓝牙数据，调用算法，推送结果 |
| 疲劳检测算法 | 信号处理与疲劳评估 | algorithm/blink_fatigue.py | 眨眼检测与疲劳程度评估 |

### 3.3 实时数据流与通信协议

**数据流**：
1. **数据采集**：通过蓝牙从硬件设备获取原始信号数据
2. **数据传输**：蓝牙数据 → 后端API（/api/bluetooth-data）
3. **数据处理**：后端接收数据 → 存储到缓冲区 → 调用算法处理
4. **结果计算**：算法处理原始信号 → 生成疲劳评估结果
5. **实时推送**：后端通过WebSocket推送评估结果到前端
6. **前端展示**：前端接收数据 → 更新UI展示

**通信协议**：
- **HTTP API**：
  - POST /api/bluetooth-data：接收蓝牙数据
  - GET /api/fatigue-latest：获取最新疲劳评估结果
  - GET /api/stats：获取数据统计信息
  - POST /api/clear-buffer：清空数据缓冲区
- **WebSocket**：
  - 路径：/ws
  - 消息类型：
    - hello：连接握手
    - ping/pong：心跳
    - bluetooth_data：原始蓝牙数据
    - fatigue：疲劳评估结果
    - stats：数据统计信息

**数据格式**：
- 蓝牙数据：`{rawData: number[], timestamp: number, signalQuality: number}`
- 疲劳评估结果：`{fatigueScore: number, fatigueLevel: string, blinkRate: number, avgBlinkDuration: number, ...}`

### 3.4 算法黑盒的输入输出映射

**算法函数**：`run_fatigue_pipeline`

**输入参数**：
| 参数 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| raw_signal | np.ndarray | 原始信号数据 | [0.1, 0.2, 0.3, ...] |
| sampling_rate | int | 采样率 | 100 |
| driving_time | string | 驾驶时长 | "1小时30分钟" |
| battery_level | number | 电池电量 | 80 |

**输出结果**：
| 字段 | 类型 | 描述 | 示例值 |
|------|------|------|--------|
| fatigueScore | number | 疲劳评分（0-100） | 65.0 |
| fatigueLevel | string | 疲劳等级 | "中度疲劳" |
| blinkRate | number | 眨眼频率（次/分钟） | 12.0 |
| avgBlinkDuration | number | 平均眨眼持续时间（毫秒） | 300.0 |
| eyeClosureRatio | number | 眼睛闭合比例（%） | 5.0 |
| longBlinkRatio | number | 长眨眼比例（%） | 15.0 |
| drivingTime | string | 驾驶时长 | "1小时30分钟" |
| alertLevel | string | 预警等级 | "警告" |

**算法流程**：
1. 信号预处理：滤波、归一化
2. 眨眼事件检测：基于阈值的眨眼检测
3. 疲劳指标计算：眨眼频率、持续时间、闭合比例等
4. 疲劳评估：基于多维度指标的综合评分
5. 预警生成：根据疲劳等级生成预警信息

### 3.5 启动流程与运行环境诊断

**启动流程**：
1. 前端：`npm run dev` → 启动Vite开发服务器
2. 后端：`python app.py` → 启动Flask服务

**运行环境**：
- **前端**：
  - Node.js 16+
  - npm 7+
  - 浏览器支持：Chrome, Firefox, Safari, Edge
- **后端**：
  - Python 3.8+
  - 依赖：Flask, Flask-CORS, Flask-Sock, NumPy

**端口配置**：
- 前端：默认3000端口（Vite开发服务器）
- 后端：3002端口（Flask服务）
- WebSocket：ws://localhost:3002/ws

**诊断命令**：
- 检查前端依赖：`npm install`
- 检查后端依赖：`pip install -r requirements.txt`
- 测试API：`curl http://localhost:3002/`
- 测试WebSocket：使用WebSocket客户端连接ws://localhost:3002/ws

## 4. 项目整合建议

### 4.1 架构整合方案

**统一前端架构**：
- 采用单一前端应用，通过路由切换不同功能模块
- 共享UI组件库和样式系统
- 统一WebSocket连接管理

**统一后端架构**：
- 采用微服务架构，每个功能模块作为独立服务
- 统一API网关，处理路由和认证
- 共享数据存储和消息队列

**统一数据采集**：
- 统一蓝牙数据采集接口
- 统一数据预处理流程
- 共享硬件设备管理

### 4.2 技术栈统一建议

**前端**：
- 统一使用React 18.3.1 + TypeScript
- 统一使用Vite作为构建工具
- 统一使用Radix UI组件库
- 统一使用recharts图表库

**后端**：
- 统一使用Python 3.8+和Flask框架
- 统一使用WebSocket进行实时通信
- 统一使用NumPy进行科学计算

**算法**：
- 统一信号预处理流程
- 统一特征提取方法
- 统一评估指标体系

### 4.3 数据流优化建议

**数据采集优化**：
- 实现蓝牙数据的批量采集和压缩传输
- 增加数据质量检测和异常处理
- 实现数据缓存和重连机制

**数据处理优化**：
- 采用异步处理模式，提高算法执行效率
- 实现数据并行处理，利用多核CPU资源
- 增加数据可视化和分析工具

**数据传输优化**：
- 实现WebSocket连接池管理
- 采用消息压缩和批量推送
- 实现数据同步和一致性保障

### 4.4 部署与监控建议

**部署方案**：
- 前端：使用Vercel或Netlify进行静态部署
- 后端：使用Docker容器化部署
- 数据库：使用MongoDB或PostgreSQL

**监控方案**：
- 实现系统健康检查和告警机制
- 建立性能监控和日志分析
- 实现用户行为分析和数据统计

**安全方案**：
- 实现HTTPS加密传输
- 建立API认证和授权机制
- 实现数据加密和隐私保护

## 5. 结论

通过对三个项目的深度分析，我们可以看到它们具有相似的架构和技术栈，主要区别在于算法实现和业务逻辑。通过整合这些项目，可以构建一个统一的健康监测平台，为用户提供全面的健康状态评估。

整合后的系统将具备以下优势：
1. **统一用户体验**：单一应用界面，统一的操作流程
2. **资源共享**：共享硬件设备、数据采集和处理资源
3. **功能互补**：三个监测功能相互补充，提供全面的健康评估
4. **技术统一**：统一的技术栈和架构，降低维护成本
5. **扩展性强**：模块化设计，便于添加新的监测功能

未来可以考虑添加更多健康监测功能，如心率监测、血压监测等，构建一个完整的健康监测生态系统。