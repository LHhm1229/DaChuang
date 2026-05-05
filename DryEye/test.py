import requests
import time
import random

API_URL = 'http://localhost:3000/api/bluetooth-data'
DRY_EYE_LATEST_URL = 'http://localhost:3000/api/dry-eye-latest'

def generate_blink_signal(duration_sec=5, sampling_rate=100, blink_rate=15):
    num_samples = int(duration_sec * sampling_rate)
    values = []

    interval = sampling_rate * 60.0 / blink_rate
    next_blink = random.uniform(interval * 0.7, interval * 1.3)
    in_blink = False
    blink_remaining = 0
    blink_duration = int(sampling_rate * 0.15)
    valley_depth = random.uniform(0.15, 0.25)

    for i in range(num_samples):
        if not in_blink and i >= next_blink:
            in_blink = True
            blink_remaining = blink_duration
            next_blink = i + interval

        if in_blink:
            progress = blink_duration - blink_remaining
            if progress < blink_duration * 0.3:
                val = 0.8 - valley_depth * (progress / (blink_duration * 0.3))
            elif progress < blink_duration * 0.7:
                val = 0.8 - valley_depth
            else:
                val = 0.8 - valley_depth * ((blink_duration - progress) / (blink_duration * 0.3))
            blink_remaining -= 1
            if blink_remaining <= 0:
                in_blink = False
        else:
            val = 0.8 + random.uniform(-0.01, 0.01)

        values.append(max(0.0, min(1.0, val)))

    return values

print('=' * 70)
print('DRY EYE - Continuous Data Injection with Debug Output')
print('=' * 70)
print('\nExpected Frontend Display:')
print('  - mainValue: dryEyeRiskScore (0-100%)')
print('  - mainValueLabel: "干眼风险"')
print('  - mainValueUnit: "%"')
print('  - mainValueColor: green(<30), yellow(<60), red(>=60)')
print('  - secondaryMetrics:')
print('      * blinkRate: 眨眼频率 (次/分钟)')
print('      * avgBlinkDuration: 平均眨眼时长 (ms)')
print('      * eyeClosureRatio: 眼睛闭合比例 (%)')
print('\n' + '=' * 70)

states = [
    ('normal', 15, 'Normal blink rate (15/min) - Healthy'),
    ('dry', 8, 'Low blink rate (8/min) - Dry eye risk'),
    ('normal', 20, 'High blink rate (20/min) - Normal'),
    ('dry', 5, 'Very low blink rate (5/min) - High risk')
]

try:
    batch_count = 0
    state_index = 0
    chunks_per_state = 12
    current_chunk_in_state = 0

    while True:
        batch_count += 1

        state_name, blink_rate, description = states[state_index]
        signal = generate_blink_signal(5, 100, blink_rate)

        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 100)
        }

        print(f'\n[Batch {batch_count:3d}] {description}')
        print(f'  Blink rate: {blink_rate} times/min')
        print(f'  Signal samples: {len(signal)}, first 10: {[round(s, 3) for s in signal[:10]]}')

        try:
            resp = requests.post(API_URL, json=payload, timeout=2)
            if resp.status_code == 200:
                print(f'  → Backend: SUCCESS')

                time.sleep(1)

                try:
                    result_resp = requests.get(DRY_EYE_LATEST_URL, timeout=2)
                    result = result_resp.json()
                    if result.get('success'):
                        data = result.get('data', {})
                        print(f'  → Frontend will show:')
                        print(f'      Dry Eye Risk Score: {data.get("dryEyeRiskScore")}%')
                        print(f'      Dry Eye Risk Level: {data.get("dryEyeRiskLevel")}')
                        print(f'      Blink Rate: {data.get("blinkRate")} 次/分钟')
                        print(f'      Avg Blink Duration: {data.get("avgBlinkDuration")} ms')
                    else:
                        print(f'  → Backend result: {result.get("reason")}')
                except:
                    print(f'  → Could not fetch latest result')
            else:
                print(f'  → Backend: FAILED ({resp.status_code})')
        except Exception as e:
            print(f'  → Error: {e}')

        current_chunk_in_state += 1
        if current_chunk_in_state >= chunks_per_state:
            current_chunk_in_state = 0
            state_index = (state_index + 1) % len(states)
            print(f'\n{"="*70}')
            print(f'--- Switching to: {states[state_index][2]} ---')
            print(f'{"="*70}\n')

        time.sleep(5)

except KeyboardInterrupt:
    print('\n\nData injection stopped.')
    print(f'Total batches sent: {batch_count}')
