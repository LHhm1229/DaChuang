from __future__ import annotations

from typing import Tuple, Dict, List

import numpy as np

def simple_medfilt(x, kernel_size=3):
    """A simple median filter implementation without scipy."""
    if kernel_size % 2 == 0:
        kernel_size += 1
    half = kernel_size // 2
    res = np.zeros_like(x)
    for i in range(len(x)):
        start = max(0, i - half)
        end = min(len(x), i + half + 1)
        res[i] = np.median(x[start:end])
    return res

def simple_lowpass(x, alpha=0.3):
    """A simple RC lowpass filter implementation without scipy."""
    res = np.zeros_like(x)
    if len(x) == 0: return res
    res[0] = x[0]
    for i in range(1, len(x)):
        res[i] = alpha * x[i] + (1 - alpha) * res[i-1]
    return res

__all__ = [
    "preprocess_and_calibrate",
    "detect_blink_events_wavelet",
    "compute_dry_eye_metrics",
    "assess_dry_eye_risk",
    "run_dry_eye_pipeline",
]


def preprocess_and_calibrate(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    lowpass_cutoff: float = 6.0
) -> np.ndarray:
    centered = raw_signal - np.mean(raw_signal)

    # Use a simple lowpass filter instead of scipy.signal.butter/filtfilt
    filtered = simple_lowpass(centered, alpha=0.3)

    min_val, max_val = np.min(filtered), np.max(filtered)
    if max_val - min_val > 1e-6:
        normalized = (filtered - min_val) / (max_val - min_val)
    else:
        normalized = filtered.copy()

    diff = np.diff(normalized)
    neg_ratio = np.sum(diff < 0) / len(diff)
    if neg_ratio < 0.4:
        normalized = 1 - normalized

    return normalized


def detect_blink_events_wavelet(
    signal_norm: np.ndarray,
    sampling_rate: int = 100,
    amplitude_thresh: float = 0.15,
    min_duration_sec: float = 0.05,
    max_duration_sec: float = 1.0,
    refractory_sec: float = 0.2
) -> List[Dict]:
    events = []
    n = len(signal_norm)
    refractory_samples = int(refractory_sec * sampling_rate)

    window = max(3, int(sampling_rate * 0.02))
    if window % 2 == 0:
        window += 1
    # Use simple_medfilt instead of scipy.signal.medfilt
    smoothed = simple_medfilt(signal_norm, kernel_size=window)
    diff = np.diff(smoothed)

    threshold_diff = amplitude_thresh / 2
    i = 0
    while i < n - 1:
        if i < refractory_samples:
            i += 1
            continue

        if diff[i] < -threshold_diff:
            start = i
            valley = start
            while valley < n-1 and smoothed[valley+1] <= smoothed[valley]:
                valley += 1
            end = valley
            target_level = smoothed[start] - amplitude_thresh * 0.5
            while end < n-1 and smoothed[end] < target_level:
                end += 1

            if end - start > max_duration_sec * sampling_rate:
                i = valley + 1
                continue

            amplitude = smoothed[start] - smoothed[valley]
            duration_sec = (end - start) / sampling_rate

            if (amplitude >= amplitude_thresh and
                min_duration_sec <= duration_sec <= max_duration_sec):
                events.append({
                    'start': start,
                    'valley': valley,
                    'end': end,
                    'amplitude': amplitude,
                    'duration_sec': duration_sec,
                    'duration_ms': duration_sec * 1000
                })
                i = end + refractory_samples
            else:
                i = valley + 1
        else:
            i += 1
    return events


def compute_dry_eye_metrics(
    events: List[Dict],
    total_duration_sec: float
) -> Dict:
    n_blinks = len(events)
    if n_blinks == 0:
        return {
            'blink_rate_per_min': 0,
            'avg_blink_duration_ms': 0,
            'eye_closure_ratio_pct': 0,
            'incomplete_blink_ratio_pct': 0,
            'long_blink_ratio_pct': 0,
            'total_blinks': 0,
            'incomplete_blinks': 0,
            'long_blinks': 0
        }

    durations_ms = [e['duration_ms'] for e in events]
    amplitudes = [e['amplitude'] for e in events]

    avg_dur_ms = np.mean(durations_ms)
    rate_per_min = n_blinks / (total_duration_sec / 60)
    total_blink_sec = sum(e['duration_sec'] for e in events)
    closure_ratio = (total_blink_sec / total_duration_sec) * 100
    closure_ratio = min(closure_ratio, 100.0)

    avg_amp = np.mean(amplitudes)
    incomplete_thresh = avg_amp * 0.4
    incomplete_count = sum(1 for a in amplitudes if a < incomplete_thresh)
    incomplete_ratio = incomplete_count / n_blinks

    long_blink_count = sum(1 for d in durations_ms if d >= 500)
    long_blink_ratio = long_blink_count / n_blinks

    return {
        'blink_rate_per_min': round(rate_per_min, 1),
        'avg_blink_duration_ms': round(avg_dur_ms, 1),
        'eye_closure_ratio_pct': round(closure_ratio, 1),
        'incomplete_blink_ratio_pct': round(incomplete_ratio * 100, 1),
        'long_blink_ratio_pct': round(long_blink_ratio * 100, 1),
        'total_blinks': n_blinks,
        'incomplete_blinks': incomplete_count,
        'long_blinks': long_blink_count
    }


