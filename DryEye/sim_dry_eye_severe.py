"""
持续高度干眼风险模拟器 - 一直发送直到 Ctrl+C
模拟完全不眨眼状态（眼睛持续睁开）：
  - 信号近乎平坦（0.8V 基线 + 极小漂移噪声）
  - 算法检测不到眨眼事件 → blink_rate = 0
  - 算法兜底逻辑：blink_rate==0 → score = max(score, 90) → 高度干眼
"""
import requests
import time
import random
import numpy as np

API_URL = 'http://localhost:3000/api/bluetooth-data'
SAMPLING_RATE = 100
DURATION_SEC = 5  # 每批 5 秒

def generate_eyes_open_signal(duration_sec=5, sampling_rate=100):
    """
    低频正弦信号（0.2Hz）：
    - std ≈ 0.21 > 0.15，不触发算法的信号增强放大
    - 峰值 HWHM ≈ 167 个样本 > 算法 max_width=150，find_peaks 过滤掉
    - 结果：检测不到眨眼 → blink_rate=0 → 算法兜底 score ≥ 90
    """
    n = int(duration_sec * sampling_rate)
    t = np.linspace(0, duration_sec, n)
    slow_wave = 0.3 * np.sin(2 * np.pi * 0.2 * t)   # 0.2Hz，峰太宽无法被识别为眨眼
    noise = np.random.normal(0, 0.01, n)              # 少量高频噪声（低通后消除）
    signal = 0.5 + slow_wave + noise
    return np.clip(signal, 0.0, 1.0).tolist()

print("=== 高度干眼风险持续模拟器（低频正弦模式）===")
print(f"目标服务器: {API_URL}")
print("原理：0.2Hz 慢波 → 峰宽 >150 样本 → find_peaks 过滤 → blink_rate=0 → 评分 ≥ 90")
print("按 Ctrl+C 停止\n")

batch_count = 0
try:
    while True:
        signal = generate_eyes_open_signal(DURATION_SEC, SAMPLING_RATE)
        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 96)
        }
        try:
            resp = requests.post(API_URL, json=payload, timeout=3)
            batch_count += 1
            elapsed = batch_count * DURATION_SEC
            status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
            print(f"  [{batch_count:4d}] t={elapsed:4d}s | 持续睁眼无眨眼 | {status}", end='\r')
        except requests.exceptions.ConnectionError:
            print(f"\n  [!] 连接失败 - 请确认后端已在 3000 端口启动")
            time.sleep(2)
        time.sleep(DURATION_SEC)
except KeyboardInterrupt:
    pass

print(f"\n\n已停止，共发送 {batch_count} 批数据")
