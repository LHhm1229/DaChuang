# 健康监测系统 - Health Monitoring System

> 基于蓝牙硬件的多模态健康监测平台，集成干眼症检测、睡眠质量评估和疲劳驾驶预警三大功能模块。

## 🏥 项目概述

本项目是一个完整的端到端健康监测系统，实现了从**蓝牙硬件数据采集**到**实时UI展示**的全链路数据流转。

**核心功能模块：**

| 模块         | 端口   | 功能描述           |
| ---------- | ---- | -------------- |
| **干眼症监测**  | 3000 | 基于眼动信号的干眼症风险评估 |
| **睡眠质量检测** | 3001 | 睡眠阶段分析与质量评分    |
| **疲劳驾驶预警** | 3002 | 实时驾驶疲劳监测与预警    |

## 🛠️ 技术栈

### 前端技术栈

- **框架**: React 18.3.1 + TypeScript
- **构建工具**: Vite 6.3.5
- **UI组件**: Radix UI
- **图表库**: Recharts
- **实时通信**: Socket.IO Client
- **样式**: Tailwind CSS 3

### 后端技术栈

- **框架**: Flask 3.0.3
- **实时通信**: Flask-Sock / Socket.IO
- **科学计算**: NumPy 2.4.4, SciPy 1.17.1
- **跨域支持**: Flask-CORS

### 通信协议

- **HTTP API**: RESTful接口用于数据上传
- **WebSocket**: 实时数据推送

## 📁 项目结构

```
DaChuang/
├── HealthMonitoringSystem/    # 统一前端应用
│   ├── src/
│   │   ├── components/       # UI组件
│   │   │   ├── ui/           # 基础UI组件
│   │   │   ├── BluetoothControl.tsx   # 蓝牙控制组件
│   │   │   ├── Gateway.tsx            # 首页入口
│   │   │   └── UnifiedBentoDashboard.tsx  # 统一仪表盘
│   │   ├── hooks/            # 自定义Hooks
│   │   │   └── useDynamicWebSocket.ts # WebSocket管理
│   │   ├── services/         # 服务层
│   │   │   ├── bluetoothService.ts    # 蓝牙服务
│   │   │   ├── dataMapper.ts          # 数据映射层
│   │   │   └── dataService.ts         # 数据服务
│   │   ├── styles/           # 全局样式
│   │   ├── App.tsx           # 应用主入口
│   │   └── main.tsx          # React入口
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts        # Vite配置（含代理）
│   └── tailwind.config.js    # Tailwind配置
├── DryEye/                   # 干眼症检测后端
│   ├── algorithm/
│   │   ├── dry_eye.py        # 干眼症算法
│   │   └── data_buffer.py    # 数据缓冲区
│   ├── app.py                # Flask服务入口
│   └── requirements.txt
├── SleepQuality/             # 睡眠质量检测后端
│   ├── algorithm/
│   │   ├── sleep_quality.py  # 睡眠算法
│   │   └── data_buffer.py
│   ├── app.py
│   └── requirements.txt
├── FatiguedDriving/          # 疲劳驾驶预警后端
│   ├── algorithm/
│   │   ├── blink_fatigue.py  # 疲劳算法
│   │   └── data_buffer.py
│   ├── app.py
│   └── requirements.txt
├── Firmware/                 # 硬件固件相关
└── README.md                 # 项目说明文档
```

## 🚀 快速开始

### 环境要求

- **Node.js**: 16+
- **Python**: 3.8+
- **npm**: 7+

### 启动步骤

**1. 安装前端依赖**

```bash
cd HealthMonitoringSystem
npm install
```

**2. 安装后端依赖（每个模块）**

```bash
# 干眼症模块
cd DryEye
pip install -r requirements.txt

# 睡眠质量模块
cd SleepQuality
pip install -r requirements.txt

# 疲劳驾驶模块
cd FatiguedDriving
pip install -r requirements.txt
```

**3. 启动后端服务（需要3个终端窗口）**

```bash
# 终端1 - 干眼症服务 (端口3000)
cd DryEye
python app.py

# 终端2 - 睡眠质量服务 (端口3001)
cd SleepQuality
python app.py

# 终端3 - 疲劳驾驶服务 (端口3002)
cd FatiguedDriving
python app.py
```

**4. 启动前端开发服务器**

```bash
cd HealthMonitoringSystem
npm run dev
```

