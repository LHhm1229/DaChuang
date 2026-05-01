import json
import time
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

import numpy as np
from algorithm.sleep_quality import run_sleep_quality_pipeline

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
start_sleep_time = None

SLEEP_WINDOW_SECONDS = 30
SAMPLING_RATE = 100
SLEEP_MIN_SAMPLES = SAMPLING_RATE * 3

sleep_signal_buffer = []
last_sleep_output = None

data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
}

ws_clients = set()


def safe_ws_send(ws, payload: dict) -> bool:
    try:
        ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


@sock.route("/ws")
def ws_handler(ws):
    print("[WS] 前端客户端已连接")
    ws_clients.add(ws)

    safe_ws_send(ws, {"type": "hello", "data": {"serverTime": datetime.utcnow().isoformat() + "Z"}})
    safe_ws_send(ws, {"type": "stats", "data": to_jsonable(data_stats)})

    if last_sleep_output is not None:
        safe_ws_send(ws, {"type": "sleepQuality", "data": to_jsonable(last_sleep_output)})

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
        print("WebSocket 连接异常：", e)
    finally:
        ws_clients.discard(ws)
        print("[WS] 前端客户端已断开")


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


def broadcast_sleep_quality(sleep_output: dict):
    broadcast({"type": "sleepQuality", "data": to_jsonable(sleep_output)})


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


@app.route("/api/sleep-quality-latest", methods=["GET"])
def get_sleep_quality_latest():
    global last_sleep_output
    if last_sleep_output is None:
        return jsonify({"success": False, "data": None, "reason": "No sleep quality output yet. Need enough samples."})
    return jsonify({"success": True, "data": to_jsonable(last_sleep_output)})


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Sleep Quality Monitoring Backend is Running", "time": datetime.now().isoformat()})


@app.route("/api/bluetooth-data", methods=["POST"])
def receive_bluetooth_data():
    global bluetooth_data, data_stats, sleep_signal_buffer, last_sleep_output, start_sleep_time
    print(f"[API] 收到数据请求: {request.method} {request.path}")

    try:
        if start_sleep_time is None:
            start_sleep_time = datetime.now()

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
        print(f"\n[DATA] [{time_str}] 蓝牙数据接收 #{data_stats['totalReceived']}")
        print(f"   信号质量: {data_point['signalQuality']}% | 缓冲区: {len(bluetooth_data)} | 接收: {data_point['receivedAt']}")

        if data_stats["totalReceived"] % 10 == 0:
            stats = calculate_stats()
            print("\n[STATS] 数据统计 (每10次):")
            print(f"   总接收次数: {data_stats['totalReceived']}")
            print(f"   平均间隔: {stats['averageInterval']}ms")
            print(f"   数据范围: [{stats['min']:.3f}, {stats['max']:.3f}]")
            print(f"   标准差: {stats['stdDev']:.3f}")

        try:
            chunk = data_point["rawData"] or []
            chunk = [float(v) for v in chunk if isinstance(v, (int, float))]
            if chunk:
                sleep_signal_buffer.extend(chunk)

            max_len = int(SLEEP_WINDOW_SECONDS * SAMPLING_RATE)
            if len(sleep_signal_buffer) > max_len:
                sleep_signal_buffer = sleep_signal_buffer[-max_len:]

            if len(sleep_signal_buffer) >= SLEEP_MIN_SAMPLES:
                raw_np = np.asarray(sleep_signal_buffer, dtype=float)
                finite_mask = np.isfinite(raw_np)
                if not np.all(finite_mask):
                    raw_np = raw_np[finite_mask]

                if raw_np.size >= SLEEP_MIN_SAMPLES:
                    t0 = time.time()

                    sleep_duration = datetime.now() - start_sleep_time
                    total_seconds = int(sleep_duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    sleep_time_str = f"{hours}小时{minutes}分钟"

                    sleep_output = run_sleep_quality_pipeline(
                        raw_signal=raw_np,
                        sampling_rate=SAMPLING_RATE
                    )
                    sleep_output = to_jsonable(sleep_output)
                    last_sleep_output = sleep_output

                    broadcast_sleep_quality(sleep_output)

                    dt_ms = (time.time() - t0) * 1000.0
                    print(
                        f"[ALGO] SLEEP computed | n={raw_np.size} | cost={dt_ms:.1f}ms "
                        f"| score={sleep_output.get('qualityScore')} "
                        f"| stage={sleep_output.get('currentStageName')}"
                    )
        except Exception as fe:
            print("[ALGO] 睡眠质量算法计算失败：", fe)

        broadcast_data(data_point)

        return jsonify({"success": True, "message": "数据接收成功"})

    except Exception as e:
        print("❌ 处理蓝牙数据失败:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    stats = calculate_stats()
    result = {**data_stats, **stats}
    return jsonify(to_jsonable(result))


@app.route("/api/clear-buffer", methods=["POST"])
def clear_buffer():
    global bluetooth_data, data_stats, sleep_signal_buffer, last_sleep_output, start_sleep_time
    cleared_count = len(bluetooth_data)
    bluetooth_data = []
    sleep_signal_buffer = []
    last_sleep_output = None
    start_sleep_time = None
    data_stats["bufferSize"] = 0
    print(f"[BUFFER] 数据缓冲区已清空，清除了 {cleared_count} 条数据")
    return jsonify({"success": True, "message": f"已清空 {cleared_count} 条数据", "clearedCount": cleared_count})


if __name__ == "__main__":
    PORT = 3001
    print("[SERVER] 睡眠质量后端服务已启动")
    print(f"   HTTP:      http://localhost:{PORT}")
    print(f"   WebSocket: ws://localhost:{PORT}/ws")
    print(f"   POST BT:   http://localhost:{PORT}/api/bluetooth-data")
    print(f"   GET stats: http://localhost:{PORT}/api/stats")
    print(f"   GET sleep: http://localhost:{PORT}/api/sleep-quality-latest")
    print(f"   clear:     http://localhost:{PORT}/api/clear-buffer\n")
    app.run(host="0.0.0.0", port=PORT, debug=True)