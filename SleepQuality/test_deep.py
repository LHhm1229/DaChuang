import requests
import time
import random
import math

API_URL = 'http://localhost:3001/api/bluetooth-data'

print('=== Testing Deep Sleep Detection ===')

# Generate deep sleep data (very small std dev)
signal = []
for i in range(3000):  # 30 seconds
    val = 0.5 + 0.003 * random.random()  # std dev ~0.001
    signal.append(max(0.0, min(1.0, val)))

payload = {
    'rawData': signal,
    'timestamp': int(time.time() * 1000),
    'signalQuality': 98
}

print('Sending 30 seconds of Deep Sleep data...')
try:
    resp = requests.post(API_URL, json=payload, timeout=5)
    if resp.status_code == 200:
        print('Success!')
    else:
        print(f'Error: {resp.status_code}')
except Exception as e:
    print(f'Connection Error: {e}')

print('\nWaiting 3 seconds...')
time.sleep(3)

# Check the result
r = requests.get('http://localhost:3001/api/sleep-quality-latest')
d = r.json()
print(f'Result:')
print(f'  Score: {d["data"]["qualityScore"]}')
print(f'  Stage: {d["data"]["currentStageName"]}')
print(f'  Stage Sequence: {d["data"]["stageSequence"]}')
