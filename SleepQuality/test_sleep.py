import numpy as np
import requests
import time
import json

API_URL = "http://localhost:3001/api/bluetooth-data"
SLEEP_LATEST_URL = "http://localhost:3001/api/sleep-quality-latest"

def generate_sleep_signal_multi_stage(fs=100):
    """
    Generate multiple epochs of sleep signal with different stages.
    Epoch 0: Wake (0) -> High std, many blinks.
    Epoch 1: Deep Sleep (3) -> Very low std < 0.05.
    Epoch 2: Light Sleep (2) -> Moderate std.
    Epoch 3: REM (4) -> High freq (rem_density), low sem.
    Total duration: 120 seconds (4 epochs)
    """
    duration_sec = 120
    t = np.linspace(0, duration_sec, duration_sec * fs)
    signal_sim = np.zeros_like(t)
    
    # Epoch 0: Wake (0-30s)
    # Target: High activity, std > 0.1, many blinks.
    signal_sim[0:30*fs] = 0.5 + 0.15 * np.random.randn(30*fs)
    for _ in range(15): # Many blinks
        idx = np.random.randint(0, 30*fs - 15)
        signal_sim[idx:idx+15] -= 0.5

    # Epoch 1: Deep Sleep (30-60s)
    # Target: std < 0.05
    signal_sim[30*fs:60*fs] = 0.5 + 0.01 * np.random.randn(30*fs)

    # Epoch 2: Light Sleep (60-90s)
    # Target: Moderate std (e.g. 0.15) to avoid N3 (<0.05)
    signal_sim[60*fs:90*fs] = 0.5 + 0.15 * np.random.randn(30*fs)

    # Epoch 3: REM (90-120s)
    # Target: REM density > 0.3 and high rem_sem_ratio.
    # Higher frequency oscillation (e.g. 1.5Hz) will increase rem_energy relative to sem_energy.
    rem_osc = 0.1 * np.sin(2 * np.pi * 1.5 * t[90*fs:120*fs])
    signal_sim[90*fs:120*fs] = 0.5 + rem_osc + 0.01 * np.random.randn(30*fs)

    return signal_sim.tolist()


def send_batch(raw_data, batch_id, signal_quality=98):
    payload = {
        "rawData": raw_data,
        "timestamp": int(time.time() * 1000),
        "signalQuality": signal_quality,
        "values": raw_data
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def test_sleep_pipeline():
    print("=" * 60)
    print("[SleepQuality] Multi-Stage Backend Test")
    print("=" * 60)

    print("\n>>> Generating 4-epoch multi-stage sleep signal (120s)...")
    print("    - Epoch 1: Wake")
    print("    - Epoch 2: Deep Sleep")
    print("    - Epoch 3: Light Sleep")
    print("    - Epoch 4: REM")
    
    signal = generate_sleep_signal_multi_stage(fs=100)
    print(f"    Signal length: {len(signal)} samples")

    chunk_size = 500 # 5 seconds per batch
    total_samples = len(signal)
    num_batches = (total_samples + chunk_size - 1) // chunk_size

    print(f"\n>>> Sending data in batches ({num_batches} batches, {chunk_size} samples each)...")
    print("-" * 60)

    for i in range(num_batches):
        start = i * chunk_size
        end = min(start + chunk_size, total_samples)
        chunk = signal[start:end]

        result = send_batch(chunk, batch_id=i+1)
        ts = time.strftime("%H:%M:%S")

        if "error" in result:
            print(f"  [{ts}] Batch {i+1}/{num_batches} [FAIL] Error: {result['error']}")
        else:
            print(f"  [{ts}] Batch {i+1}/{num_batches} [OK] Data Sent ({len(chunk)} samples)")

        # Send fast for testing, but wait slightly
        time.sleep(0.05)

    print("-" * 60)
    print("\n>>> Waiting for final algorithm processing...")
    time.sleep(3)

    print("\n>>> Querying full sleep history:")
    try:
        resp = requests.get(SLEEP_LATEST_URL, timeout=5)
        result = resp.json()
        if result["success"]:
            data = result["data"]
            print(f"\nFinal Result:")
            print(f"  Total Minutes: {data['totalMinutes']}")
            print(f"  Sleep Efficiency: {data['sleepEfficiency']}%")
            print(f"  Current Stage: {data['currentStageName']}")
            print(f"  Stage Sequence: {data['stageSequence']}")
            print(f"  Stage Percentages: {json.dumps(data['stagePercentages'], indent=2)}")
        else:
            print(f"  [FAIL] {result['reason']}")
    except Exception as e:
        print(f"    [FAIL] Query failed: {e}")

    print("\n" + "=" * 60)
    print("[DONE] Test complete")
    print("=" * 60)


if __name__ == "__main__":
    test_sleep_pipeline()
