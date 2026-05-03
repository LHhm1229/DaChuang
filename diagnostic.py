import requests
import time
import json

print('=' * 60)
print('System Data Path Diagnostic Tool')
print('=' * 60)

def check_service(name, port, path='/'):
    print(f'\n[{name}] Port {port}')
    print('-' * 40)
    try:
        resp = requests.get(f'http://localhost:{port}{path}', timeout=2)
        print(f'  Status: {resp.status_code} OK')
        return True
    except requests.exceptions.ConnectionError:
        print(f'  Status: NOT RUNNING (Connection refused)')
        return False
    except Exception as e:
        print(f'  Status: ERROR - {e}')
        return False

def check_websocket(name, port):
    print(f'\n[WebSocket {name}] Port {port}')
    print('-' * 40)
    try:
        resp = requests.get(f'http://localhost:{port}/', timeout=2)
        if resp.status_code == 200:
            print(f'  WebSocket Endpoint: Available')
            return True
    except:
        pass
    print(f'  WebSocket Endpoint: Not available')
    return False

def test_data_injection(name, port, test_data):
    print(f'\n[Data Injection Test] {name} Port {port}')
    print('-' * 40)
    try:
        resp = requests.post(f'http://localhost:{port}/api/bluetooth-data',
                           json=test_data, timeout=2)
        if resp.status_code == 200:
            print(f'  Data Injection: SUCCESS')
            return True
        else:
            print(f'  Data Injection: FAILED (Status {resp.status_code})')
            return False
    except Exception as e:
        print(f'  Data Injection: ERROR - {e}')
        return False

print('\n[1] Checking Backend Services...')
print('=' * 60)
services = [
    ('DryEye', 3000, '/'),
    ('SleepQuality', 3001, '/'),
    ('FatiguedDriving', 3002, '/')
]

results = {}
for name, port, path in services:
    results[name] = check_service(name, port, path)

print('\n[2] Checking Data Injection...')
print('=' * 60)

if results.get('SleepQuality'):
    test_data = {
        'rawData': [0.5] * 500,
        'timestamp': int(time.time() * 1000),
        'signalQuality': 95
    }
    test_data_injection('SleepQuality', 3001, test_data)

if results.get('DryEye'):
    test_data = {
        'rawData': [0.8] * 500,
        'timestamp': int(time.time() * 1000),
        'signalQuality': 95
    }
    test_data_injection('DryEye', 3000, test_data)

if results.get('FatiguedDriving'):
    test_data = {
        'rawData': [0.75] * 500,
        'timestamp': int(time.time() * 1000),
        'signalQuality': 95
    }
    test_data_injection('FatiguedDriving', 3002, test_data)

print('\n[3] Checking API Results...')
print('=' * 60)

time.sleep(1)

if results.get('SleepQuality'):
    try:
        resp = requests.get('http://localhost:3001/api/sleep-quality-latest', timeout=2)
        d = resp.json()
        if d.get('success'):
            print(f'  SleepQuality Result: Score={d["data"]["qualityScore"]}, Stage={d["data"]["currentStageName"]}')
        else:
            print(f'  SleepQuality Result: {d.get("reason")}')
    except Exception as e:
        print(f'  SleepQuality Result: ERROR - {e}')

if results.get('DryEye'):
    try:
        resp = requests.get('http://localhost:3000/api/dry-eye-latest', timeout=2)
        d = resp.json()
        if d.get('success'):
            print(f'  DryEye Result: Risk={d["data"].get("dryEyeRiskScore", "N/A")}')
        else:
            print(f'  DryEye Result: {d.get("reason")}')
    except Exception as e:
        print(f'  DryEye Result: ERROR - {e}')

if results.get('FatiguedDriving'):
    try:
        resp = requests.get('http://localhost:3002/api/fatigue-latest', timeout=2)
        d = resp.json()
        if d.get('success'):
            print(f'  FatiguedDriving Result: Level={d["data"].get("fatigueLevel", "N/A")}')
        else:
            print(f'  FatiguedDriving Result: {d.get("reason")}')
    except Exception as e:
        print(f'  FatiguedDriving Result: ERROR - {e}')

print('\n' + '=' * 60)
print('Diagnostic Complete')
print('=' * 60)