def assess_dry_eye_risk(
    blink_rate: float,
    avg_dur_ms: float,
    closure_ratio: float,
    incomplete_ratio_pct: float,
    long_blink_ratio_pct: float = 0
) -> Tuple[float, str, Dict]:
    if blink_rate < 12:
        freq_score = 60 + (12 - blink_rate) * 5
    elif blink_rate < 15:
        freq_score = (15 - blink_rate) * 20
    elif blink_rate <= 25:
        freq_score = 0
    elif blink_rate <= 30:
        freq_score = (blink_rate - 25) * 12
    else:
        freq_score = min(80, 60 + (blink_rate - 30) * 2)

    if avg_dur_ms <= 200:
        dur_score = 0
    elif avg_dur_ms <= 400:
        dur_score = (avg_dur_ms - 200) / 2
    else:
        dur_score = min(100, 100 + (avg_dur_ms - 400) * 0.2)

    if closure_ratio <= 2.5:
        closure_score = 0
    elif closure_ratio <= 10:
        closure_score = (closure_ratio - 2.5) * 10
    else:
        closure_score = min(100, 75 + (closure_ratio - 10) * 3)

    incomplete_pct = incomplete_ratio_pct
    if incomplete_pct < 30:
        inc_score = 0
    elif incomplete_pct < 40:
        inc_score = (incomplete_pct - 30) * 3
    elif incomplete_pct < 60:
        inc_score = 30 + (incomplete_pct - 40) * 2
    else:
        inc_score = min(95, 70 + (incomplete_pct - 60) * 0.5)

    long_score = 0
    if long_blink_ratio_pct > 5:
        long_score = min(60, (long_blink_ratio_pct - 5) * 3)

    weights = {
        'freq': 0.20,
        'duration': 0.20,
        'closure': 0.25,
        'incomplete': 0.30,
        'long': 0.05
    }
    risk_score = (freq_score * weights['freq'] +
                  dur_score * weights['duration'] +
                  closure_score * weights['closure'] +
                  inc_score * weights['incomplete'] +
                  long_score * weights['long'])

    risk_score = min(100.0, max(0.0, risk_score))

    if risk_score < 30:
        level = "低风险"
    elif risk_score < 60:
        level = "中风险"
    else:
        level = "高风险"

    detail = {
        "blink_rate_per_min": blink_rate,
        "avg_blink_duration_ms": avg_dur_ms,
        "closure_sec_per_min": round(closure_ratio / 100 * 60, 2),
        "incomplete_blink_ratio_pct": incomplete_ratio_pct,
        "long_blink_ratio_pct": long_blink_ratio_pct,
        "dry_eye_risk_score": round(risk_score, 1),
        "dry_eye_risk_level": level
    }
    return risk_score, level, detail


def run_dry_eye_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    duration_sec: float = None
) -> Dict:
    signal_norm = preprocess_and_calibrate(raw_signal, sampling_rate)
    events = detect_blink_events_wavelet(signal_norm, sampling_rate)

    if duration_sec is None:
        total_sec = len(raw_signal) / sampling_rate
    else:
        total_sec = duration_sec

    metrics = compute_dry_eye_metrics(events, total_sec)
    risk_score, risk_level, detail = assess_dry_eye_risk(
        blink_rate=metrics['blink_rate_per_min'],
        avg_dur_ms=metrics['avg_blink_duration_ms'],
        closure_ratio=metrics['eye_closure_ratio_pct'],
        incomplete_ratio_pct=metrics['incomplete_blink_ratio_pct'],
        long_blink_ratio_pct=metrics['long_blink_ratio_pct']
    )

    result = {
        "blinkRate": metrics['blink_rate_per_min'],
        "avgBlinkDuration": metrics['avg_blink_duration_ms'],
        "eyeClosureRatio": metrics['eye_closure_ratio_pct'],
        "incompleteBlinkRatio": metrics['incomplete_blink_ratio_pct'],
        "longBlinkRatio": metrics['long_blink_ratio_pct'],
        "dryEyeRiskScore": round(risk_score, 1),
        "dryEyeRiskLevel": risk_level,
        "totalBlinks": metrics['total_blinks'],
        "incompleteBlinks": metrics['incomplete_blinks'],
        "longBlinks": metrics['long_blinks'],
        "details": detail
    }
    return result