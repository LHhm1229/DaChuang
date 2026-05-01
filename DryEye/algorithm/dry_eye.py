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
    filtered = simple_lowpass(centered, alpha=0.3)

    min_val, max_val = np.min(filtered), np.max(filtered)
    if max_val - min_val > 1e-6:
        normalized = (filtered - min_val) / (max_val - min_val)
    else:
        normalized = filtered.copy()

    # 校正极性：确保眨眼特征表现为向下的波谷 (对应眼睑闭合导致的电位下降)
    diff = np.diff(normalized)
    neg_ratio = np.sum(diff < 0) / len(diff)
    if neg_ratio < 0.4:
        normalized = 1 - normalized

    return normalized

def detect_blink_events_wavelet(
    signal_norm: np.ndarray,
    sampling_rate: int = 100,
    amplitude_thresh: float = 0.10, # 稍微调低以适应干眼患者微弱眨眼
    min_duration_sec: float = 0.04, # 放宽下限，捕捉极短微眨眼
    max_duration_sec: float = 1.0,
    refractory_sec: float = 0.15
) -> List[Dict]:
    """基于一阶差分与形态学的事件检测 (原名保留以兼容接口)"""
    events = []
    n = len(signal_norm)
    refractory_samples = int(refractory_sec * sampling_rate)

    window = max(3, int(sampling_rate * 0.02))
    if window % 2 == 0: window += 1
    smoothed = simple_medfilt(signal_norm, kernel_size=window)
    diff = np.diff(smoothed)

    threshold_diff = amplitude_thresh / 3  # 降低斜率门槛，防止漏检
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
            
            # 寻找波形恢复点
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
            'blink_rate_per_min': 0, 'avg_blink_duration_ms': 0,
            'eye_closure_ratio_pct': 0, 'incomplete_blink_ratio_pct': 100.0, # 没眨眼视为极度异常
            'long_blink_ratio_pct': 0, 'total_blinks': 0,
            'incomplete_blinks': 0, 'long_blinks': 0
        }

    durations_ms = [e['duration_ms'] for e in events]
    amplitudes = [e['amplitude'] for e in events]

    avg_dur_ms = np.mean(durations_ms)
    rate_per_min = n_blinks / (total_duration_sec / 60)
    total_blink_sec = sum(e['duration_sec'] for e in events)
    closure_ratio = (total_blink_sec / total_duration_sec) * 100
    closure_ratio = min(closure_ratio, 100.0)

    # 【修复】使用绝对归一化阈值判断不完全眨眼，而不是动态均值
    # 假设充分的眨眼振幅应大于 0.4
    absolute_incomplete_thresh = 0.4
    incomplete_count = sum(1 for a in amplitudes if a < absolute_incomplete_thresh)
    incomplete_ratio = incomplete_count / n_blinks

    long_blink_count = sum(1 for d in durations_ms if d >= 500)
    long_blink_ratio = long_blink_count / n_blinks

    result = {
        'blink_rate_per_min': round(rate_per_min, 1),
        'avg_blink_duration_ms': round(avg_dur_ms, 1),
        'eye_closure_ratio_pct': round(closure_ratio, 1),
        'incomplete_blink_ratio_pct': round(incomplete_ratio * 100, 1),
        'long_blink_ratio_pct': round(long_blink_ratio * 100, 1),
        'total_blinks': n_blinks,
        'incomplete_blinks': incomplete_count,
        'long_blinks': long_blink_count
    }
    
    print(f"[ALGO] 检测到 {n_blinks} 次眨眼 | 频率={result['blink_rate_per_min']}/min | 闭合={result['eye_closure_ratio_pct']}% | 不完全={result['incomplete_blink_ratio_pct']}%")
    return result

def assess_dry_eye_risk(
    blink_rate: float,
    avg_dur_ms: float,
    closure_ratio: float,
    incomplete_ratio_pct: float,
    long_blink_ratio_pct: float = 0
) -> Tuple[float, str, Dict]:
    # 1. 频率得分 (U型曲线：正常 15-25，过低或过高都是风险)
    if blink_rate < 5: freq_score = 100
    elif blink_rate < 15: freq_score = 100 - (blink_rate - 5) * 10
    elif blink_rate <= 25: freq_score = 0
    elif blink_rate <= 40: freq_score = (blink_rate - 25) * 6
    else: freq_score = 100

    # 2. 时长得分 (U型曲线：正常 100-250ms)
    if avg_dur_ms < 50: dur_score = 100
    elif avg_dur_ms < 100: dur_score = 100 - (avg_dur_ms - 50) * 2
    elif avg_dur_ms <= 250: dur_score = 0
    elif avg_dur_ms <= 500: dur_score = (avg_dur_ms - 250) * 0.4
    else: dur_score = 100

    # 3. 闭合比例得分 (U型曲线：正常 3% - 8%)
    # 【修复】闭合比例过低 (死盯着屏幕) 现在会产生极高的风险分
    if closure_ratio < 1.0: closure_score = 100
    elif closure_ratio < 3.0: closure_score = 100 - (closure_ratio - 1) * 50
    elif closure_ratio <= 8.0: closure_score = 0
    elif closure_ratio <= 15.0: closure_score = (closure_ratio - 8) * 14
    else: closure_score = 100

    # 4. 不完全眨眼得分 (线性递增：大于10%开始算风险)
    if incomplete_ratio_pct < 10: inc_score = 0
    else: inc_score = min(100, (incomplete_ratio_pct - 10) * 1.5)

    # 5. 长时间眨眼得分
    if long_blink_ratio_pct < 5: long_score = 0
    else: long_score = min(100, (long_blink_ratio_pct - 5) * 5)

    weights = {
        'freq': 0.15,
        'duration': 0.15,
        'closure': 0.25,
        'incomplete': 0.30,
        'long': 0.15
    }
    
    risk_score = (freq_score * weights['freq'] +
                  dur_score * weights['duration'] +
                  closure_score * weights['closure'] +
                  inc_score * weights['incomplete'] +
                  long_score * weights['long'])

    # 如果频率为0，强制高风险
    if blink_rate == 0: risk_score = max(risk_score, 90.0)

    risk_score = min(100.0, max(0.0, risk_score))

    if risk_score < 30: level = "低风险"
    elif risk_score < 60: level = "中风险"
    else: level = "高风险"

    detail = {
        "blink_rate_per_min": blink_rate,
        "avg_blink_duration_ms": avg_dur_ms,
        "closure_sec_per_min": round(closure_ratio / 100 * 60, 2),
        "incomplete_blink_ratio_pct": incomplete_ratio_pct,
        "long_blink_ratio_pct": long_blink_ratio_pct,
        "dry_eye_risk_score": round(risk_score, 1),
        "dry_eye_risk_level": level,
        "debug_scores": f"F:{int(freq_score)} D:{int(dur_score)} C:{int(closure_score)} I:{int(inc_score)}"
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