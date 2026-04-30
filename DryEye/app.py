import json
import time
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

import numpy as np
from algorithm.dry_eye import run_dry_eye_pipeline

app = Flask(__name__)
CORS(app)
sock = Sock(app)


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


bluetooth_data = []
data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
}

DRY_EYE_WINDOW_SECONDS = 10
SAMPLING_RATE = 100
DRY_EYE_MIN_SAMPLES = SAMPLING_RATE * 3

dry_eye_signal_buffer = []
last_dry_eye_output = None

ws_clients = set()


def safe_ws_send(ws, payload: dict) -> bool:
    try:
        ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


@sock.route('/ws')
def ws_handler(ws):
    print("[WS] Client connected")
    ws_clients.add(ws)

    safe_ws_send(ws, {"type": "hello", "data": {"serverTime": datetime.utcnow().isoformat() + "Z"}})
    safe_ws_send(ws, {"type": "stats", "data": to_jsonable(data_stats)})

    if last_dry_eye_output is not None:
        safe_ws_send(ws, {"type": "dryEye", "data": to_jsonable(last_dry_eye_output)})

    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break
            try:
                obj = json.loads(msg)
                if isinstance(obj, dict) and obj.get("type") == "ping":
                    safe_ws_send(ws, {"type": "pong", "data": {"ts": int(time.time() * 1000)}})
                    continue
            except Exception:
                pass
    except Exception as e:
        print("[WS] Exception:", e)
    finally:
        ws_clients.discard(ws)
        print("[WS] Client disconnected")


def broadcast(payload: dict):
    dead = []
    for client in list(ws_clients):
        ok = safe_ws_send(client, payload)
        if not ok:
            dead.append(client)
    for c in dead:
        ws_clients.discard(c)


def broadcast_data(data_point):
    broadcast({"type": "bluetooth_data", "data": to_jsonable(data_point)})


def broadcast_dry_eye(dry_eye_output: dict):
    broadcast({"type": "dryEye", "data": to_jsonable(dry_eye_output)})


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
def receive_bluetooth_data():
    global bluetooth_data, data_stats, dry_eye_signal_buffer, last_dry_eye_output

    try:
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

        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[DATA] [{time_str}] Bluetooth data received #{data_stats['totalReceived']}")
        print(f"   Quality: {data_point['signalQuality']}% | Buffer: {len(bluetooth_data)} | Received: {data_point['receivedAt']}")

        if data_stats["totalReceived"] % 10 == 0:
            stats = calculate_stats()
            print("\n[STATS] (every 10):")
            print(f"   Total: {data_stats['totalReceived']}")
            print(f"   Avg Interval: {stats['averageInterval']}ms")
            print(f"   Range: [{stats['min']:.3f}, {stats['max']:.3f}]")
            print(f"   StdDev: {stats['stdDev']:.3f}")

        try:
            chunk = data_point["rawData"] or []
            chunk = [float(v) for v in chunk if isinstance(v, (int, float))]
            if chunk:
                dry_eye_signal_buffer.extend(chunk)

            max_len = int(DRY_EYE_WINDOW_SECONDS * SAMPLING_RATE)
            if len(dry_eye_signal_buffer) > max_len:
                dry_eye_signal_buffer = dry_eye_signal_buffer[-max_len:]

            if len(dry_eye_signal_buffer) >= DRY_EYE_MIN_SAMPLES:
                raw_np = np.asarray(dry_eye_signal_buffer, dtype=float)
                finite_mask = np.isfinite(raw_np)
                if not np.all(finite_mask):
                    raw_np = raw_np[finite_mask]

                if raw_np.size >= DRY_EYE_MIN_SAMPLES:
                    t0 = time.time()
                    dry_eye_output = run_dry_eye_pipeline(
                        raw_signal=raw_np,
                        sampling_rate=SAMPLING_RATE,
                        duration_sec=len(raw_np) / SAMPLING_RATE
                    )
                    dry_eye_output = to_jsonable(dry_eye_output)
                    last_dry_eye_output = dry_eye_output

                    broadcast_dry_eye(dry_eye_output)

                    dt_ms = (time.time() - t0) * 1000.0
                    print(
                        f"[ALGO] DRY EYE computed | n={raw_np.size} | cost={dt_ms:.1f}ms "
                        f"| riskScore={dry_eye_output.get('dryEyeRiskScore')} "
                        f"| blinkRate={dry_eye_output.get('blinkRate')}"
                    )
        except Exception as fe:
            print("[ALGO] Dry eye computation failed:", fe)

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
    global bluetooth_data, data_stats, dry_eye_signal_buffer, last_dry_eye_output
    cleared_count = len(bluetooth_data)
    bluetooth_data = []
    dry_eye_signal_buffer = []
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
    print(f"   WebSocket: ws://localhost:{PORT}/ws")
    print(f"   API (POST 数据): http://localhost:{PORT}/api/bluetooth-data")
    print(f"   API (GET 统计): http://localhost:{PORT}/api/stats")
    print(f"   API (POST 清空): http://localhost:{PORT}/api/clear-buffer")
    print("\n等待蓝牙数据...\n")

    # Flask 自带开发服务器（带 WebSocket 支持）
    app.run(host='0.0.0.0', port=PORT, debug=True)