**5. 访问应用**
打开浏览器访问: <http://localhost:5173>

## 🔄 数据流架构

```
蓝牙硬件 → 前端蓝牙服务 → HTTP POST → 后端API → 算法处理 → WebSocket推送 → 前端UI
              │                                              │
              └─────────────────────── 数据缓冲区 ────────────┘
```

### 数据流程详解

1. **数据采集**: 前端通过Web Bluetooth API获取硬件数据
2. **数据传输**: 蓝牙数据通过HTTP POST发送到对应后端模块
3. **数据处理**: 后端将数据存入缓冲区，累积到一定量后触发算法计算
4. **结果推送**: 算法处理完成后，通过WebSocket实时推送结果到前端
5. **UI展示**: 前端接收数据并更新仪表盘展示

### API接口

| 接口                    | 方法   | 模块   | 描述     |
| --------------------- | ---- | ---- | ------ |
| `/api/bluetooth-data` | POST | 所有模块 | 接收蓝牙数据 |
| `/`                   | GET  | 所有模块 | 健康检查   |
| `/api/stats`          | GET  | 所有模块 | 获取统计信息 |

### WebSocket消息类型

| 消息类型             | 描述       |
| ---------------- | -------- |
| `hello`          | 连接握手     |
| `dryEye`         | 干眼症评估结果  |
| `sleepQuality`   | 睡眠质量评估结果 |
| `fatigue`        | 疲劳评估结果   |
| `bluetooth_data` | 原始蓝牙数据回显 |
| `ping/pong`      | 心跳检测     |

## 📊 功能模块

### 1. 干眼症监测

- **核心指标**: 眨眼频率、平均眨眼时长、眼睛闭合比例、不完全眨眼比例
- **风险评估**: 基于多维度指标的干眼症风险评分（0-100）

### 2. 睡眠质量检测

- **核心指标**: 睡眠效率、REM密度、睡眠阶段分布
- **阶段识别**: Wake/N1/N2/N3/REM五个睡眠阶段

### 3. 疲劳驾驶预警

- **核心指标**: 疲劳评分、眨眼频率、平均眨眼时长、预警等级
- **实时预警**: 根据疲劳程度自动生成预警信息

## 🔧 配置说明

### Vite代理配置

前端通过Vite代理实现跨域请求，配置位于 `vite.config.ts`:

```typescript
proxy: {
  '/api/bluetooth-data': { target: 'http://localhost:3000' },      // 干眼症
  '/api/bluetooth-data-sleep': { target: 'http://localhost:3001' }, // 睡眠
  '/api/bluetooth-data-fatigue': { target: 'http://localhost:3002' }, // 疲劳
  '/ws/dry-eye': { target: 'ws://localhost:3000', ws: true },
  '/ws/sleep': { target: 'ws://localhost:3001', ws: true },
  '/ws/fatigue': { target: 'ws://localhost:3002', ws: true },
}
```

### 端口分配

| 服务      | 端口   | 协议             |
| ------- | ---- | -------------- |
| 前端开发服务器 | 5173 | HTTP           |
| 干眼症后端   | 3000 | HTTP/WebSocket |
| 睡眠质量后端  | 3001 | HTTP/WebSocket |
| 疲劳驾驶后端  | 3002 | HTTP/WebSocket |

## 🎯 使用指南

1. **启动应用**: 按上述步骤启动所有服务
2. **连接蓝牙**: 点击页面蓝牙图标，选择设备进行连接
3. **选择模块**: 在首页点击对应模块进入监测界面
4. **查看数据**: 等待蓝牙数据流入，实时查看评估结果

## 🔍 故障排查

##

诊断命令

```bash
# 检查端口占用
netstat -ano | findstr ":3000 :3001 :3002 :5173"

# 测试API
curl http://localhost:3000/
curl http://localhost:3001/
curl http://localhost:3002/

# 查看Python进程
Get-Process -Name python
```

## 📝 开发说明

### 代码规范

- TypeScript代码遵循ESLint规则
- Python代码遵循PEP8规范
- 提交信息使用约定式提交格式

### 扩展开发

如需添加新的健康监测模块：

1. 在 `HealthMonitoringSystem/src/App.tsx` 中添加模块配置
2. 创建新的后端服务目录（参考现有模块结构）
3. 在 `vite.config.ts` 中添加代理配置
4. 在 `dataMapper.ts` 中添加数据映射函数

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和PR！

***

*项目维护中*
