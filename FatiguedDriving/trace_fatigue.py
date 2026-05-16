"""
Trace fatigue score batch-by-batch without the server,
replicating exactly what app.py does.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from algorithm.blink_fatigue import run_fatigue_pipeline, reset_fatigue_state

SAMPLING_RATE = 100
CALIBRATION_DURATION_SECONDS = 6

def generate_eyelid_blink_signal(base_voltage, duration_sec, blink_config=None):
    def smoothstep(t):
        return t * t * (3 - 2 * t)

    num_samples = int(duration_sec * SAMPLING_RATE)
    signal = np.ones(num_samples) * base_voltage
    noise = np.random.normal(0, 0.015, num_samples)
    signal = signal + noise

    if blink_config:
        for blink_time, blink_duration, voltage_mult in blink_config:
            blink_start = int(blink_time * SAMPLING_RATE)
            blink_end = min(int((blink_time + blink_duration) * SAMPLING_RATE), num_samples)
            fade_samples = max(3, int(0.02 * SAMPLING_RATE))
            for k in range(blink_start, blink_end):
                if k >= num_samples:
                    break
                blink_voltage = base_voltage * voltage_mult
                if k < blink_start + fade_samples:
                    t = (k - blink_start) / fade_samples
                    signal[k] = base_voltage + (blink_voltage - base_voltage) * smoothstep(t)
                elif k > blink_end - fade_samples:
                    t = (blink_end - k) / fade_samples
                    signal[k] = blink_voltage - (blink_voltage - base_voltage) * smoothstep(t)
                else:
                    signal[k] = blink_voltage

    signal = np.clip(signal, 0.0, 3.3)
    return signal


# --- Scenario 3: normal blinks ---
scenario3_blinks = [
    (2.0, 0.15, 2.5),
    (4.0, 0.15, 2.5),
    (6.0, 0.15, 2.5),
    (9.0, 0.3,  2.8),
    (12.0, 0.5, 3.2),
]

# --- Scenario 4: fatigue blinks ---
scenario4_blinks = [
    (1.0, 0.15, 2.5),
    (3.0, 0.15, 2.5),
    (5.0, 0.15, 2.5),
    (7.0, 0.2,  2.6),
    (9.0, 0.3,  2.8),
    (11.0, 0.4, 3.0),
    (13.0, 0.6, 3.2),
]

def run_trace(name, signal):
    print(f"\n{'='*80}")
    print(f"Scenario: {name}  |  total_samples={len(signal)}  |  duration={len(signal)/SAMPLING_RATE:.1f}s")
    print(f"{'='*80}")
    print(f"{'batch':>6} | {'t':>4} | {'score':>6} | {'blinkRate':>10} | {'avgDur(ms)':>12} | {'longBlinks':>10} | {'normBlinks':>10} | {'calibrating':>12}")
    print("-" * 95)

    reset_fatigue_state()

    batch_size = SAMPLING_RATE  # 100 samples = 1 second
    for batch_idx, start in enumerate(range(0, len(signal), batch_size)):
        batch = signal[start:start + batch_size]
        t_sec = start / SAMPLING_RATE

        raw_np = np.array(batch, dtype=float)
        finite_mask = np.isfinite(raw_np)
        if not np.all(finite_mask):
            raw_np = raw_np[finite_mask]
        if raw_np.size < 1:
            continue

        try:
            out = run_fatigue_pipeline(
                raw_signal=raw_np,
                sampling_rate=SAMPLING_RATE,
                driving_time="0小时0分钟",
                battery_level=None,
                calibration_duration_sec=CALIBRATION_DURATION_SECONDS,
            )
            score = out.get("fatigueScore", "?")
            blink_rate = out.get("blinkRate", "?")
            avg_dur = out.get("avgBlinkDuration", "?")
            eye = out.get("eyelidStatus", {})
            long_b = eye.get("longBlinks", "?")
            norm_b = eye.get("normalBlinks", "?")
            dbg = out.get("debug", {})
            is_cal = dbg.get("isCalibrating", "?")
            print(f"{batch_idx:>6} | {t_sec:>4.1f} | {str(score):>6} | {str(blink_rate):>10} | {str(avg_dur):>12} | {str(long_b):>10} | {str(norm_b):>10} | {str(is_cal):>12}")
        except Exception as e:
            print(f"{batch_idx:>6} | {t_sec:>4.1f} | ERROR: {e}")

np.random.seed(42)
signal3 = generate_eyelid_blink_signal(1.0, 15, scenario3_blinks)
np.random.seed(42)
signal4 = generate_eyelid_blink_signal(1.0, 16, scenario4_blinks)

run_trace("Scenario 3: Normal blinks (5 blinks)", signal3)
run_trace("Scenario 4: Fatigue blinks (7 blinks)", signal4)
