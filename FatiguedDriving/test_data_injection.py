import time
import json
import random
import urllib.request
import urllib.error
from datetime import datetime
import math

# 配置 - 疲劳驾驶后端端口
API_URL = "http://127.0.0.1:3002/api/bluetooth-data"
ROOT_URL = "http://127.0.0.1:3002/"
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
    
    # 状态追踪
    in_blink = False
    blink_duration = 0
    in_long_close = False
    long_close_duration = 0
    in_slow_blink = False
    slow_blink_duration = 0
    
    # 眨眼持续时间（样本数）
    normal_blink_length = int(0.1 * sampling_rate)     # 100ms
    slow_blink_length = int(0.4 * sampling_rate)       # 400ms 慢速眨眼
    long_close_length = int(2.0 * sampling_rate)       # 2秒长闭眼
    
    for i in range(num_samples):
        noise = random.uniform(-0.02, 0.02)
        
        if state == "normal":
            # 正常状态：清醒，低频眨眼（约12次/分钟），眨眼时间短
            # 眨眼概率约 0.002 每样本 ≈ 12次/分钟
            if not in_blink and random.random() > 0.998:
                in_blink = True
                blink_duration = 0
            
            if in_blink:
                blink_duration += 1
                if blink_duration <= normal_blink_length:
                    val = 0.85 + noise  # 眨眼峰值
                else:
                    in_blink = False
                    val = 0.05 + noise  # 低基线表示睁眼
            else:
                val = 0.05 + noise  # 稳定低基线
                
        elif state == "fatigue":
            # 疲劳状态：符合算法预期的疲劳特征
            # 算法期望：疲劳时眨眼频率降低，但闭眼时间显著增加
            # 1. 长时间闭眼状态（最关键的疲劳指标）
            if in_long_close:
                long_close_duration += 1
                if long_close_duration <= long_close_length:
                    val = 0.98 + noise  # 非常高的值表示深度闭眼
                else:
                    in_long_close = False
                    long_close_duration = 0
                    val = 0.15 + noise
            # 2. 慢速长眨眼（很少，但持续时间很长）
            elif in_slow_blink:
                slow_blink_duration += 1
                if slow_blink_duration <= slow_blink_length:
                    val = 0.95 + noise  # 眨眼峰值更高
                else:
                    in_slow_blink = False
                    slow_blink_duration = 0
                    # 长眨眼后极可能进入长时间闭眼
                    if random.random() > 0.1:
                        in_long_close = True
                        long_close_duration = 0
                    val = 0.15 + noise
            # 3. 触发新的长眨眼（低频，但每次持续时间长）
            elif not in_blink and random.random() > 0.995:
                in_slow_blink = True
                slow_blink_duration = 0
                val = 0.95 + noise
            # 4. 基线状态（大部分时间是半闭合或闭眼状态）
            else:
                # 极高概率进入长时间闭眼（每0.2秒约50%概率）
                if random.random() > 0.98:
                    in_long_close = True
                    long_close_duration = 0
                    val = 0.98 + noise
                else:
                    # 基线非常高，表示眼皮沉重，接近半闭合状态
                    val = 0.55 + noise  # 高基线表示严重眼皮沉重
                    
        elif state == "poor_signal":
            # 信号不稳定：大幅随机波动，质量差
            # 使用更大的噪声和突然跳变
            if random.random() > 0.92:
                # 频繁大幅跳变
                val = random.uniform(0, 1.0)
            else:
                # 持续的大幅波动，无规律
                val = random.uniform(0, 1.0)
            
        else:
            val = 0.0
            
        values.append(max(0.0, min(1.0, val)))  # 限制在[0,1]范围
    
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