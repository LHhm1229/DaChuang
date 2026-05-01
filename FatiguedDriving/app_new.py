"""
app.py - 疲劳驾驶监测后端 (端口3002)
基于《新项目数据传输方案与设计思路》标准化重构
- 统一缓冲区管理 (DataBuffer)
- 安全WebSocket广播与心跳机制 (DataBroadcaster)
- 数据与UI完全解耦
"""

import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock

import numpy as np
from algorithm.blink_fatigue import run_fatigue_pipeline
from algorithm.data_buffer import DataBuffer, BufferConfig, DataBroadcaster

app = Flask(__name__)
CORS(app)
sock = Sock(app)


def to_jsonable(obj):
    """确保输出可JSON序列化"""
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
# 缓冲区与广播器初始化
# =========================
buffer_config = BufferConfig(
    max_size=1000,           # 原始数据缓冲区容量
    window_seconds=30,        # 计算窗口30秒
    sampling_rate=100,       # 100Hz采样
    min_samples=300          # 最少3秒数据启动计算
)

data_buffer = DataBuffer(buffer_config)
broadcaster = DataBroadcaster()

# 驾驶开始时间
start_driving_time = None

# 最新算法输出（用于连接时立即推送）
last_fatigue_output = None

# 数据统计
data_stats = {
    "totalReceived": 0,
    "lastUpdate": None,
    "bufferSize": 0,
    "computeCount": 0
}


# =========================
# WebSocket 连接处理
# =========================
@sock.route("/ws")
def ws_handler(ws):
    """WebSocket连接处理器 - 集成心跳机制"""
    print(f"[WS] 客户端已连接 | 时间: {datetime.now().strftime('%H:%M:%S')}")
    broadcaster.add_client(ws)

    # 连接握手
    broadcaster.safe_send(ws, {
        "type": "hello",
        "data": {
            "serverTime": datetime.utcnow().isoformat() + "Z",
            "module": "fatigue",
            "port": 3002
        }
    })

    # 推送当前统计
    broadcaster.safe_send(ws, {
        "type": "stats",
        "data": to_jsonable(data_stats)
    })

    # 如果已有结果，立即推送（让UI尽快显示）
    global last_fatigue_output
    if last_fatigue_output is not None:
        broadcaster.safe_send(ws, {
            "type": "fatigue",
            "data": to_jsonable(last_fatigue_output)
        })

    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break

            try:
                obj = json.loads(msg)
                msg_type = obj.get("type")

                if msg_type == "ping":
                    # 心跳响应
                    broadcaster.safe_send(ws, {
                        "type": "pong",
                        "data": {"ts": int(time.time() * 1000)}
                    })
                    broadcaster.update_heartbeat()

                elif msg_type == "getStats":
                    # 主动获取统计
                    broadcaster.safe_send(ws, {
                        "type": "stats",
                        "data": to_jsonable(data_stats)
                    })

                elif msg_type == "getLatest":
                    # 主动获取最新结果
                    if last_fatigue_output is not None:
                        broadcaster.safe_send(ws, {
                            "type": "fatigue",
                            "data": to_jsonable(last_fatigue_output)
                        })

            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"[WS] 连接异常: {e}")
    finally:
        broadcaster.remove_client(ws)
        print(f"[WS] 客户端已断开 | 剩余连接: {broadcaster.get_client_count()}")


# =========================
# HTTP API 接口
# =========================
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Fatigue Monitoring Backend (端口3002)",
        "time": datetime.now().isoformat(),
        "module": "fatigue"
    })


