"""Poll fatigue API every second for N seconds and print progression."""
import requests
import time
import sys

URL = "http://localhost:3002/api/fatigue-latest"
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 20

print(f"Polling {URL} every 1s for {DURATION}s...")
print(f"{'t':>4} | {'score':>6} | {'blinkRate':>10} | {'avgDur(ms)':>12} | {'longBlinks':>10} | {'normalBlinks':>12} | {'PERCLOS':>8}")
print("-" * 80)

last_score = None
for i in range(1, DURATION + 1):
    time.sleep(1)
    try:
        r = requests.get(URL, timeout=2)
        d = r.json()
        if not d.get("success") or d.get("data") is None:
            print(f"{i:>4}s | -- no data yet --")
            continue
        data = d["data"]
        score = data.get("fatigueScore", "?")
        blink_rate = data.get("blinkRate", "?")
        avg_dur = data.get("avgBlinkDuration", "?")
        eye = data.get("eyelidStatus", {})
        long_blinks = eye.get("longBlinks", "?")
        normal_blinks = eye.get("normalBlinks", "?")
        closure = eye.get("eyeClosureRatio", "?")
        changed = " <-- CHANGED" if score != last_score else ""
        print(f"{i:>4}s | {str(score):>6} | {str(blink_rate):>10} | {str(avg_dur):>12} | {str(long_blinks):>10} | {str(normal_blinks):>12} | {str(closure):>8}{changed}")
        last_score = score
    except Exception as e:
        print(f"{i:>4}s | ERROR: {e}")
