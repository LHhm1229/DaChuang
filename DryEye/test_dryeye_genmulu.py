import numpy as np
import requests
import time
import json

API_URL = "http://localhost:3000/api/bluetooth-data"
DRY_EYE_LATEST_URL = "http://localhost:3000/api/dry-eye-latest"

def generate_blink_signal(duration_sec=60, fs=100, blink_rate_per_min=15):
    t = np.linspace(0, duration_sec, duration_sec * fs)
    baseline = 0.85
    signal_sim = np.full_like(t, baseline)

    blink_rate = blink_rate_per_min / 60
    blink_dur_sec = 0.15

    for i in range(int(duration_sec * blink_rate)):
        start_t = i / blink_rate
        idx = np.where((t >= start_t) & (t <= start_t + blink_dur_sec))[0]
        if len(idx) > 0:
            for j, pos in enumerate(idx):
                progress = j / len(idx)
                if progress < 0.3:
                    signal_sim[pos] = baseline - (baseline - 0.2) * (progress / 0.3)
                else:
                    signal_sim[pos] = 0.2 + (baseline - 0.2) * ((progress - 0.3) / 0.7)

    noise = np.random.normal(0, 0.03, len(t))
    signal_sim += noise
    return signal_sim.tolist()


def send_batch(raw_data, batch_id, signal_quality=95):
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


def test_dryeye_pipeline():
    print("=" * 60)
    print("[DryEye] Backend Line Test")
    print("=" * 60)

    print("\n>>> Generating simulated blink signal...")
    signal = generate_blink_signal(duration_sec=10, fs=100, blink_rate_per_min=18)
    print(f"    Signal length: {len(signal)} samples ({len(signal)/100:.1f} sec)")

    chunk_size = 100
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
            print(f"  [{ts}] Batch {i+1}/{num_batches} [OK] {result.get('message', 'OK')} ({len(chunk)} samples)")

        time.sleep(0.05)

    print("-" * 60)
    print("\n>>> Waiting for algorithm processing...")

    time.sleep(2)

    print("\n>>> Querying latest dry eye detection results:")
    try:
        resp = requests.get(DRY_EYE_LATEST_URL, timeout=5)
        result = resp.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"    [FAIL] Query failed: {e}")

    print("\n" + "=" * 60)
    print("[DONE] Test complete")
    print("=" * 60)


if __name__ == "__main__":
    test_dryeye_pipeline()
