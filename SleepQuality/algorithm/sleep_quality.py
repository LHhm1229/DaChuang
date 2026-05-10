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

def compute_alpha(fc: float, fs: float) -> float:
    """计算RC低通滤波器的alpha系数，使截止频率与采样率绑定"""
    dt = 1.0 / fs
    RC = 1.0 / (2 * np.pi * fc)
    return dt / (RC + dt)

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

    # 使用频率绑定的alpha系数
    smooth_alpha = compute_alpha(smooth_cutoff_hz, sampling_rate)
    filtered_signal = simple_lowpass(baseline_removed, alpha=smooth_alpha)

    # ✅ 问题1改进：使用抗异常值的robust normalization（5%和95%分位数）
    p5, p95 = np.percentile(filtered_signal, [5, 95])
    range_val = p95 - p5
    if range_val > 1e-12:
        normalized_signal = np.clip((filtered_signal - p5) / range_val, 0, 1)
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

    # ✅ 问题2改进：让alpha跟频率绑定
    # SEM (Slow Eye Movement) roughly 0.1-0.5 Hz，使用0.5Hz作为截止频率
    sem_alpha = compute_alpha(0.5, fs)
    sem_signal = simple_lowpass(eye_signal, alpha=sem_alpha)

    # REM (Rapid Eye Movement) roughly 1-5 Hz，使用5.0Hz作为截止频率
    rem_alpha = compute_alpha(5.0, fs)
    rem_signal = simple_lowpass(eye_signal, alpha=rem_alpha)

    return sem_signal, rem_signal


def detect_sem_events(
    sem_signal: np.ndarray,
    time: np.ndarray,
    fs: int,
    amp_thresh: float = 0.05,
    min_dur: float = 0.5
) -> List[Tuple[float, float, float]]:
    # ✅ 问题4改进：在zero-crossing之前先做平滑，减少噪声干扰
    sem_signal_smoothed = simple_lowpass(sem_signal, alpha=0.2)
    
    # ✅ 问题4改进：检查信号质量，避免低质量信号误检测
    if np.std(sem_signal_smoothed) < 0.02:
        return []
    
    zero_crossings = np.where(np.diff(np.sign(sem_signal_smoothed)))[0]
    events = []
    for i in range(len(zero_crossings) - 1):
        start = zero_crossings[i]
        end = zero_crossings[i + 1]
        dur = (end - start) / fs
        if dur >= min_dur:
            peak_amp = np.max(np.abs(sem_signal_smoothed[start:end]))
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
    """Simple peak detection without scipy.signal.find_peaks.
    
    ✅ 问题3改进：
    - 改进A：动态阈值 amp_thresh = max(0.1, 2 * np.std(rem_signal))
    - 改进B：增大最小间隔到0.3~0.4秒（最大频率≈3 Hz ≈180/min）
    - 改进C：增加"峰宽过滤"（去掉尖刺噪声）
    - 改进D：增加"生理上限保护"（max_rem_per_sec = 3）
    """
    # ✅ 改进A：动态阈值
    dynamic_thresh = max(0.1, 2 * np.std(rem_signal))
    thresh = max(amp_thresh, dynamic_thresh)
    
    # ✅ 改进B：增大最小间隔（直接封顶频率）
    min_dist_sec = max(min_dist_sec, 0.3)  # 推荐 0.3~0.4，最大频率≈3 Hz
    min_dist = int(min_dist_sec * fs)
    
    # ✅ 改进C：峰宽过滤 - 检查峰值前后点是否也超过阈值的50%
    def find_simple_peaks(x, thresh, dist):
        peaks = []
        last_peak = -dist
        for i in range(1, len(x) - 1):
            # 峰宽过滤：当前点>阈值，且前后点>阈值的50%
            if x[i] > thresh and x[i-1] > thresh * 0.5 and x[i+1] > thresh * 0.5:
                if x[i] > x[i-1] and x[i] > x[i+1]:
                    if i - last_peak >= dist:
                        peaks.append(i)
                        last_peak = i
        return np.array(peaks)

    peaks_pos = find_simple_peaks(rem_signal, thresh, min_dist)
    peaks_neg = find_simple_peaks(-rem_signal, thresh, min_dist)
    
    # ✅ 改进D：生理上限保护
    duration_sec = len(rem_signal) / fs
    max_rem_per_sec = 3
    max_total_rem = int(max_rem_per_sec * duration_sec)
    
    if len(peaks_pos) > max_total_rem:
        peaks_pos = peaks_pos[:max_total_rem]
    if len(peaks_neg) > max_total_rem:
        peaks_neg = peaks_neg[:max_total_rem]
    
    return peaks_pos, peaks_neg


