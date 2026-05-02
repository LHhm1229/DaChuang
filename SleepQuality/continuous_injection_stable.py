import requests
import time
import random
import math

API_URL = 'http://localhost:3001/api/bluetooth-data'

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
            val = 0.5 + 0.005 * random.random()  # 极小的标准差，确保触发深睡规则
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

print('=== Stable Sleep Quality Data Injection ===')
print('Sequentially sending each state for 40 seconds\n')

states = ['deep', 'light_n2', 'rem', 'light_n1', 'wake']
state_descriptions = {
    'deep': 'Deep Sleep (score ~75)',
    'light_n2': 'Light Sleep N2 (score ~60)',
    'rem': 'REM Sleep (score ~70)',
    'light_n1': 'Light Sleep N1 (score ~45)',
    'wake': 'Awake (score ~30)'
}

try:
    batch_count = 0
    state_index = 0
    chunks_per_state = 8  # 每个状态持续8个5秒chunk（共40秒）
    current_chunk_in_state = 0

    while True:
        batch_count += 1
        
        state = states[state_index]
        
        # Generate and send 5 seconds of data
        signal = generate_signal_chunk(5, 100, state)
        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(90, 100)
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=2)
            if resp.status_code == 200:
                print(f"[Batch {batch_count:3d}] {state_descriptions[state]} - OK")
            else:
                print(f"[Batch {batch_count:3d}] Error: {resp.status_code}")
        except Exception as e:
            print(f"[Batch {batch_count:3d}] Connection Error: {e}")
        
        # Move to next chunk in current state
        current_chunk_in_state += 1
        
        # If we've sent enough chunks for this state, move to next state
        if current_chunk_in_state >= chunks_per_state:
            current_chunk_in_state = 0
            state_index = (state_index + 1) % len(states)
            print(f"\n--- Switching to next state: {state_descriptions[states[state_index]]} ---")
        
        # Wait before sending next batch
        time.sleep(3)

except KeyboardInterrupt:
    print('\n\nData injection stopped.')
    print(f'Total batches sent: {batch_count}')
