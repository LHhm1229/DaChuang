import json
import time
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import numpy as np
from algorithm.blink_fatigue import run_fatigue_pipeline

app = Flask(__name__)
CORS(app)  # 允许所有来源跨域
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

# WebSocket 数据存储
bluetooth_data = []  # 缓冲区，存储蓝牙数据
start_driving_time = None  # 驾驶开始时间

# =========================
# 疲劳算法计算缓冲（窗口）
# =========================
FATIGUE_WINDOW_SECONDS = 30  # 使用30秒窗口进行评估
SAMPLING_RATE = 100
FATIGUE_MIN_SAMPLES = SAMPLING_RATE * 3  # 最少 3 秒数据就开始算

fatigue_signal_buffer = []
last_fatigue_output = None

data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
}

# 记录当前所有 WebSocket 连接
ws_clients = set()

# =========================
# WebSocket 连接处理
# =========================
@socketio.on('connect')
def handle_connect():
    print("[WS] 前端客户端已连接")
    emit('hello', {"type": "hello", "data": {"serverTime": datetime.utcnow().isoformat() + "Z"}})
    emit('stats', {"type": "stats", "data": to_jsonable(data_stats)})
    if last_fatigue_output is not None:
        emit('fatigue', {"type": "fatigue", "data": to_jsonable(last_fatigue_output)})

@socketio.on('disconnect')
def handle_disconnect():
    print("[WS] 前端客户端已断开")

@socketio.on('ping')
def handle_ping(data):
    emit('pong', {"type": "pong", "data": {"ts": int(time.time() * 1000)}})

# =========================
# 广播：蓝牙数据 / 疲劳结果
# =========================
def broadcast_data(data_point):
    socketio.emit('bluetooth_data', {"type": "bluetooth_data", "data": to_jsonable(data_point)})

def broadcast_fatigue(fatigue_output: dict):
    socketio.emit('fatigue', {"type": "fatigue", "data": to_jsonable(fatigue_output)})

# =========================
# 统计信息
# =========================
def calculate_stats():
    if len(bluetooth_data) == 0:
        return {"count": 0, "mean": 0, "stdDev": 0, "min": 0, "max": 0, "averageInterval": 0}

    all_values = [v for d in bluetooth_data for v in d.get("rawData", [])]
    if not all_values:
        return {"count": len(bluetooth_data), "mean": 0, "stdDev": 0, "min": 0, "max": 0, "averageInterval": 0}

    mean = sum(all_values) / len(all_values)
    variance = sum((val - mean) ** 2 for val in all_values) / len(all_values)
    std_dev = variance ** 0.5
    min_val = min(all_values)
    max_val = max(all_values)

    average_interval = 0
    if len(bluetooth_data) > 1:
        intervals = []
        for i in range(1, len(bluetooth_data)):
            intervals.append(bluetooth_data[i]["timestamp"] - bluetooth_data[i - 1]["timestamp"])
        if intervals:
            average_interval = sum(intervals) / len(intervals)

    return {
        "count": len(bluetooth_data),
        "mean": round(mean, 3),
        "stdDev": round(std_dev, 3),
        "min": round(min_val, 3),
        "max": round(max_val, 3),
        "averageInterval": round(average_interval),
    }

