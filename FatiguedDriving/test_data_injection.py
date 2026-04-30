import time
import json
import random
import urllib.request
import urllib.error
from datetime import datetime
import math

# 配置
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
        print("请确保 'start-flask-dev.bat' 正在运行且后端未报错。")
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
    
    for i in range(num_samples):
        # 基础噪声
        noise = random.uniform(-0.05, 0.05)
        
        if state == "normal":
            # 正常状态：偶尔眨眼（低频，短时）
            if random.random() > 0.99: 
                val = 0.8 + noise # 眨眼峰值
            else:
                val = 0.1 + noise # 睁眼基线
                
        elif state == "fatigue":
            # 疲劳状态：频繁眨眼，且有长闭眼
            if random.random() > 0.90: 
                val = 0.9 + noise # 频繁眨眼/闭眼
            else:
                val = 0.2 + noise # 即使睁眼也可能不完全
                
        elif state == "poor_signal":
            # 信号差：大幅随机波动
            val = random.uniform(0, 1.0)
            
        else:
            val = 0.0
            
        values.append(val)
    
    return values

def run_test():
    print("🚀 开始数据传输测试...")
    print(f"🎯 目标地址: {API_URL}")
    print("-" * 50)

    scenarios = [
        {"name": "🟢 阶段一：正常驾驶 (清醒)", "state": "normal", "duration": 30, "quality": 95, "desc": "预期：疲劳分 < 30，状态良好"},
        {"name": "🔴 阶段二：疲劳模拟 (闭眼)", "state": "fatigue", "duration": 30, "quality": 90, "desc": "预期：疲劳分 > 70，触发警报"},
        {"name": "⚠️ 阶段三：信号不稳定", "state": "poor_signal", "duration": 15, "quality": 30, "desc": "预期：信号质量变红，数据波动"},
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']} - 持续 {scenario['duration']} 秒")
        print(f"   {scenario['desc']}")
        start_time = time.time()
        
        while time.time() - start_time < scenario['duration']:
            # 模拟每 200ms 发送一次数据包 (5Hz 发包率，每次包含 20 个采样点 = 100Hz 采样率)
            chunk = generate_signal_chunk(0.2, 100, scenario['state'])
            
            payload = {
                "rawData": chunk,
                "timestamp": int(time.time() * 1000),
                "signalQuality": max(0, min(100, scenario['quality'] + random.randint(-5, 5))),
                "values": chunk # 兼容字段
            }
            
            success = send_data(payload)
            if success:
                print(".", end="", flush=True)
            else:
                print("x", end="", flush=True)
                
            time.sleep(0.2) # 等待 200ms
        print(" [完成]")

    print("\n" + "-" * 50)
    print("✅ 测试结束！请检查前端 UI 是否正确响应了以上三个阶段的变化。")

if __name__ == "__main__":
    if check_server():
        run_test()