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

print('=== Sleep Quality System Test ===')
print('Testing backend API...')

print('\n[Test 1] Sending wake state data...')
signal = generate_signal_chunk(5, 100, 'wake')
payload = {'rawData': signal, 'timestamp': int(time.time() * 1000), 'signalQuality': 95}
resp = requests.post(API_URL, json=payload, timeout=5)
print(f'Response: {resp.status_code} - {resp.json()}')

time.sleep(1)

print('\n[Test 2] Sending deep sleep state data...')
signal = generate_signal_chunk(5, 100, 'deep')
payload = {'rawData': signal, 'timestamp': int(time.time() * 1000), 'signalQuality': 90}
resp = requests.post(API_URL, json=payload, timeout=5)
print(f'Response: {resp.status_code} - {resp.json()}')

time.sleep(1)

print('\n[Test 3] Sending light sleep state data...')
signal = generate_signal_chunk(5, 100, 'light')
payload = {'rawData': signal, 'timestamp': int(time.time() * 1000), 'signalQuality': 85}
resp = requests.post(API_URL, json=payload, timeout=5)
print(f'Response: {resp.status_code} - {resp.json()}')

print('\n[Final] Getting latest sleep quality result...')
resp = requests.get('http://localhost:3001/api/sleep-quality-latest', timeout=5)
result = resp.json()
if result.get('success'):
    data = result['data']
    print(f"Sleep Quality Score: {data.get('qualityScore')}")
    print(f"Current Stage: {data.get('currentStageName')}")
    print(f"Sleep Efficiency: {data.get('sleepEfficiency')}%")
    print(f"Total Minutes: {data.get('totalMinutes')}")
else:
    print(f"No result yet: {result.get('reason')}")

print('\n=== Test Complete ===')
