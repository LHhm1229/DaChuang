# 健康与生理状态实时监测系统

## 项目简介

本项目是一个一体化的健康与生理状态实时监测系统，整合了干眼症监测、睡眠质量检测和疲劳驾驶预警三个功能模块。系统采用现代前端技术栈和玻璃态设计，提供美观、高效的用户界面。

## 技术栈

- **前端**：React 18.2.0 + TypeScript + Vite + Tailwind CSS
- **UI组件**：自定义玻璃态组件 + Radix UI
- **数据可视化**：Recharts
- **图标**：Lucide React
- **后端**：Python Flask（三个独立服务）
- **通信**：WebSocket + RESTful API

## 项目结构

```
HealthMonitoringSystem/
├── src/
│   ├── components/          # 组件目录
│   │   ├── ui/             # 玻璃态UI组件
│   │   ├── Gateway.tsx     # 网关首页
│   │   └── UnifiedBentoDashboard.tsx  # 统一仪表盘
│   ├── services/           # 服务层
│   │   └── dataService.ts  # 数据服务
│   ├── styles/             # 样式文件
│   │   └── globals.css     # 全局样式
│   ├── App.tsx             # 应用入口
│   └── main.tsx            # 主入口
├── package.json            # 项目配置
├── vite.config.ts          # Vite配置
└── tailwind.config.js      # Tailwind配置
```

## 功能模块

### 1. 干眼症监测
- 实时监测眨眼频率和眼部状态
- 评估干眼风险
- 提供详细的眼部健康数据

### 2. 睡眠质量检测
- 分析睡眠阶段和眼动情况
- 评估睡眠质量
- 提供睡眠质量评分和建议

### 3. 疲劳驾驶预警
- 监测驾驶过程中的疲劳状态
- 及时发出预警
- 提供疲劳程度评估

## 系统特点

- **视觉美学**：采用玻璃态设计和便当盒网格布局，具有现代科技感
- **动态主题**：根据不同模块自动切换主题色，提供沉浸式体验
- **实时数据**：通过WebSocket实现实时数据推送和展示
- **性能优化**：使用React.memo和数据防抖，确保动画丝滑不卡顿
- **统一架构**：三个模块共享同一套代码库，维护成本低

## 启动指南

### 1. 安装依赖

```bash
# 在HealthMonitoringSystem目录下运行
npm install
```

### 2. 启动前端开发服务器

```bash
npm run dev
```

### 3. 启动后端服务

- **干眼症监测**：运行 `DryEye/app.py`（端口3000）
- **睡眠质量检测**：运行 `SleepQuality/app.py`（端口3001）
- **疲劳驾驶预警**：运行 `FatiguedDriving/app.py`（端口3002）

### 4. 访问系统

打开浏览器，访问 `http://localhost:5173`，选择要监测的模块，开始实时监测。

## 环境要求

- **前端**：Node.js 16+，npm 7+
- **后端**：Python 3.8+，Flask 3.0.3+
- **浏览器**：Chrome, Firefox, Safari, Edge

## 注意事项

- 确保三个后端服务都已启动，并且端口配置正确
- 系统默认使用模拟数据，实际部署时需要连接真实的硬件设备
- 如需修改后端服务端口，需要同时更新 `vite.config.ts` 中的代理配置

## 许可证

MIT License