# =========================
# 最新疲劳结果接口（验收备用）
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
def receive_bluetooth_data():
    global bluetooth_data, data_stats, fatigue_signal_buffer, last_fatigue_output, start_driving_time
    print(f"[API] 收到数据请求: {request.method} {request.path}")

    try:
        if start_driving_time is None:
            start_driving_time = datetime.now()

        body = request.get_json(force=True, silent=False) or {}
        raw_data = body.get("rawData")
        timestamp = body.get("timestamp")
        signal_quality = body.get("signalQuality")
        values = body.get("values")

        now_ts_ms = int(time.time() * 1000)
        data_point = {
            "id": now_ts_ms,
            "timestamp": timestamp if timestamp is not None else now_ts_ms,
            "rawData": raw_data if raw_data is not None else (values or []),
            "signalQuality": signal_quality if signal_quality is not None else 0,
            "receivedAt": datetime.utcnow().isoformat() + "Z",
        }

        bluetooth_data.append(data_point)
        if len(bluetooth_data) > 1000:
            bluetooth_data = bluetooth_data[-1000:]

        data_stats["totalReceived"] += 1
        data_stats["lastUpdate"] = datetime.utcnow().isoformat() + "Z"
        data_stats["bufferSize"] = len(bluetooth_data)

        # 终端日志
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[DATA] [{time_str}] 蓝牙数据接收 #{data_stats['totalReceived']}")
        print(f"   信号质量: {data_point['signalQuality']}% | 缓冲区: {len(bluetooth_data)} | 接收: {data_point['receivedAt']}")

        # 每 10 次打印统计
        if data_stats["totalReceived"] % 10 == 0:
            stats = calculate_stats()
            print("\n[STATS] 数据统计 (每10次):")
            print(f"   总接收次数: {data_stats['totalReceived']}")
            print(f"   平均间隔: {stats['averageInterval']}ms")
            print(f"   数据范围: [{stats['min']:.3f}, {stats['max']:.3f}]")
            print(f"   标准差: {stats['stdDev']:.3f}")

        # =========================
        # 疲劳算法：累积信号 + 定期评估
        # =========================
        try:
            chunk = data_point["rawData"] or []
            chunk = [float(v) for v in chunk if isinstance(v, (int, float))]
            if chunk:
                fatigue_signal_buffer.extend(chunk)

            max_len = int(FATIGUE_WINDOW_SECONDS * SAMPLING_RATE)
            if len(fatigue_signal_buffer) > max_len:
                fatigue_signal_buffer = fatigue_signal_buffer[-max_len:]

            if len(fatigue_signal_buffer) >= FATIGUE_MIN_SAMPLES:
                raw_np = np.asarray(fatigue_signal_buffer, dtype=float)
                finite_mask = np.isfinite(raw_np)
                if not np.all(finite_mask):
                    raw_np = raw_np[finite_mask]

                if raw_np.size >= FATIGUE_MIN_SAMPLES:
                    t0 = time.time()
                    
                    # 计算驾驶时长
                    driving_duration = datetime.now() - start_driving_time
                    total_seconds = int(driving_duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    driving_time_str = f"{hours}小时{minutes}分钟"
                    
                    fatigue_output = run_fatigue_pipeline(
                        raw_signal=raw_np,
                        sampling_rate=SAMPLING_RATE,
                        driving_time=driving_time_str,
                        battery_level=None
                    )
                    fatigue_output = to_jsonable(fatigue_output)
                    last_fatigue_output = fatigue_output

                    # ✅ 关键：推给前端（让 UI 变）
                    broadcast_fatigue(fatigue_output)

                    dt_ms = (time.time() - t0) * 1000.0
                    print(
                        f"[ALGO] FATIGUE computed | n={raw_np.size} | cost={dt_ms:.1f}ms "
                        f"| score={fatigue_output.get('fatigueScore')} "
                        f"| blinkRate={fatigue_output.get('blinkRate')}"
                    )
        except Exception as fe:
            print("[ALGO] 疲劳算法计算失败：", fe)

        # 推送原始蓝牙数据（可用于前端显示信号质量/连接活跃）
        broadcast_data(data_point)

        # 也可以顺便推一次 stats（可选；不想太频繁可以改为每N次推）
        # broadcast({"type": "stats", "data": to_jsonable(data_stats)})

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
    global bluetooth_data, data_stats, fatigue_signal_buffer, last_fatigue_output, start_driving_time
    cleared_count = len(bluetooth_data)
    bluetooth_data = []
    fatigue_signal_buffer = []
    last_fatigue_output = None
    start_driving_time = None
    data_stats["bufferSize"] = 0
    print(f"[BUFFER] 数据缓冲区已清空，清除了 {cleared_count} 条数据（并清空 fatigue buffer）")
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
