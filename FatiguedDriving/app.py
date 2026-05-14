import eventlet
eventlet.monkey_patch()

import json
import time
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import numpy as np
from algorithm.blink_fatigue import run_fatigue_pipeline
from algorithm.data_buffer import DataBuffer, BufferConfig

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, 
                   async_mode='eventlet',
                   ping_interval=25,
                   ping_timeout=120,
                   cors_allowed_origins="*")

# =========================
# 工具：确保输出可 JSON 序列化
# =========================
def to_jsonable(obj):
    import numpy as _np
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (_np.integer,)):
        return int(obj)
    if isinstance(obj, (_np.floating,)):
        return float(obj)
    if isinstance(obj, (_np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return str(obj)

# =========================
# 数据缓冲区（使用统一模块）
# =========================
FATIGUE_WINDOW_SECONDS = 30
CALIBRATION_DURATION_SECONDS = 6
SAMPLING_RATE = 100

data_buffer = DataBuffer(
    config=BufferConfig(
        max_size=1000,
        window_seconds=FATIGUE_WINDOW_SECONDS,
        sampling_rate=SAMPLING_RATE,
        min_samples=50  # 降低门槛，快速触发计算
    )
)

last_fatigue_output = None
start_driving_time = None

data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
}

# =========================
# WebSocket 连接处理
# =========================
@socketio.on('connect')
def handle_connect():
    print("[WS] 前端客户端已连接")
    emit('hello', {"serverTime": datetime.utcnow().isoformat() + "Z"})
    emit('stats', to_jsonable(data_stats))
    if last_fatigue_output is not None:
        emit('fatigue', to_jsonable(last_fatigue_output))

@socketio.on('disconnect')
def handle_disconnect():
    print("[WS] 前端客户端已断开")

@socketio.on('ping')
def handle_ping(data):
    emit('pong', {"ts": int(time.time() * 1000)})

# =========================
# 广播：蓝牙数据 / 疲劳结果
# =========================
def broadcast_data(data_point):
    socketio.emit('bluetooth_data', to_jsonable(data_point))

def broadcast_fatigue(fatigue_output: dict):
    socketio.emit('fatigue', to_jsonable(fatigue_output))

# =========================
# 统计信息
# =========================
def calculate_stats():
    if len(data_buffer.raw_buffer) == 0:
        return {"count": 0, "mean": 0, "stdDev": 0, "min": 0, "max": 0, "averageInterval": 0}

    all_values = [v for d in data_buffer.raw_buffer for v in d.get("rawData", [])]
    if not all_values:
        return {"count": len(data_buffer.raw_buffer), "mean": 0, "stdDev": 0, "min": 0, "max": 0, "averageInterval": 0}

    mean = sum(all_values) / len(all_values)
    variance = sum((val - mean) ** 2 for val in all_values) / len(all_values)
    std_dev = variance ** 0.5
    min_val = min(all_values)
    max_val = max(all_values)

    average_interval = 0
    if len(data_buffer.raw_buffer) > 1:
        intervals = []
        for i in range(1, len(data_buffer.raw_buffer)):
            intervals.append(data_buffer.raw_buffer[i]["timestamp"] - data_buffer.raw_buffer[i - 1]["timestamp"])
        if intervals:
            average_interval = sum(intervals) / len(intervals)

    return {
        "count": len(data_buffer.raw_buffer),
        "mean": round(mean, 3),
        "stdDev": round(std_dev, 3),
        "min": round(min_val, 3),
        "max": round(max_val, 3),
        "averageInterval": round(average_interval),
    }

# =========================
# 最新疲劳结果接口
# =========================
@app.route("/api/fatigue-latest", methods=["GET"])
def get_fatigue_latest():
    global last_fatigue_output
    if last_fatigue_output is None:
        return jsonify({"success": False, "data": None, "reason": "No fatigue output yet. Need enough samples."})
    return jsonify({"success": True, "data": to_jsonable(last_fatigue_output)})

# =========================
# 接收蓝牙数据
# =========================
@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Fatigue Monitoring Backend is Running", "time": datetime.now().isoformat()})

@app.route("/api/bluetooth-data", methods=["POST"])
@app.route("/api/bluetooth-data-fatigue", methods=["POST"])
def receive_bluetooth_data():
    global last_fatigue_output, start_driving_time
    print(f"[API] 收到数据请求: {request.method} {request.path}")

    try:
        if start_driving_time is None:
            start_driving_time = datetime.now()

        content_type = request.headers.get('Content-Type', '')
        print(f"[API] Content-Type: {content_type}")
        
        body = request.get_json(force=True, silent=False) or {}
        print(f"[API] 原始请求体: {json.dumps(body, ensure_ascii=False)[:500]}...")
        
        raw_data = body.get("rawData")
        timestamp = body.get("timestamp")
        signal_quality = body.get("signalQuality")
        values = body.get("values")

        # 调试：检查数据类型和格式
        print(f"[API] rawData 类型: {type(raw_data)}, 长度: {len(raw_data) if isinstance(raw_data, list) else 'N/A'}")
        print(f"[API] timestamp: {timestamp}")
        print(f"[API] signalQuality: {signal_quality}")
        print(f"[API] values 类型: {type(values)}, 长度: {len(values) if isinstance(values, list) else 'N/A'}")
        
        # 打印前几个数据点（如果有）
        if isinstance(raw_data, list) and len(raw_data) > 0:
            sample_count = min(5, len(raw_data))
            print(f"[API] rawData 前{sample_count}个样本: {raw_data[:sample_count]}")
        
        now_ts_ms = int(time.time() * 1000)
        data_point = {
            "id": now_ts_ms,
            "timestamp": timestamp if timestamp is not None else now_ts_ms,
            "rawData": raw_data if raw_data is not None else (values or []),
            "signalQuality": signal_quality if signal_quality is not None else 0,
            "receivedAt": datetime.utcnow().isoformat() + "Z",
        }

        # 使用统一缓冲区
        should_compute = data_buffer.add_data(data_point)
        
        # 打印缓冲区状态
        buffer_stats = data_buffer.get_stats()
        print(f"[API] 缓冲区状态: {json.dumps(buffer_stats, ensure_ascii=False)}")
        print(f"[API] 是否触发计算: {should_compute}")

        data_stats["totalReceived"] += 1
        data_stats["lastUpdate"] = datetime.utcnow().isoformat() + "Z"
        data_stats["bufferSize"] = len(data_buffer.raw_buffer)

        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[DATA] [{time_str}] 蓝牙数据接收 #{data_stats['totalReceived']}")
        print(f"   信号质量: {data_point['signalQuality']}% | 缓冲区: {len(data_buffer.raw_buffer)} | 接收: {data_point['receivedAt']}")

        if data_stats["totalReceived"] % 10 == 0:
            stats = calculate_stats()
            print("\n[STATS] 数据统计 (每10次):")
            print(f"   总接收次数: {data_stats['totalReceived']}")
            print(f"   平均间隔: {stats['averageInterval']}ms")
            print(f"   数据范围: [{stats['min']:.3f}, {stats['max']:.3f}]")
            print(f"   标准差: {stats['stdDev']:.3f}")

        # 疲劳算法：累积信号 + 定期评估
        try:
            if should_compute:
                raw_np = data_buffer.get_signal_array()
                finite_mask = np.isfinite(raw_np)
                if not np.all(finite_mask):
                    raw_np = raw_np[finite_mask]

                if raw_np.size >= data_buffer.config.min_samples:
                    t0 = time.time()
                    
                    driving_duration = datetime.now() - start_driving_time
                    total_seconds = int(driving_duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    driving_time_str = f"{hours}小时{minutes}分钟"
                    
                    print(f"[ALGO] 开始计算疲劳评分... 样本数: {raw_np.size}")
                    fatigue_output = run_fatigue_pipeline(
                        raw_signal=raw_np,
                        sampling_rate=SAMPLING_RATE,
                        driving_time=driving_time_str,
                        battery_level=None,
                        calibration_duration_sec=CALIBRATION_DURATION_SECONDS
                    )
                    fatigue_output = to_jsonable(fatigue_output)
                    last_fatigue_output = fatigue_output

                    broadcast_fatigue(fatigue_output)

                    dt_ms = (time.time() - t0) * 1000.0
                    print(
                        f"[ALGO] 疲劳计算完成 | 耗时={dt_ms:.1f}ms "
                        f"| 评分={fatigue_output.get('fatigueScore')} "
                        f"| 眨眼频率={fatigue_output.get('blinkRate')}"
                    )
                else:
                    print(f"[ALGO] 样本数不足，跳过计算: {raw_np.size}/{data_buffer.config.min_samples}")
        except Exception as fe:
            import traceback
            print("[ALGO] 疲劳算法计算失败：", fe)
            print(traceback.format_exc())

        broadcast_data(data_point)

        return jsonify({"success": True, "message": "数据接收成功"})

    except Exception as e:
        print("❌ 处理蓝牙数据失败:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# =========================
# 统计接口
# =========================
@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = calculate_stats()
    result = {**data_stats, **stats}
    return jsonify(to_jsonable(result))

# =========================
# 清空缓冲区
# =========================
@app.route("/api/clear-buffer", methods=["POST"])
def clear_buffer():
    global last_fatigue_output, start_driving_time
    cleared_count = len(data_buffer.raw_buffer)
    data_buffer.clear()
    last_fatigue_output = None
    start_driving_time = None
    data_stats["bufferSize"] = 0
    print(f"[BUFFER] 数据缓冲区已清空，清除了 {cleared_count} 条数据")
    return jsonify({"success": True, "message": f"已清空 {cleared_count} 条数据", "clearedCount": cleared_count})

if __name__ == "__main__":
    PORT = 3002
    print("[SERVER] 后端服务已启动")
    print(f"   HTTP:      http://localhost:{PORT}")
    print(f"   WebSocket: ws://localhost:{PORT}/socket.io/")
    print(f"   POST BT:   http://localhost:{PORT}/api/bluetooth-data")
    print(f"   GET stats: http://localhost:{PORT}/api/stats")
    print(f"   GET fat:   http://localhost:{PORT}/api/fatigue-latest")
    print(f"   clear:     http://localhost:{PORT}/api/clear-buffer\n")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=True)
