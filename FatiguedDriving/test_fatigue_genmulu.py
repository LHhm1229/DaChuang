import numpy as np
import requests
import time
import json

API_URL = "http://localhost:3002/api/bluetooth-data"
FATIGUE_LATEST_URL = "http://localhost:3002/api/fatigue-latest"
CLEAR_BUFFER_URL = "http://localhost:3002/api/clear-buffer"


def generate_eyelid_signal(fs=100, duration_sec=30, fatigue_level="awake"):
    """
    生成模拟眼睑传感器信号，不同疲劳状态有不同特征
    
    信号语义：高值=闭眼/眨眼峰，低值=睁眼
    """
    t = np.linspace(0, duration_sec, duration_sec * fs)
    signal = np.full_like(t, 0.2)  # 基础值代表睁眼状态（低值）
    
    if fatigue_level == "awake":
        # 清醒：正常眨眼
        blink_rate_per_min = 20
        blink_duration_ms = 150
        amplitude = 0.7
    elif fatigue_level == "mild":
        # 轻度疲劳：眨眼频率略降，持续略长
        blink_rate_per_min = 14
        blink_duration_ms = 200
        amplitude = 0.65
    elif fatigue_level == "moderate":
        # 中度疲劳：眨眼频率明显下降，长眨眼增多，眼闭合比例增加
        blink_rate_per_min = 8
        blink_duration_ms = 350
        amplitude = 0.6
    elif fatigue_level == "severe":
        # 严重疲劳：很少眨眼，长时间闭眼，眼闭合比例很高
        blink_rate_per_min = 2
        blink_duration_ms = 600
        amplitude = 0.5
    else:
        blink_rate_per_min = 20
        blink_duration_ms = 150
        amplitude = 0.7
    
    blink_rate = blink_rate_per_min / 60
    blink_duration_samples = int(blink_duration_ms * fs / 1000)
    
    for i in range(int(duration_sec * blink_rate)):
        start_t = i / blink_rate + np.random.uniform(-0.1, 0.1)
        start_idx = int(start_t * fs)
        end_idx = start_idx + blink_duration_samples
        
        if start_idx >= 0 and end_idx <= len(signal) and end_idx > start_idx:
            blink_samples = end_idx - start_idx
            progress = np.linspace(0, 1, blink_samples)
            
            rising = progress < 0.25
            holding = (progress >= 0.25) & (progress < 0.75)
            falling = progress >= 0.75
            
            blink_wave = np.zeros(blink_samples)
            blink_wave[rising] = 0.2 + amplitude * (progress[rising] / 0.25)
            blink_wave[holding] = 0.2 + amplitude
            blink_wave[falling] = 0.2 + amplitude * (1 - (progress[falling] - 0.75) / 0.25)
            
            signal[start_idx:end_idx] = blink_wave
    
    # 添加噪声
    signal += np.random.normal(0, 0.02, len(signal))
    
    # 涓ラ噸鐤插姵鏃舵坊鍔犻暱鏃堕棿闂溂鍖洪棿锛?0绉掞級
    if fatigue_level == "severe":
        long_close_start = int(duration_sec * fs * 0.3)
        long_close_end = long_close_start + int(10 * fs)
        if long_close_end <= len(signal):
            signal[long_close_start:long_close_end] = 0.85 + np.random.normal(0, 0.02, long_close_end - long_close_start)
    
    # 中度疲劳时添加一个较长的闭眼区间（1.5秒）
    if fatigue_level == "moderate":
        long_close_start = int(duration_sec * fs * 0.5)
        long_close_end = long_close_start + int(1.5 * fs)
        if long_close_end <= len(signal):
            signal[long_close_start:long_close_end] = 0.75 + np.random.normal(0, 0.02, long_close_end - long_close_start)
    
    return signal.tolist()


def send_batch(raw_data, batch_id, signal_quality=95):
    payload = {
        "rawData": raw_data,
        "timestamp": int(time.time() * 1000),
        "signalQuality": signal_quality,
        "values": raw_data
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def test_fatigue_pipeline():
    print("=" * 70)
    print("[Fatigue Driving] Multi-State Backend Test")
    print("=" * 70)
    
    test_states = [
        ("awake", "清醒状态"),
        ("mild", "轻度疲劳"),
        ("moderate", "中度疲劳"),
        ("severe", "严重疲劳")
    ]
    
    for fatigue_code, fatigue_name in test_states:
        print(f"\n{'='*70}")
        print("测试状态: " + fatigue_name)
        print("=" * 70)
        
        print("\n>>> 清除缓冲区...")
        try:
            requests.get(CLEAR_BUFFER_URL, timeout=3)
            print("    缓冲区已清除")
        except Exception as e:
            print("    清除缓冲区失败: " + str(e))
        
        print("\n>>> 生成 " + fatigue_name + " 的模拟信号 (30秒)...")
        signal = generate_eyelid_signal(fs=100, duration_sec=30, fatigue_level=fatigue_code)
        print("    信号长度: " + str(len(signal)) + " 采样点")
        
        print("\n>>> 一次性发送全部数据 (" + str(len(signal)) + " 采样点)...")
        print("-" * 70)
        
        result = send_batch(signal, batch_id=1)
        ts = time.strftime("%H:%M:%S")
        
        if "error" in result:
            print("  [" + ts + "] [失败] 错误: " + result["error"])
        else:
            print("  [" + ts + "] [成功] 已发送 " + str(len(signal)) + " 采样点")
        
        print("-" * 70)
        print("\n>>> 等待算法处理...")
        time.sleep(3)
        
        print("\n>>> 查询 " + fatigue_name + " 对应的疲劳检测结果:")
        try:
            resp = requests.get(FATIGUE_LATEST_URL, timeout=5)
            result = resp.json()
            if result["success"]:
                data = result["data"]
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("\n结果摘要:")
                print("   疲劳评分: " + str(data.get("fatigueScore", "N/A")))
                print("   疲劳等级: " + str(data.get("fatigueLevel", "N/A")))
                print("   眨眼频率: " + str(data.get("blinkRate", "N/A")) + " 次/分钟")
                print("   眼闭合比例: " + str(data.get("eyelidStatus", {}).get("eyeClosureRatio", "N/A")) + "%")
                print("   告警级别: " + str(data.get("alertLevel", "N/A")))
            else:
                print("   [失败] " + result["reason"])
        except Exception as e:
            print("   [失败] 查询失败: " + str(e))
        
        if fatigue_code != "severe":
            print("\n>>> 等待5秒进入下一状态测试...")
            time.sleep(5)
    
    print("\n" + "=" * 70)
    print("[完成] 疲劳驾驶多状态测试结束")
    print("=" * 70)


if __name__ == "__main__":
    test_fatigue_pipeline()