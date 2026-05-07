import json
import time
from datetime import datetime

import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import numpy as np
from algorithm.dry_eye import run_dry_eye_pipeline
from algorithm.data_buffer import DataBuffer, BufferConfig

app = Flask(__name__)
CORS(app, origins="*")

socketio = SocketIO(app, 
                   async_mode='eventlet',
                   ping_interval=25,
                   ping_timeout=120,
                   cors_allowed_origins="*")

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
DRY_EYE_WINDOW_SECONDS = 10
SAMPLING_RATE = 100

data_buffer = DataBuffer(
    config=BufferConfig(
        max_size=1000,
        window_seconds=DRY_EYE_WINDOW_SECONDS,
        sampling_rate=SAMPLING_RATE,
        min_samples=50
    )
)

last_dry_eye_output = None

data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
}

@socketio.on('connect')
def handle_connect():
    print("[WS] Client connected")
    emit('hello', {"type": "hello", "data": {"serverTime": datetime.utcnow().isoformat() + "Z"}})
    emit('stats', {"type": "stats", "data": to_jsonable(data_stats)})
    if last_dry_eye_output is not None:
        emit('dryEye', to_jsonable(last_dry_eye_output))

@socketio.on('disconnect')
def handle_disconnect():
    print("[WS] Client disconnected")

@socketio.on('ping')
def handle_ping(data):
    emit('pong', {"type": "pong", "data": {"ts": int(time.time() * 1000)}})

def broadcast_dry_eye(dry_eye_output: dict):
    socketio.emit('dryEye', to_jsonable(dry_eye_output))
    try:
        client_count = len(socketio.server.manager.rooms.get('/', {}))
    except Exception:
        client_count = 'unknown'
    print(f"[WS] Broadcast dryEye data to {client_count} clients")

def broadcast_data(data_point):
    socketio.emit('bluetooth_data', {"type": "bluetooth_data", "data": to_jsonable(data_point)})

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

@app.route("/api/dry-eye-latest", methods=["GET"])
def get_dry_eye_latest():
    global last_dry_eye_output
    if last_dry_eye_output is None:
        return jsonify({"success": False, "data": None, "reason": "No dry eye output yet. Need enough samples."})
    return jsonify({"success": True, "data": to_jsonable(last_dry_eye_output)})

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Dry Eye Monitoring Backend is Running", "time": datetime.now().isoformat()})

