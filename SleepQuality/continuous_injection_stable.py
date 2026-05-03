import requests
import time
import random
import math

API_URL = 'http://localhost:3001/api/bluetooth-data'
SLEEP_LATEST_URL = 'http://localhost:3001/api/sleep-quality-latest'

def generate_signal_chunk(duration_sec, sampling_rate, state='normal'):
    num_samples = int(duration_sec * sampling_rate)
    values = []

    if state == 'wake':
        for i in range(num_samples):
            noise = random.uniform(-0.02, 0.02)
            if random.random() > 0.95:
                val = 0.85 + noise
            else:
                val = 0.15 + noise
            values.append(max(0.0, min(1.0, val)))
    elif state == 'deep':
        for i in range(num_samples):
            val = 0.5 + 0.005 * random.random()
            values.append(max(0.0, min(1.0, val)))
    elif state == 'light_n1':
        for i in range(num_samples):
            noise = random.uniform(-0.08, 0.08)
            val = 0.5 + noise
            values.append(max(0.0, min(1.0, val)))
    elif state == 'light_n2':
        for i in range(num_samples):
            noise = random.uniform(-0.03, 0.03)
            val = 0.5 + noise
            values.append(max(0.0, min(1.0, val)))
    elif state == 'rem':
        t = [i / sampling_rate for i in range(num_samples)]
        for i in range(num_samples):
            rem_osc = 0.15 * math.sin(2 * math.pi * 1.5 * t[i])
            val = 0.5 + rem_osc + 0.01 * random.random()
            values.append(max(0.0, min(1.0, val)))
    else:
        for i in range(num_samples):
            values.append(0.5)
    return values

print('=' * 70)
print('SLEEP QUALITY - Continuous Data Injection with Debug Output')
print('=' * 70)
print('\nExpected Frontend Display:')
print('  - mainValue: qualityScore (0-100)')
print('  - mainValueLabel: "睡眠质量"')
print('  - mainValueUnit: "分"')
print('  - mainValueColor: green(>=80), yellow(>=60), red(<60)')
print('  - secondaryMetrics:')
print('      * currentStage: 当前阶段名称')
print('      * remDensity: REM密度')
print('      * sleepEfficiency: 睡眠效率')
print('\n' + '=' * 70)

states = ['deep', 'light_n2', 'rem', 'light_n1', 'wake']
state_descriptions = {
    'deep': 'Deep Sleep (expected score ~75)',
    'light_n2': 'Light Sleep N2 (expected score ~60)',
    'rem': 'REM Sleep (expected score ~70)',
    'light_n1': 'Light Sleep N1 (expected score ~45)',
    'wake': 'Awake (expected score ~30)'
}

try:
    batch_count = 0
    state_index = 0
    chunks_per_state = 8
    current_chunk_in_state = 0

    while True:
        batch_count += 1

        state = states[state_index]

        signal = generate_signal_chunk(5, 100, state)
        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 100)
        }

        print(f'\n[Batch {batch_count:3d}] Sending {state.upper()} data...')
        print(f'  Signal samples: {len(signal)}, first 5: {[round(s, 3) for s in signal[:5]]}')
        print(f'  Signal std: {round(sum(signal) / len(signal), 3)} (approx)')

        try:
            resp = requests.post(API_URL, json=payload, timeout=2)
            if resp.status_code == 200:
                print(f'  → Backend: SUCCESS')

                time.sleep(1)

                try:
                    result_resp = requests.get(SLEEP_LATEST_URL, timeout=2)
                    result = result_resp.json()
                    if result.get('success'):
                        data = result['data']
                        print(f'  → Frontend will show:')
                        print(f'      Quality Score: {data.get("qualityScore")} 分')
                        print(f'      Current Stage: {data.get("currentStageName")}')
                        print(f'      Sleep Efficiency: {data.get("sleepEfficiency")}%')
                        print(f'      REM Density: {data.get("rem_density", 0):.2f}')
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
            print(f'--- Switching to: {state_descriptions[states[state_index]]} ---')
            print(f'{"="*70}\n')

        time.sleep(5)

except KeyboardInterrupt:
    print('\n\nData injection stopped.')
    print(f'Total batches sent: {batch_count}')
