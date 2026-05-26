"""
持续重度疲劳模拟器 - 一直发送直到 Ctrl+C
模拟长时间闭眼/极度疲劳状态，疲劳评分持续维持在 70+ 区间
"""
import requests
import time
import numpy as np

SERVER_URL = "http://localhost:3002/api/bluetooth-data"
SAMPLING_RATE = 100

def make_severe_batch():
    """生成一批严重疲劳信号：高电压（眼睛闭合）+ 少量噪声"""
    base = 3.0  # 高电压 = 眼睑下垂/闭合
    noise = np.random.normal(0, 0.03, SAMPLING_RATE)
    return np.clip(base + noise, 0, 3.3).tolist()

print("=== 重度疲劳持续模拟器 ===")
print(f"目标服务器: {SERVER_URL}")
print("按 Ctrl+C 停止\n")

batch_count = 0
while True:
    batch = make_severe_batch()
    try:
        resp = requests.post(
            SERVER_URL,
            json={"rawData": batch, "timestamp": int(time.time() * 1000), "signalQuality": 95},
            timeout=3
        )
        batch_count += 1
        elapsed = batch_count * 1.0
        print(f"  [{batch_count:4d}] t={elapsed:6.0f}s | V={np.mean(batch):.3f}V | HTTP {resp.status_code}", end='\r')
    except requests.exceptions.ConnectionError:
        print(f"\n  [!] 连接失败 - 请确认后端已在 3002 端口启动")
        time.sleep(2)
    except KeyboardInterrupt:
        break
    time.sleep(1.0)

print(f"\n\n已停止，共发送 {batch_count} 批数据")
