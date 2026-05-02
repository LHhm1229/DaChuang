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
            if random.random() > 0.98:
                val = 0.85 + noise
            else:
                val = 0.15 + noise
            values.append(max(0.0, min(1.0, val)))
    elif state == 'deep':
        for i in range(num_samples):
            val = 0.5 + 0.01 * random.random()
            values.append(max(0.0, min(1.0, val)))
    elif state == 'light':
        for i in range(num_samples):
            noise = random.uniform(-0.1, 0.1)
            val = 0.5 + noise
            values.append(max(0.0, min(1.0, val)))
    elif state == 'rem':
        t = [i / sampling_rate for i in range(num_samples)]
        for i in range(num_samples):
            rem_osc = 0.15 * math.sin(2 * math.pi * 1.5 * t[i])
            val = 0.5 + rem_osc + 0.02 * random.random()
            values.append(max(0.0, min(1.0, val)))
    else:
        for i in range(num_samples):
            values.append(0.5)
    return values

print('=== Continuous Sleep Quality Data Injection ===')
print('Press Ctrl+C to stop\n')

states = ['deep', 'light', 'rem', 'wake']
state_descriptions = {
    'deep': 'Deep Sleep',
    'light': 'Light Sleep',
    'rem': 'REM Sleep',
    'wake': 'Awake'
}

try:
    batch_count = 0
    while True:
        batch_count += 1
        # Randomly select a sleep state
        state = random.choice(states)
        
        # Generate and send 5 seconds of data
        signal = generate_signal_chunk(5, 100, state)
        payload = {
            'rawData': signal,
            'timestamp': int(time.time() * 1000),
            'signalQuality': random.randint(85, 100)
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=2)
            if resp.status_code == 200:
                print(f"[Batch {batch_count:3d}] Sent 5s of {state_descriptions[state]:12s} data - OK")
            else:
                print(f"[Batch {batch_count:3d}] Error: {resp.status_code}")
        except Exception as e:
            print(f"[Batch {batch_count:3d}] Connection Error: {e}")
        
        # Wait before sending next batch
        time.sleep(3)

except KeyboardInterrupt:
    print('\n\nData injection stopped.')
    print(f'Total batches sent: {batch_count}')
