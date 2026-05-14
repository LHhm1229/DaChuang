"""
蓝牙数据模拟器
用于测试疲劳驾驶算法对不同电压变化的响应
"""

import requests
import time
import json
import numpy as np

SERVER_URL = "http://localhost:3002/api/bluetooth-data"
SAMPLING_RATE = 100

def smoothstep(t):
    return t * t * (3 - 2 * t)

def generate_smooth_signal(voltage_sequence, total_samples):
    """
    生成连续平滑变化的信号，电压之间渐变过渡
    """
    total_duration = sum(duration for _, duration in voltage_sequence)
    
    samples_per_voltage = [int(duration * SAMPLING_RATE) for _, duration in voltage_sequence]
    actual_total = sum(samples_per_voltage)
    scale_factor = total_samples / actual_total
    samples_per_voltage = [int(s * scale_factor) for s in samples_per_voltage]
    
    signal = []
    prev_voltage = voltage_sequence[0][0]
    
    for i, ((voltage, _), num_samples) in enumerate(zip(voltage_sequence, samples_per_voltage)):
        if num_samples <= 0:
            continue
            
        transition_samples = int(num_samples * 0.4)
        
        for j in range(num_samples):
            if i > 0 and j < transition_samples:
                t = j / transition_samples
                eased_t = smoothstep(t)
                current_voltage = prev_voltage + (voltage - prev_voltage) * eased_t
            else:
                current_voltage = voltage
            
            noise = np.random.normal(0, 0.02)
            signal.append(current_voltage + noise)
        
        prev_voltage = voltage
    
    return signal[:total_samples]

def generate_eyelid_blink_signal(base_voltage, duration_sec, blink_config=None):
    """
    生成眨眼模式的眼睑信号
    
    blink_config: [(眨眼开始秒, 闭合持续秒, 闭合时电压倍数), ...]
    """
    num_samples = int(duration_sec * SAMPLING_RATE)
    signal = np.ones(num_samples) * base_voltage
    noise = np.random.normal(0, 0.015, num_samples)
    signal = signal + noise
    
    if blink_config:
        for blink_time, blink_duration, voltage_mult in blink_config:
            blink_start = int(blink_time * SAMPLING_RATE)
            blink_end = min(int((blink_time + blink_duration) * SAMPLING_RATE), num_samples)
            
            fade_samples = max(3, int(0.02 * SAMPLING_RATE))
            
            for k in range(blink_start, blink_end):
                if k >= num_samples:
                    break
                blink_voltage = base_voltage * voltage_mult
                
                if k < blink_start + fade_samples:
                    t = (k - blink_start) / fade_samples
                    signal[k] = base_voltage + (blink_voltage - base_voltage) * smoothstep(t)
                elif k > blink_end - fade_samples:
                    t = (blink_end - k) / fade_samples
                    signal[k] = blink_voltage - (blink_voltage - base_voltage) * smoothstep(t)
                else:
                    signal[k] = blink_voltage
    
    return signal.tolist()

def send_bluetooth_data(signal_data, timestamp=None):
    data = {
        "rawData": signal_data,
        "timestamp": timestamp or int(time.time() * 1000),
        "signalQuality": 95,
        "values": signal_data
    }
    
    try:
        response = requests.post(SERVER_URL, json=data, timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def simulate_continuous(name, voltage_sequence, duration_sec=15):
    """连续平滑变化的模拟"""
    print(f"\n{'='*50}")
    print(f"场景: {name}")
    print(f"{'='*50}")
    
    total_samples = int(duration_sec * SAMPLING_RATE)
    signal = generate_smooth_signal(voltage_sequence, total_samples)
    
    print(f"总样本数: {len(signal)}, 预计时长: {len(signal)/SAMPLING_RATE:.1f}秒")
    
    batch_size = SAMPLING_RATE
    for i in range(0, len(signal), batch_size):
        batch = signal[i:i+batch_size]
        current_sec = i / SAMPLING_RATE
        current_voltage = batch[len(batch)//2]
        
        send_bluetooth_data(batch)
        print(f"  t={current_sec:5.1f}s | 电压: {current_voltage:.3f}V", end='\r')
        time.sleep(0.95)
    
    print(f"\n✓ 场景完成")

def simulate_blinks(name, base_voltage, duration_sec, blink_sequence):
    """眨眼模式模拟"""
    print(f"\n{'='*50}")
    print(f"场景: {name}")
    print(f"{'='*50}")
    
    signal = generate_eyelid_blink_signal(base_voltage, duration_sec, blink_sequence)
    
    batch_size = SAMPLING_RATE
    for i in range(0, len(signal), batch_size):
        batch = signal[i:i+batch_size]
        send_bluetooth_data(batch)
        time.sleep(0.95)
    
    print(f"\n✓ 场景完成")

def main():
    print("蓝牙数据模拟器")
    print(f"服务器: {SERVER_URL}\n")
    
    scenario1 = [
        (1.0, 5),
        (1.3, 3),
        (2.3, 5),
        (3.3, 4),
        (1.2, 5),
    ]
    
    scenario2 = [
        (1.0, 8),
        (2.0, 4),
        (3.0, 3),
        (1.5, 5),
    ]
    
    scenario3_blinks = [
        (2.0, 0.15, 2.5),
        (4.0, 0.15, 2.5),
        (6.0, 0.15, 2.5),
        (9.0, 0.3, 2.8),
        (12.0, 0.5, 3.2),
    ]
    
    print("选择场景:")
    print("1) 连续电压变化 (1.0→1.3→2.3→3.3→1.2)")
    print("2) 连续电压变化 (1.0→2.0→3.0→1.5)")
    print("3) 眨眼模式 (睁眼基线1.0V + 眨眼)")
    print("4) 疲劳眨眼模式 (眨眼频率增加/时长增加)")
    
    choice = input("\n选择 (1-4): ").strip()
    
    if choice == "1":
        simulate_continuous("连续电压变化(用户指定)", scenario1, duration_sec=20)
    elif choice == "2":
        simulate_continuous("连续电压变化", scenario2, duration_sec=18)
    elif choice == "3":
        simulate_blinks("眨眼模式", 1.0, 15, scenario3_blinks)
    elif choice == "4":
        fatigue_blinks = [
            (1.0, 0.15, 2.5),
            (3.0, 0.15, 2.5),
            (5.0, 0.15, 2.5),
            (7.0, 0.2, 2.6),
            (9.0, 0.3, 2.8),
            (11.0, 0.4, 3.0),
            (13.0, 0.6, 3.2),
        ]
        simulate_blinks("疲劳眨眼模式", 1.0, 16, fatigue_blinks)
    else:
        print("无效选择")

if __name__ == "__main__":
    main()