@app.route('/api/bluetooth-data', methods=['POST'])
@app.route('/api/bluetooth-data-dry-eye', methods=['POST'])
def receive_bluetooth_data():
    global last_dry_eye_output

    try:
        content_type = request.headers.get('Content-Type', '')
        print(f"[API] Content-Type: {content_type}")
        
        body = request.get_json(force=True, silent=False) or {}
        print(f"[API] Raw body: {json.dumps(body, ensure_ascii=False)[:500]}...")
        
        raw_data = body.get("rawData")
        timestamp = body.get("timestamp")
        signal_quality = body.get("signalQuality")
        values = body.get("values")

        print(f"[API] rawData type: {type(raw_data)}, length: {len(raw_data) if isinstance(raw_data, list) else 'N/A'}")
        print(f"[API] timestamp: {timestamp}")
        print(f"[API] signalQuality: {signal_quality}")
        print(f"[API] values type: {type(values)}, length: {len(values) if isinstance(values, list) else 'N/A'}")
        
        if isinstance(raw_data, list) and len(raw_data) > 0:
            sample_count = min(5, len(raw_data))
            print(f"[API] rawData first {sample_count} samples: {raw_data[:sample_count]}")

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

        data_stats["totalReceived"] += 1
        data_stats["lastUpdate"] = datetime.utcnow().isoformat() + "Z"
        data_stats["bufferSize"] = len(data_buffer.raw_buffer)

        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[DATA] [{time_str}] Bluetooth data received #{data_stats['totalReceived']}")
        print(f"   Quality: {data_point['signalQuality']}% | Buffer: {len(data_buffer.raw_buffer)} | Received: {data_point['receivedAt']}")
        print(f"   RawData length: {len(data_point['rawData'])}")

        if data_stats["totalReceived"] % 10 == 0:
            stats = calculate_stats()
            print("\n[STATS] (every 10):")
            print(f"   Total: {data_stats['totalReceived']}")
            print(f"   Avg Interval: {stats['averageInterval']}ms")
            print(f"   Range: [{stats['min']:.3f}, {stats['max']:.3f}]")
            print(f"   StdDev: {stats['stdDev']:.3f}")

        try:
            if should_compute:
                raw_np = data_buffer.get_signal_array()
                finite_mask = np.isfinite(raw_np)
                if not np.all(finite_mask):
                    print(f"[ALGO] Found {len(raw_np) - np.sum(finite_mask)} invalid samples, filtered")
                    raw_np = raw_np[finite_mask]

                if raw_np.size >= data_buffer.config.min_samples:
                    t0 = time.time()
                    dry_eye_output = run_dry_eye_pipeline(
                        raw_signal=raw_np,
                        sampling_rate=SAMPLING_RATE,
                        duration_sec=len(raw_np) / SAMPLING_RATE
                    )
                    dry_eye_output = to_jsonable(dry_eye_output)
                    last_dry_eye_output = dry_eye_output

                    print(f"[ALGO] Compute success | riskScore={dry_eye_output.get('dryEyeRiskScore')} | blinkRate={dry_eye_output.get('blinkRate')}")
                    
                    eventlet.sleep(0.005)
                    broadcast_dry_eye(dry_eye_output)

                    dt_ms = (time.time() - t0) * 1000.0
                    print(
                        f"[ALGO] DRY EYE computed | n={raw_np.size} | cost={dt_ms:.1f}ms "
                        f"| riskScore={dry_eye_output.get('dryEyeRiskScore')} "
                        f"| blinkRate={dry_eye_output.get('blinkRate')} "
                        f"| incompleteRatio={dry_eye_output.get('incompleteBlinkRatio')} "
                        f"| longBlinkRatio={dry_eye_output.get('longBlinkRatio')}"
                    )
                else:
                    print(f"[ALGO] Not enough valid samples: {raw_np.size}/{data_buffer.config.min_samples}")
            else:
                print(f"[ALGO] Waiting for more samples: {len(data_buffer.signal_buffer)}/{data_buffer.config.min_samples}")
        except Exception as fe:
            import traceback
            print(f"[ALGO] Computation failed: {fe}")
            print(f"[ALGO] Stack trace:\n{traceback.format_exc()}")

        broadcast_data(data_point)

        return jsonify({"success": True, "message": "Data received successfully"})

    except Exception as e:
        print("[DATA] Error processing bluetooth data:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = calculate_stats()
    result = {**data_stats, **stats}
    return jsonify(to_jsonable(result))

@app.route("/api/clear-buffer", methods=["POST"])
def clear_buffer():
    global last_dry_eye_output
    cleared_count = len(data_buffer.raw_buffer)
    data_buffer.clear()
    last_dry_eye_output = None
    data_stats["bufferSize"] = 0

    print(f"[BUFFER] Cleared {cleared_count} items from buffer")

    return jsonify({
        "success": True,
        "message": f"Cleared {cleared_count} items",
        "clearedCount": cleared_count,
    })

if __name__ == '__main__':
    PORT = 3000
    print("[服务器] 干眼症后端服务启动中...")
    print(f"   访问地址: http://localhost:{PORT}")
    print(f"   WebSocket: http://localhost:{PORT}/socket.io")
    print(f"   API (POST 数据): http://localhost:{PORT}/api/bluetooth-data")
    print(f"   API (GET 统计): http://localhost:{PORT}/api/stats")
    print(f"   API (POST 清空): http://localhost:{PORT}/api/clear-buffer")
    print("\n等待蓝牙数据...\n")

    socketio.run(app, host='0.0.0.0', port=PORT, debug=True)
