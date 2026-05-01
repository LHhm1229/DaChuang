import time
import json
import random
import urllib.request
import urllib.error
from datetime import datetime
import math

API_URL = "http://127.0.0.1:3001/api/bluetooth-data"
ROOT_URL = "http://127.0.0.1:3001/"
HEADERS = {'Content-Type': 'application/json'}


def check_server():
    try:
        print(f"🔍 正在检查后端服务: {ROOT_URL}")
        with urllib.request.urlopen(ROOT_URL, timeout=2) as response:
            if response.status == 200:
                print("✅ 后端服务连接成功！")
                return True
    except urllib.error.URLError as e:
        print(f"❌ 无法连接后端服务: {e}")
        print("请确保睡眠质量后端正在运行 (python app.py)。")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


def send_data(payload):
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(API_URL, data=data, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        print(f"\n❌ 发送失败: HTTP {e.code} {e.reason}")
        try:
            print(f"   服务器返回: {e.read().decode('utf-8')}")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"\n❌ 连接失败: {e.reason}")
        return False


def generate_signal_chunk(duration_sec, sampling_rate, state="normal"):
    """生成一段模拟的眼电信号数据"""
    num_samples = int(duration_sec * sampling_rate)
    values = []
    
    if state == "wake":
        for i in range(num_samples):
            noise = random.uniform(-0.02, 0.02)
            if random.random() > 0.98:
                val = 0.85 + noise
            else:
                val = 0.15 + noise
            values.append(max(0.0, min(1.0, val)))
    
    elif state == "deep":
        for i in range(num_samples):
            val = 0.5 + 0.01 * random.random()
            values.append(max(0.0, min(1.0, val)))
    
    elif state == "light":
        for i in range(num_samples):
            noise = random.uniform(-0.1, 0.1)
            val = 0.5 + noise
            values.append(max(0.0, min(1.0, val)))
    
    elif state == "rem":
        t = [i / sampling_rate for i in range(num_samples)]
        for i in range(num_samples):
            rem_osc = 0.15 * math.sin(2 * math.pi * 1.5 * t[i])
            val = 0.5 + rem_osc + 0.02 * random.random()
            values.append(max(0.0, min(1.0, val)))
    
    elif state == "poor_signal":
        for i in range(num_samples):
            val = random.uniform(0, 1.0)
            values.append(val)
    
    else:
        for i in range(num_samples):
            values.append(0.5)
    
    return values


def run_test():
    print("🚀 开始睡眠质量数据传输测试...")
    print(f"🎯 目标地址: {API_URL}")
    print("-" * 50)

    scenarios = [
        {"name": "🟡 阶段一：清醒状态", "state": "wake", "duration": 20, "quality": 95, "desc": "预期：阶段=清醒(0)，质量分中等"},
        {"name": "🔵 阶段二：深睡状态", "state": "deep", "duration": 20, "quality": 90, "desc": "预期：阶段=深睡(3)，质量分较高"},
        {"name": "🟢 阶段三：浅睡状态", "state": "light", "duration": 20, "quality": 85, "desc": "预期：阶段=浅睡(2)，质量分中等"},
        {"name": "🟣 阶段四：REM状态", "state": "rem", "duration": 20, "quality": 90, "desc": "预期：阶段=REM(4)，质量分较高"},
        {"name": "⚠️ 阶段五：信号不稳定", "state": "poor_signal", "duration": 10, "quality": 30, "desc": "预期：信号质量变红，数据波动"},
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']} - 持续 {scenario['duration']} 秒")
        print(f"   {scenario['desc']}")
        start_time = time.time()
        
        while time.time() - start_time < scenario['duration']:
            chunk = generate_signal_chunk(0.2, 100, scenario['state'])
            
            payload = {
                "rawData": chunk,
                "timestamp": int(time.time() * 1000),
                "signalQuality": max(0, min(100, scenario['quality'] + random.randint(-5, 5))),
                "values": chunk
            }
            
            success = send_data(payload)
            if success:
                print(".", end="", flush=True)
            else:
                print("x", end="", flush=True)
                
            time.sleep(0.2)
        print(" [完成]")

    print("\n" + "-" * 50)
    print("✅ 测试结束！请检查前端 UI 是否正确响应了以上阶段的变化。")


if __name__ == "__main__":
    if check_server():
        run_test()
