#!/usr/bin/env python3
"""
蓝牙数据格式测试脚本
用于测试三个模块（疲劳驾驶、干眼症、睡眠质量）的数据传输格式
"""

import requests
import time
import random
import math

# 服务端口配置
PORTS = {
    'fatigue': 3002,
    'dry-eye': 3000,
    'sleep': 3001
}

def generate_eye_signal(duration_sec=5, sampling_rate=100, eye_openness=0.8, perclos=0.1):
    """生成眼部信号数据（用于疲劳驾驶和干眼症）"""
    num_samples = int(duration_sec * sampling_rate)
    values = []
    for i in range(num_samples):
        t = i / sampling_rate
        if random.random() < perclos / 10:
            eye_openness_current = 0.2 + 0.1 * random.random()
        else:
            eye_openness_current = eye_openness + random.uniform(-0.05, 0.05)
        base_signal = eye_openness_current + 0.02 * math.sin(2 * math.pi * 0.5 * t)
        noise = random.uniform(-0.01, 0.01)
        val = base_signal + noise
        values.append(max(0.0, min(1.0, val)))
    return values

def generate_sleep_signal(duration_sec=5, sampling_rate=100):
    """生成睡眠信号数据"""
    num_samples = int(duration_sec * sampling_rate)
    values = []
    for i in range(num_samples):
        t = i / sampling_rate
        # 模拟睡眠阶段的变化
        base_value = 0.3 + 0.4 * math.sin(2 * math.pi * 0.1 * t)
        noise = random.uniform(-0.05, 0.05)
        values.append(max(0.0, min(1.0, base_value + noise)))
    return values

def test_module(module_name: str):
    """测试指定模块"""
    port = PORTS.get(module_name)
    if not port:
        print(f"❌ 未知模块: {module_name}")
        return
    
    url = f'http://localhost:{port}/api/bluetooth-data'
    print(f"\n{'='*60}")
    print(f"测试模块: {module_name}")
    print(f"目标地址: {url}")
    print(f"{'='*60}")
    
    try:
        # 根据模块生成对应数据
        if module_name == 'sleep':
            raw_data = generate_sleep_signal()
        else:
            raw_data = generate_eye_signal()
        
        payload = {
            'rawData': raw_data,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 100)
        }
        
        print(f"📤 发送数据:")
        print(f"   - rawData 长度: {len(raw_data)}")
        print(f"   - 前5个样本: {[round(v, 3) for v in raw_data[:5]]}")
        print(f"   - timestamp: {payload['timestamp']}")
        print(f"   - signalQuality: {payload['signalQuality']}%")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ 发送成功! 状态码: {response.status_code}")
            try:
                result = response.json()
                print(f"📥 响应: {result}")
            except:
                print(f"📥 响应: {response.text[:200]}")
        else:
            print(f"❌ 发送失败! 状态码: {response.status_code}")
            print(f"   错误信息: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败! 请确保 {module_name} 服务已启动在端口 {port}")
    except Exception as e:
        print(f"❌ 发送异常: {str(e)}")

def main():
    print("蓝牙数据格式测试脚本")
    print("="*60)
    
    while True:
        print("\n选择要测试的模块:")
        print("1. 疲劳驾驶 (fatigue)")
        print("2. 干眼症 (dry-eye)")
        print("3. 睡眠质量 (sleep)")
        print("4. 测试所有模块")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ")
        
        if choice == '1':
            test_module('fatigue')
        elif choice == '2':
            test_module('dry-eye')
        elif choice == '3':
            test_module('sleep')
        elif choice == '4':
            for module in ['fatigue', 'dry-eye', 'sleep']:
                test_module(module)
                time.sleep(1)
        elif choice == '5':
            print("退出测试...")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    main()