def compute_epoch_eye_features(
    epoch_signal: np.ndarray,
    epoch_time: np.ndarray,
    fs: int
) -> Dict[str, float]:
    sem_sig, rem_sig = extract_eye_movement_bands(epoch_signal, fs)
    rem_pos, rem_neg = detect_rem_events(rem_sig, epoch_time, fs)
    sem_events = detect_sem_events(sem_sig, epoch_time, fs)

    # ✅ 问题5改进：REM密度约束（防止异常值）
    rem_density_raw = (len(rem_pos) + len(rem_neg)) / 30.0
    # 约束REM密度上限为3.0，超过5则判为噪声
    if rem_density_raw > 5:
        rem_density = 0  # 判为噪声
    else:
        rem_density = min(rem_density_raw, 3.0)
    
    # ✅ 新增：信号质量指标
    mean_abs = np.mean(np.abs(epoch_signal))
    signal_quality = np.std(epoch_signal) / (mean_abs + 1e-6) if mean_abs > 0 else 0.0

    feats = {
        'rem_density': rem_density,
        'sem_count': len(sem_events),
        'rem_energy': float(np.sum(rem_sig ** 2)),
        'sem_energy': float(np.sum(sem_sig ** 2)),
        'rem_sem_ratio': float(np.sum(rem_sig ** 2) / (np.sum(sem_sig ** 2) + 1e-6)),
        'signal_std': float(np.std(epoch_signal)),
        'signal_quality': float(signal_quality),
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
    
    # ✅ 问题6改进A：加入保护逻辑 - 信号过稳定强制判为深睡，避免假REM
    if signal_std < 0.02:
        return 3  # 强制深睡，避免假REM
    
    # 1. 首先检查深睡 - 信号非常稳定（标准差很小）
    if signal_std < 0.03:
        return 3  # 深睡 - 稳定的低值信号
    
    # 2. 检查清醒 - 高变异性或有明显眼动
    if signal_std > 0.25 or sem_count > 10 or (rem_density > 3 and sem_count > 3):
        return 0  # 清醒 - 高变异性
    
    # 3. 检查REM - 中等变异性 + 较高REM密度 + 较高REM能量
    if rem_density > 2.0 and rem_energy > 1.0:
        stage = 4  # REM
    # 4. 检查浅睡N1 - 有一定SEM活动但REM密度低
    elif sem_count >= 3 and sem_count <= 10 and rem_density < 1.0:
        stage = 1  # 浅睡N1
    # 5. 检查浅睡N2 - 低REM密度，适度SEM活动
    elif rem_density < 2.0 and sem_count < 15:
        stage = 2  # 浅睡N2
    else:
        # 默认返回前一状态或浅睡N2
        stage = prev_stage if prev_stage is not None else 2
    
    # ✅ 问题6改进B：加入阶段平滑（防止N3→REM等突变）
    if prev_stage is not None:
        if abs(stage - prev_stage) > 2:
            stage = prev_stage
    
    return stage


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
            "signal_std": 0,
            "signal_quality": 0
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
    
    # ✅ 问题8改进：使用简单平均代替加权平均，更稳定
    # 计算基于阶段序列的分数
    stage_scores_list = [stage_scores.get(s, 60) for s in stage_sequence]
    stage_based_score = np.mean(stage_scores_list) if stage_scores_list else 60
    
    # 结合当前阶段
    current_stage_score = stage_scores.get(current_stage, 60)
    base_score = (stage_based_score * 0.6 + current_stage_score * 0.4)
    
    # 考虑睡眠效率
    efficiency_bonus = min(se / 100, 1.0) * 10
    base_score += efficiency_bonus
    
    # ✅ 问题7改进：REM比例奖励（修复可能异常的问题）
    rem_ratio = rem_epochs / n_epochs if n_epochs > 0 else 0
    optimal_rem_ratio = 0.2
    # 使用max(0, ...)确保奖励不会为负
    rem_score = max(0, 100 - abs(rem_ratio - optimal_rem_ratio) / 0.2 * 50)
    rem_bonus = rem_score / 100 * 5
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
        "signal_quality": round(last_feats.get('signal_quality', 0), 4),
        "totalMinutes": round(total_minutes, 1),
        "tstMinutes": round(tst_min, 1),
        "stageSequence": stage_sequence.tolist()
    }