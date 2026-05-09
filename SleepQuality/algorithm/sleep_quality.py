from __future__ import annotations

from typing import Tuple, List, Dict, Optional

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

def simple_highpass(x, alpha=0.9):
    """A simple RC highpass filter implementation without scipy."""
    res = np.zeros_like(x)
    if len(x) == 0: return res
    res[0] = x[0]
    for i in range(1, len(x)):
        res[i] = alpha * (res[i-1] + x[i] - x[i-1])
    return res

def simple_grey_erosion(x, size):
    """A simple 1D grey erosion implementation."""
    res = np.zeros_like(x)
    half = size // 2
    for i in range(len(x)):
        start = max(0, i - half)
        end = min(len(x), i + half + 1)
        res[i] = np.min(x[start:end])
    return res

def simple_grey_dilation(x, size):
    """A simple 1D grey dilation implementation."""
    res = np.zeros_like(x)
    half = size // 2
    for i in range(len(x)):
        start = max(0, i - half)
        end = min(len(x), i + half + 1)
        res[i] = np.max(x[start:end])
    return res

__all__ = [
    "preprocess_eyelid_signal",
    "adaptive_preprocess_eyelid_signal",
    "extract_eye_movement_bands",
    "detect_sem_events",
    "detect_rem_events",
    "compute_epoch_eye_features",
    "rule_based_sleep_staging",
    "analyze_sleep_from_eyelid_sensor",
    "run_sleep_quality_pipeline",
]


def _grey_opening(signal_arr: np.ndarray, size: int) -> np.ndarray:
    eroded = simple_grey_erosion(signal_arr, size=size)
    dilated = simple_grey_dilation(eroded, size=size)
    return dilated


def _grey_closing(signal_arr: np.ndarray, size: int) -> np.ndarray:
    dilated = simple_grey_dilation(signal_arr, size=size)
    eroded = simple_grey_erosion(dilated, size=size)
    return eroded


def preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    drift_window_sec: float = 2.0,
    smooth_cutoff_hz: float = 6.5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(raw_signal, dtype=float)
    if x.ndim != 1 or x.size < max(50, sampling_rate):
        centered = x - np.mean(x) if x.size > 0 else x
        return centered, centered, centered

    centered_signal = x - np.mean(x)

    size_drift = int(max(3, round(drift_window_sec * sampling_rate)))
    trend_open = _grey_opening(centered_signal, size=size_drift)
    trend_base = _grey_closing(trend_open, size=size_drift)
    baseline_removed = centered_signal - trend_base

    # Use simple_lowpass instead of scipy.signal.butter/filtfilt
    filtered_signal = simple_lowpass(baseline_removed, alpha=0.3)

    min_val = float(np.min(filtered_signal))
    max_val = float(np.max(filtered_signal))
    if max_val - min_val > 1e-12:
        normalized_signal = (filtered_signal - min_val) / (max_val - min_val)
    else:
        normalized_signal = filtered_signal.copy()

    return filtered_signal, normalized_signal, trend_base


def adaptive_preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return preprocess_eyelid_signal(raw_signal, sampling_rate)


