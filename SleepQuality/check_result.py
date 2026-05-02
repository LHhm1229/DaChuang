import requests
import time

print('Waiting for data to accumulate...')
time.sleep(45)

r = requests.get('http://localhost:3001/api/sleep-quality-latest')
d = r.json()

if d.get('success'):
    data = d['data']
    print(f"Score: {data.get('qualityScore')}")
    print(f"Current Stage (CN): {data.get('currentStageName')}")
    print(f"Current Stage (EN): {data.get('sleepStage')}")
    print(f"Stage Sequence: {data.get('stageSequence')}")
    print(f"Stage Durations: {data.get('stageDurations')}")
    print(f"Stage Percentages: {data.get('stagePercentages')}")
    print(f"Total Minutes: {data.get('totalMinutes')}")
else:
    print(f"Failed: {d.get('reason')}")
