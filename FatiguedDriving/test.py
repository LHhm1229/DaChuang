import requests
import time
import random
import math

API_URL = 'http://localhost:3002/api/bluetooth-data'
FATIGUE_LATEST_URL = 'http://localhost:3002/api/fatigue-latest'

def generate_eye_signal(duration_sec=5, sampling_rate=100, eye_openness=0.8, perclos=0.1):
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

print('=' * 70)
print('FATIGUED DRIVING - Continuous Data Injection with Debug Output')
print('=' * 70)
print('\nExpected Frontend Display:')
print('  - mainValue: fatigueScore (0-100)')
print('  - mainValueLabel: "疲劳评分"')
print('  - mainValueUnit: "分"')
print('  - mainValueColor: green(<40), yellow(<70), red(>=70)')
print('  - secondaryMetrics:')
print('      * blinkRate: 眨眼频率 (次/分钟)')
print('      * avgBlinkDuration: 平均眨眼时长 (ms)')
print('      * alertLevel: 预警等级')
print('\n' + '=' * 70)

states = [
    (0.85, 0.05, 'Alert - Eye open (85%), PERCLOS 5%'),
    (0.70, 0.15, 'Slightly Tired - Eye 70%, PERCLOS 15%'),
    (0.55, 0.25, 'Tired - Eye 55%, PERCLOS 25%'),
    (0.40, 0.40, 'Very Tired - Eye 40%, PERCLOS 40%'),
    (0.80, 0.08, 'Normal - Eye 80%, PERCLOS 8%')
]

try:
    batch_count = 0
    state_index = 0
    chunks_per_state = 10
    current_chunk_in_state = 0

    while True:
        batch_count += 1

        eye_openness, perclos, description = states[state_index]
        signal = generate_eye_signal(5, 100, eye_openness, perclos)

        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 100)
        }

        print(f'\n[Batch {batch_count:3d}] {description}')
        print(f'  Eye openness: {eye_openness * 100:.0f}%')
        print(f'  PERCLOS: {perclos * 100:.0f}%')
        print(f'  Signal samples: {len(signal)}, first 10: {[round(s, 3) for s in signal[:10]]}')

        try:
            resp = requests.post(API_URL, json=payload, timeout=2)
            if resp.status_code == 200:
                print(f'  → Backend: SUCCESS')

                time.sleep(1)

                try:
                    result_resp = requests.get(FATIGUE_LATEST_URL, timeout=2)
                    result = result_resp.json()
                    if result.get('success'):
                        data = result.get('data', {})
                        print(f'  → Frontend will show:')
                        print(f'      Fatigue Score: {data.get("fatigueScore")} 分')
                        print(f'      Fatigue Level: {data.get("fatigueLevel")}')
                        print(f'      Blink Rate: {data.get("blinkRate")} 次/分钟')
                        print(f'      Alert Level: {data.get("alertLevel")}')
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
