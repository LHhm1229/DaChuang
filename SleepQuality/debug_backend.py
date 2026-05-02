import requests
import json

# Check stats
r = requests.get('http://localhost:3001/api/stats')
stats = r.json()
print("=== Backend Stats ===")
print(f"Total Received: {stats.get('totalReceived')}")
print(f"Buffer Size: {stats.get('bufferSize')}")
print(f"Last Update: {stats.get('lastUpdate')}")

# Check sleep quality
r = requests.get('http://localhost:3001/api/sleep-quality-latest')
result = r.json()
print("\n=== Sleep Quality ===")
print(f"Success: {result.get('success')}")
if result.get('success'):
    data = result.get('data')
    print(f"Quality Score: {data.get('qualityScore')}")
    print(f"Current Stage: {data.get('currentStageName')} ({data.get('sleepStage')})")
    print(f"Stage Sequence: {data.get('stageSequence')}")
    print(f"Total Minutes: {data.get('totalMinutes')}")
else:
    print(f"Reason: {result.get('reason')}")