@app.route("/api/bluetooth-data", methods=["POST"])
def receive_bluetooth_data():
    """
    接收传感器数据 - 标准化入口
    基于老方案的数据接收与异步处理模式
    """
    global last_fatigue_output, start_driving_time

    try:
        # 记录驾驶开始时间
        if start_driving_time is None:
            start_driving_time = datetime.now()

        # 1. 数据接收与标准化
        body = request.get_json(force=True, silent=False) or {}
        raw_data = body.get("rawData")
        timestamp = body.get("timestamp")
        signal_quality = body.get("signalQuality")

        now_ts_ms = int(time.time() * 1000)
        data_point = {
            "id": now_ts_ms,
            "timestamp": timestamp if timestamp is not None else now_ts_ms,
            "rawData": raw_data if raw_data is not None else body.get("values", []),
            "signalQuality": signal_quality if signal_quality is not None else 0,
            "receivedAt": datetime.utcnow().isoformat() + "Z",
        }

        # 2. 添加到缓冲区（触发计算检查）
        should_compute = data_buffer.add_data(data_point)

        # 3. 更新统计
        data_stats["totalReceived"] += 1
        data_stats["lastUpdate"] = datetime.utcnow().isoformat() + "Z"
        data_stats["bufferSize"] = data_buffer.get_stats()["signal_buffer_size"]

        # 4. 日志输出（每10次）
        if data_stats["totalReceived"] % 10 == 0:
            stats = data_buffer.get_stats()
            print(f"\n[STATS] #{data_stats['totalReceived']} | "
                  f"缓冲: {stats['signal_buffer_size']}/{buffer_config.window_seconds * buffer_config.sampling_rate} "
                  f"({stats['buffer_fill_ratio']}%) | "
                  f"可计算: {stats['can_compute']}")

        # 5. 算法计算（非阻塞）
        if should_compute and data_buffer.can_compute():
            try:
                raw_np = data_buffer.get_signal_array()

                # 计算驾驶时长
                driving_duration = datetime.now() - start_driving_time
                total_seconds = int(driving_duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                driving_time_str = f"{hours}小时{minutes}分钟"

                # 执行算法
                t0 = time.time()
                fatigue_output = run_fatigue_pipeline(
                    raw_signal=raw_np,
                    sampling_rate=buffer_config.sampling_rate,
                    driving_time=driving_time_str,
                    battery_level=None
                )
                fatigue_output = to_jsonable(fatigue_output)
                last_fatigue_output = fatigue_output

                # 更新计算计数
                data_stats["computeCount"] = data_buffer.compute_count

                # 广播到所有客户端
                broadcaster.broadcast({
                    "type": "fatigue",
                    "data": fatigue_output
                })

                dt_ms = (time.time() - t0) * 1000.0
                print(f"[ALGO] 疲劳计算完成 | 耗时: {dt_ms:.1f}ms | "
                      f"评分: {fatigue_output.get('fatigueScore')} | "
                      f"眨眼率: {fatigue_output.get('blinkRate')}/min")

            except Exception as fe:
                print(f"[ALGO] 疲劳算法计算失败: {fe}")

        # 6. 广播原始数据（可选，用于调试）
        broadcaster.broadcast({
            "type": "data",
            "data": to_jsonable(data_point)
        })

        return jsonify({"success": True, "message": "数据接收成功"})

    except Exception as e:
        print(f"[DATA] 处理蓝牙数据失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fatigue-latest", methods=["GET"])
def get_fatigue_latest():
    """获取最新疲劳结果"""
    global last_fatigue_output
    if last_fatigue_output is None:
        return jsonify({
            "success": False,
            "data": None,
            "reason": "暂无疲劳数据，需要足够的样本才能计算"
        })
    return jsonify({"success": True, "data": to_jsonable(last_fatigue_output)})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取数据统计信息"""
    stats = data_buffer.get_stats()
    return jsonify(to_jsonable({**data_stats, **stats}))


@app.route("/api/buffer/clear", methods=["POST"])
def clear_buffer():
    """清空缓冲区"""
    global last_fatigue_output, start_driving_time

    cleared_count = len(data_buffer.raw_buffer)
    data_buffer.clear()
    last_fatigue_output = None
    start_driving_time = None

    # 重置统计
    data_stats["totalReceived"] = 0
    data_stats["bufferSize"] = 0
    data_stats["computeCount"] = 0

    print(f"[BUFFER] 已清空 | 清除数据点: {cleared_count}")

    return jsonify({
        "success": True,
        "message": f"已清空 {cleared_count} 条数据",
        "clearedCount": cleared_count
    })


# =========================
# 启动服务器
# =========================
if __name__ == "__main__":
    PORT = 3002
    print("=" * 60)
    print(f"[SERVER] 疲劳驾驶监测后端启动 | 端口: {PORT}")
    print("=" * 60)
    print(f"  HTTP API:      http://localhost:{PORT}")
    print(f"  WebSocket:     ws://localhost:{PORT}/ws")
    print(f"  数据接收:      POST http://localhost:{PORT}/api/bluetooth-data")
    print(f"  最新结果:      GET  http://localhost:{PORT}/api/fatigue-latest")
    print(f"  数据统计:      GET  http://localhost:{PORT}/api/stats")
    print(f"  清空缓冲:      POST http://localhost:{PORT}/api/buffer/clear")
    print()
    print(f"[CONFIG] 缓冲区配置:")
    print(f"  窗口大小:      {buffer_config.window_seconds}秒")
    print(f"  采样率:        {buffer_config.sampling_rate}Hz")
    print(f"  最小样本:      {buffer_config.min_samples}个 ({buffer_config.min_samples/buffer_config.sampling_rate}秒)")
    print(f"  最大缓冲:      {buffer_config.max_size}条")
    print("=" * 60)

    app.run(host="0.0.0.0", port=PORT, debug=True)