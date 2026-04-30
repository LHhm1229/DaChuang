/*
// Node.js 後端服務 - 接收和顯示藍牙數據
const express = require('express');//Web框架（将URL路径映射到对应的处理函数等基本功能）
const cors = require('cors');//跨域
const WebSocket = require('ws');//WebSocket库，确保实时双向性
const http = require('http');//创建最基础的HTTP服务器
//创建服务器
const app = express();//创建一个 Express 应用实例，用来注册路由/中间件
const server = http.createServer(app);//用 Node 的 http 把 Express 应用包装成真正的 HTTP 服务器
const wss = new WebSocket.Server({ server });//基于 ws 库、复用同一个 HTTP 服务器创建 WebSocket 服务

// 中間件
app.use(cors());//允许所有网页来访问我这个服务器
app.use(express.json());//自动解析 JSON 请求数据

// WebSocket 数据存储
let bluetoothData = [];//缓冲区，存储蓝牙数据
let dataStats = {
  totalReceived: 0,
  lastUpdate: null,
  bufferSize: 0
};

// WebSocket 连接处理
wss.on('connection', (ws) => {
  console.log('🔗 前端客户端已连接');
  
  // 发送当前统计信息
  ws.send(JSON.stringify({
    type: 'stats',
    data: dataStats
  }));//使用 WebSocket 连接对象 ws 向前端发送一条消息     

  ws.on('close', () => {
    console.log('🔌 前端客户端已断开');
  });
});

// 广播蓝牙数据到所有连接的客户端
function broadcastData(data) {
  const message = JSON.stringify({
    type: 'bluetooth_data',
    data: data
  });
  
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

// 接收蓝牙数据的 API 端点
app.post('/api/bluetooth-data', (req, res) => {//定义POST接口
  try {
    const { rawData, timestamp, signalQuality, values } = req.body;//用 解构赋值 从 req.body 里取出前端传来的字段
    
    // 更新统计信息
    dataStats.totalReceived++;
    dataStats.lastUpdate = new Date().toISOString();
    dataStats.bufferSize = bluetoothData.length;
    
    // 把一条数据 标准化，变成统一格式的对象
    const dataPoint = {
      id: Date.now(),
      timestamp: timestamp || Date.now(),
      rawData: rawData || values || [],
      signalQuality: signalQuality || 0,
      receivedAt: new Date().toISOString()
    };
    
    // 添加到数据数组
    bluetoothData.push(dataPoint);
    
    // 保持数据数组大小（最近1000条）
    if (bluetoothData.length > 1000) {
      bluetoothData = bluetoothData.slice(-1000);//生成一个只包含最近 1000 条数据的新数组
    }
    
    // 在终端显示数据
    const timeStr = new Date().toLocaleTimeString("zh-CN");//让日志里带上清晰的时间戳
    console.log(`\n📡 [${timeStr}] 蓝牙数据接收 #${dataStats.totalReceived}`);           
    console.log(`   原始数据: [${dataPoint.rawData.map(v => v.toFixed(3)).join(', ')}]`);
    console.log(`   信号质量: ${dataPoint.signalQuality}%`);
    console.log(`   缓冲区大小: ${bluetoothData.length}`);
    console.log(`   接收时间: ${dataPoint.receivedAt}`);
    
    // 每10次接收显示统计信息
    if (dataStats.totalReceived % 10 === 0) {
      const stats = calculateStats();
      console.log(`\n📊 数据统计 (每10次):`);
      console.log(`   总接收次数: ${dataStats.totalReceived}`);
      console.log(`   平均间隔: ${stats.averageInterval}ms`);
      console.log(`   数据范围: [${stats.min.toFixed(3)}, ${stats.max.toFixed(3)}]`);
      console.log(`   标准差: ${stats.stdDev.toFixed(3)}`);
    }
    
    // 广播到前端
    broadcastData(dataPoint);
    
    res.json({ success: true, message: '数据接收成功' });
  } catch (error) {
    console.error('❌ 处理蓝牙数据失败:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// 获取数据统计的 API
app.get('/api/stats', (req, res) => {
  const stats = calculateStats();
  res.json({
    ...dataStats,
    ...stats
  });
});

// 清空数据缓冲区的 API
app.post('/api/clear-buffer', (req, res) => {
  const clearedCount = bluetoothData.length;
  bluetoothData = [];
  dataStats.bufferSize = 0;
  
  console.log(`🗑️ 数据缓冲区已清空，清除了 ${clearedCount} 条数据`);
  
  res.json({ 
    success: true, 
    message: `已清空 ${clearedCount} 条数据`,
    clearedCount 
  });
});

// 计算统计信息
function calculateStats() {
  if (bluetoothData.length === 0) {
    return {
      count: 0,
      mean: 0,
      stdDev: 0,
      min: 0,
      max: 0,
      averageInterval: 0
    };
  }
  
  // 計算數據統計
  const allValues = bluetoothData.flatMap(d => d.rawData);
  const mean = allValues.reduce((sum, val) => sum + val, 0) / allValues.length;
  const variance = allValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / allValues.length;
  const stdDev = Math.sqrt(variance);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  
    // 计算平均接收间隔
  let averageInterval = 0;
  if (bluetoothData.length > 1) {
    const intervals = [];
    for (let i = 1; i < bluetoothData.length; i++) {
      intervals.push(bluetoothData[i].timestamp - bluetoothData[i-1].timestamp);
    }
    averageInterval = intervals.reduce((sum, val) => sum + val, 0) / intervals.length;
  }
  
  return {
    count: bluetoothData.length,
    mean: Math.round(mean * 1000) / 1000,
    stdDev: Math.round(stdDev * 1000) / 1000,
    min: Math.round(min * 1000) / 1000,
    max: Math.round(max * 1000) / 1000,
    averageInterval: Math.round(averageInterval)
  };
}

// 启动服务器
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`🚀 后端服务已启动`);
  console.log(`   服务器地址: http://localhost:${PORT}`);
  console.log(`   WebSocket: ws://localhost:${PORT}`);
  console.log(`   蓝牙数据 API: http://localhost:${PORT}/api/bluetooth-data`);
  console.log(`   统计信息 API: http://localhost:${PORT}/api/stats`);
  console.log(`   清空缓冲区 API: http://localhost:${PORT}/api/clear-buffer`);
  console.log(`\n等待蓝牙数据...\n`);
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n🛑 正在关闭服务器...');
  server.close(() => {
    console.log('✅ 服务器已关闭');
    process.exit(0);
  });
});
