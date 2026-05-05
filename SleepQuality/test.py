import requests
import time
import random
import math

API_URL = 'http://localhost:3001/api/bluetooth-data'
SLEEP_QUALITY_LATEST_URL = 'http://localhost:3001/api/sleep-quality-latest'

def generate_wake_signal(num_samples, sampling_rate):
    """生成清醒状态信号 - 高频波动，有明显眨眼"""
    values = []
    blink_interval = int(sampling_rate * random.uniform(1.5, 3.5))  # 随机眨眼间隔
    blink_duration = int(sampling_rate * random.uniform(0.1, 0.2))  # 随机眨眼持续时间
    in_blink = False
    blink_counter = 0
    blink_timer = random.randint(0, blink_interval)
    
    for i in range(num_samples):
        if blink_timer > 0:
            blink_timer -= 1
        
        if in_blink:
            progress = blink_counter / blink_duration
            if progress < 0.3:
                val = 0.8 - 0.6 * (progress / 0.3)
            elif progress < 0.7:
                val = 0.2
            else:
                val = 0.2 + 0.6 * ((progress - 0.7) / 0.3)
            blink_counter += 1
            if blink_counter >= blink_duration:
                in_blink = False
                blink_interval = int(sampling_rate * random.uniform(1.5, 3.5))
                blink_timer = blink_interval
        else:
            baseline = 0.75 + random.uniform(-0.08, 0.08)
            noise = math.sin(i * random.uniform(0.05, 0.15)) * 0.03 + random.uniform(-0.04, 0.04)
            val = baseline + noise
            
            if blink_timer == 0 and random.random() < 0.005:
                in_blink = True
                blink_counter = 0
                blink_duration = int(sampling_rate * random.uniform(0.1, 0.2))
        
        values.append(max(0.0, min(1.0, val)))
    return values

def generate_light_sleep_signal(num_samples, sampling_rate):
    """生成浅睡眠信号 - 中等波动，周期性变化"""
    values = []
    slow_freq = random.uniform(0.3, 0.7)
    med_freq = random.uniform(1.5, 2.5)
    
    for i in range(num_samples):
        t = i / sampling_rate
        slow_wave = 0.45 + random.uniform(-0.05, 0.05) + 0.15 * math.sin(2 * math.pi * slow_freq * t)
        medium_wave = 0.05 * math.sin(2 * math.pi * med_freq * t)
        noise = random.uniform(-0.08, 0.08)
        val = slow_wave + medium_wave + noise
        values.append(max(0.0, min(1.0, val)))
    return values

def generate_deep_sleep_signal(num_samples, sampling_rate):
    """生成深睡眠信号 - 平稳，低频波动"""
    values = []
    slow_freq = random.uniform(0.1, 0.3)
    
    for i in range(num_samples):
        t = i / sampling_rate
        slow_wave = 0.5 + 0.03 * math.sin(2 * math.pi * slow_freq * t)
        noise = random.uniform(-0.02, 0.02)
        val = slow_wave + noise
        values.append(max(0.0, min(1.0, val)))
    return values

def generate_rem_sleep_signal(num_samples, sampling_rate):
    """生成REM睡眠信号 - 快速眼动，高频振荡"""
    values = []
    fast_freq = random.uniform(3.5, 4.5)
    med_freq = random.uniform(1.2, 1.8)
    
    for i in range(num_samples):
        t = i / sampling_rate
        fast_osc = 0.15 * math.sin(2 * math.pi * fast_freq * t + random.uniform(0, 2*math.pi))
        medium_osc = 0.08 * math.sin(2 * math.pi * med_freq * t)
        baseline = 0.5 + random.uniform(-0.05, 0.05)
        noise = random.uniform(-0.03, 0.03)
        val = baseline + fast_osc + medium_osc + noise
        values.append(max(0.0, min(1.0, val)))
    return values

def generate_random_night_segment(duration_sec, sampling_rate):
    """生成随机的夜间睡眠片段"""
    num_samples = int(duration_sec * sampling_rate)
    
    # 随机选择当前睡眠阶段（带权重）
    stage_weights = [
        ('light', 0.4),    # 浅睡眠最常见
        ('deep', 0.25),    # 深睡眠
        ('rem', 0.2),      # REM
        ('wake', 0.15)     # 短暂清醒
    ]
    
    rand = random.random()
    cumulative = 0
    selected_stage = 'light'
    
    for stage, weight in stage_weights:
        cumulative += weight
        if rand < cumulative:
            selected_stage = stage
            break
    
    # 生成对应阶段的信号
    if selected_stage == 'wake':
        return generate_wake_signal(num_samples, sampling_rate), selected_stage
    elif selected_stage == 'light':
        return generate_light_sleep_signal(num_samples, sampling_rate), selected_stage
    elif selected_stage == 'deep':
        return generate_deep_sleep_signal(num_samples, sampling_rate), selected_stage
    elif selected_stage == 'rem':
        return generate_rem_sleep_signal(num_samples, sampling_rate), selected_stage
    
    return generate_light_sleep_signal(num_samples, sampling_rate), 'light'

print('=' * 70)
print('SLEEP QUALITY - Realistic Random Data Injection')
print('=' * 70)
print('\nFeatures:')
print('  - Realistic sleep stage transitions with weighted probabilities')
print('  - Random signal characteristics for each stage')
print('  - Variable blink patterns during wakefulness')
print('  - Smooth signal transitions')
print('  - Random durations and intervals')
print('\nExpected Frontend Display:')
print('  - mainValue: qualityScore (10-95)')
print('  - mainValueLabel: "睡眠质量"')
print('  - sleepStage: deep/light/rem/awake')
print('\n' + '=' * 70)

stage_descriptions = {
    'wake': 'Awake',
    'light': 'Light Sleep',
    'deep': 'Deep Sleep',
    'rem': 'REM Sleep'
}

try:
    batch_count = 0
    
    while True:
        batch_count += 1
        
        # 随机选择发送时长（20-45秒，更广泛的范围）
        duration_sec = random.randint(20, 45)
        signal, current_stage = generate_random_night_segment(duration_sec, 100)
        
        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(75, 100)  # 更随机的信号质量
        }
        
        print(f'\n[Batch {batch_count:3d}] {stage_descriptions[current_stage]:<15} | Duration: {duration_sec}s | Samples: {len(signal)}')
        print(f'  Signal quality: {payload["signalQuality"]}%')
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            if resp.status_code == 200:
                print(f'  → Backend: SUCCESS')
                
                time.sleep(0.5)
                
                try:
                    result_resp = requests.get(SLEEP_QUALITY_LATEST_URL, timeout=2)
                    result = result_resp.json()
                    if result.get('success'):
                        data = result.get('data', {})
                        print(f'  → Frontend will show:')
                        print(f'      Quality Score: {data.get("qualityScore")}%')
                        print(f'      Current Stage: {data.get("currentStageName")}')
                        print(f'      Sleep Stage: {data.get("sleepStage")}')
                    else:
                        print(f'  → Backend result: {result.get("reason")}')
                except Exception as e:
                    print(f'  → Could not fetch latest result: {e}')
            else:
                print(f'  → Backend: FAILED ({resp.status_code})')
        except Exception as e:
            print(f'  → Error: {e}')
        
        # 随机间隔（3-10秒，更广泛的范围）
        sleep_time = random.uniform(3, 10)
        time.sleep(sleep_time)
        
except KeyboardInterrupt:
    print('\n\nData injection stopped.')
    print(f'Total batches sent: {batch_count}')