def extract_eye_movement_bands(
    preprocessed_signal: np.ndarray,
    fs: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    # Use simple filters instead of scipy.signal.butter/sosfilt
    eye_signal = simple_highpass(preprocessed_signal, alpha=0.95)

    # SEM (Slow Eye Movement) roughly 0.1-0.5 Hz
    sem_signal = simple_lowpass(eye_signal, alpha=0.1)

    # REM (Rapid Eye Movement) roughly 1-5 Hz
    rem_signal = simple_lowpass(eye_signal, alpha=0.3)

    return sem_signal, rem_signal


def detect_sem_events(
    sem_signal: np.ndarray,
    time: np.ndarray,
    fs: int,
    amp_thresh: float = 0.05,
    min_dur: float = 0.5
) -> List[Tuple[float, float, float]]:
    zero_crossings = np.where(np.diff(np.sign(sem_signal)))[0]
    events = []
    for i in range(len(zero_crossings) - 1):
        start = zero_crossings[i]
        end = zero_crossings[i + 1]
        dur = (end - start) / fs
        if dur >= min_dur:
            peak_amp = np.max(np.abs(sem_signal[start:end]))
            if peak_amp >= amp_thresh:
                events.append((time[start], time[end], peak_amp))
    return events


def detect_rem_events(
    rem_signal: np.ndarray,
    time: np.ndarray,
    fs: int,
    amp_thresh: float = 0.1,
    min_dist_sec: float = 0.1
) -> Tuple[np.ndarray, np.ndarray]:
    """Simple peak detection without scipy.signal.find_peaks."""
    min_dist = int(min_dist_sec * fs)
    
    def find_simple_peaks(x, thresh, dist):
        peaks = []
        last_peak = -dist
        for i in range(1, len(x) - 1):
            if x[i] > thresh and x[i] > x[i-1] and x[i] > x[i+1]:
                if i - last_peak >= dist:
                    peaks.append(i)
                    last_peak = i
        return np.array(peaks)

    peaks_pos = find_simple_peaks(rem_signal, amp_thresh, min_dist)
    peaks_neg = find_simple_peaks(-rem_signal, amp_thresh, min_dist)
    return peaks_pos, peaks_neg


def compute_epoch_eye_features(
    epoch_signal: np.ndarray,
    epoch_time: np.ndarray,
    fs: int
) -> Dict[str, float]:
    sem_sig, rem_sig = extract_eye_movement_bands(epoch_signal, fs)
    rem_pos, rem_neg = detect_rem_events(rem_sig, epoch_time, fs)
    sem_events = detect_sem_events(sem_sig, epoch_time, fs)

    feats = {
        'rem_density': (len(rem_pos) + len(rem_neg)) / 30.0,
        'sem_count': len(sem_events),
        'rem_energy': float(np.sum(rem_sig ** 2)),
        'sem_energy': float(np.sum(sem_sig ** 2)),
        'rem_sem_ratio': float(np.sum(rem_sig ** 2) / (np.sum(sem_sig ** 2) + 1e-6)),
        'signal_std': float(np.std(epoch_signal)),
    }
    return feats


def rule_based_sleep_staging(
    features: Dict[str, float],
    prev_stage: Optional[int] = None
) -> int:
    signal_std = features['signal_std']
    rem_density = features['rem_density']
    sem_count = features['sem_count']
    rem_energy = features['rem_energy']
    
    # 1. 首先检查深睡 - 信号非常稳定（标准差很小）
    if signal_std < 0.03:
        return 3  # 深睡 - 稳定的低值信号
    
    # 2. 检查清醒 - 高变异性或有明显眼动
    if signal_std > 0.25 or sem_count > 10 or (rem_density > 5 and sem_count > 3):
        return 0  # 清醒 - 高变异性
    
    # 3. 检查REM - 中等变异性 + 较高REM密度 + 较高REM能量
    if rem_density > 2.0 and rem_energy > 1.0:
        return 4  # REM
    
    # 4. 检查浅睡N1 - 有一定SEM活动但REM密度低
    if sem_count >= 3 and sem_count <= 10 and rem_density < 1.0:
        return 1  # 浅睡N1
    
    # 5. 检查浅睡N2 - 低REM密度，适度SEM活动
    if rem_density < 2.0 and sem_count < 15:
        return 2  # 浅睡N2
    
    # 默认返回前一状态或浅睡N2
    return prev_stage if prev_stage is not None else 2


def analyze_sleep_from_eyelid_sensor(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    epoch_duration_sec: int = 30
) -> Tuple[np.ndarray, List[Dict]]:
    filtered, normalized, baseline = preprocess_eyelid_signal(raw_signal, sampling_rate)

    total_duration = len(normalized) / sampling_rate
    time_axis = np.linspace(0, total_duration, len(normalized))

    epoch_samples = epoch_duration_sec * sampling_rate
    # 确保至少有 1 个 epoch，即使数据不足 30s 也可以进行初步分析
    n_epochs = max(1, len(normalized) // epoch_samples)

    stage_sequence = []
    epoch_features_list = []

    prev_stage = None
    for i in range(n_epochs):
        start_idx = i * epoch_samples
        end_idx = min(start_idx + epoch_samples, len(normalized))
        
        # 如果最后一个 epoch 太短（不足 5s），跳过
        if end_idx - start_idx < 5 * sampling_rate and i > 0:
            continue
            
        epoch_sig = normalized[start_idx:end_idx]
        epoch_t = time_axis[start_idx:end_idx]

        feats = compute_epoch_eye_features(epoch_sig, epoch_t, sampling_rate)
        epoch_features_list.append(feats)

        stage = rule_based_sleep_staging(feats, prev_stage)
        stage_sequence.append(stage)
        prev_stage = stage

    return np.array(stage_sequence), epoch_features_list


def run_sleep_quality_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100
) -> Dict:
    stage_sequence, epoch_features_list = analyze_sleep_from_eyelid_sensor(
        raw_signal, sampling_rate
    )

    epoch_duration_sec = 30
    n_epochs = len(stage_sequence)
    
    if n_epochs == 0:
        return {
            "qualityScore": 50,
            "currentStage": 2,
            "currentStageName": "浅睡N2",
            "sleepEfficiency": 0,
            "rem_density": 0,
            "sem_count": 0,
            "signal_std": 0
        }

    total_minutes = n_epochs * epoch_duration_sec / 60.0

    wake_epochs = int(np.sum(stage_sequence == 0))
    n1_epochs = int(np.sum(stage_sequence == 1))
    n2_epochs = int(np.sum(stage_sequence == 2))
    n3_epochs = int(np.sum(stage_sequence == 3))
    rem_epochs = int(np.sum(stage_sequence == 4))

    def to_minutes(epochs):
        return epochs * epoch_duration_sec / 60.0

    tst_min = to_minutes(n1_epochs + n2_epochs + n3_epochs + rem_epochs)
    se = (tst_min / total_minutes * 100) if total_minutes > 0 else 0.0

    current_stage = int(stage_sequence[-1]) if len(stage_sequence) > 0 else 2
    
    # 基础阶段分数
    stage_scores = {
        0: 20,   # 清醒
        1: 45,   # 浅睡N1
        2: 65,   # 浅睡N2
        4: 80,   # REM
        3: 95    # 深睡
    }
    
    # 各阶段权重
    stage_weights = {
        0: 0.3,
        1: 0.5,
        2: 0.7,
        4: 0.85,
        3: 0.95
    }
    
    # 计算加权平均阶段分数
    weighted_sum = 0
    total_weight = 0
    for stage, weight in stage_weights.items():
        count = int(np.sum(stage_sequence == stage))
        weighted_sum += count * weight * 100
        total_weight += count * weight
    
    stage_based_score = weighted_sum / total_weight if total_weight > 0 else 60
    
    # 结合当前阶段
    current_stage_score = stage_scores.get(current_stage, 60)
    base_score = (stage_based_score * 0.6 + current_stage_score * 0.4)
    
    # 考虑睡眠效率
    efficiency_bonus = min(se / 100, 1.0) * 10
    base_score += efficiency_bonus
    
    # REM比例奖励
    rem_ratio = rem_epochs / n_epochs if n_epochs > 0 else 0
    optimal_rem_ratio = 0.2
    rem_score = 100 - abs(rem_ratio - optimal_rem_ratio) / 0.2 * 50
    rem_bonus = max(0, rem_score / 100 * 5)
    base_score += rem_bonus
    
    # 限制在 10-100 范围内
    score = max(10, min(100, base_score))
    
    # 获取最后一个 epoch 的特征用于输出
    last_feats = epoch_features_list[-1] if epoch_features_list else {}
    
    stage_names = {0: "清醒", 1: "浅睡N1", 2: "浅睡N2", 3: "深睡", 4: "REM"}

    return {
        "qualityScore": round(score),
        "currentStage": current_stage,
        "currentStageName": stage_names.get(current_stage, "未知"),
        "sleepEfficiency": round(se, 1),
        "rem_density": round(last_feats.get('rem_density', 0), 2),
        "sem_count": last_feats.get('sem_count', 0),
        "signal_std": round(last_feats.get('signal_std', 0), 4),
        "totalMinutes": round(total_minutes, 1),
        "tstMinutes": round(tst_min, 1),
        "stageSequence": stage_sequence.tolist()
    }