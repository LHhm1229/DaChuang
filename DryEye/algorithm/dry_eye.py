from __future__ import annotations

from typing import Tuple, Dict, List
import numpy as np
from scipy import signal
from scipy.ndimage import median_filter

__all__ = [
    "preprocess_and_calibrate",
    "detect_blink_events_wavelet",
    "compute_dry_eye_metrics",
    "assess_dry_eye_risk",
    "run_dry_eye_pipeline",
]


def sigmoid(x: np.ndarray, midpoint: float = 0.0, steepness: float = 1.0) -> np.ndarray:
    """Sigmoid 函数，用于平滑过渡"""
    return 1 / (1 + np.exp(-steepness * (x - midpoint)))


def quantile_normalize(
    signal: np.ndarray,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95
) -> np.ndarray:
    """
    分位数归一化 - 解决全局极值导致的信号压缩问题
    使用 5% 和 95% 分位数代替绝对极值
    """
    lower = np.quantile(signal, lower_quantile)
    upper = np.quantile(signal, upper_quantile)
    range_val = upper - lower
    
    if range_val < 1e-6:
        return (signal - np.mean(signal)) / (np.std(signal) + 1e-6)
    
    normalized = (signal - lower) / range_val
    # 裁剪到 [0, 1] 范围
    normalized = np.clip(normalized, 0, 1)
    return normalized


def highpass_filter(
    signal: np.ndarray,
    sampling_rate: int,
    cutoff_freq: float = 0.5
) -> np.ndarray:
    """
    高通滤波 - 去除基线漂移
    使用 Butterworth 滤波器设计
    """
    nyquist = 0.5 * sampling_rate
    b, a = signal.butter(4, cutoff_freq / nyquist, btype='high')
    return signal.filtfilt(b, a, signal)


def detect_blink_events_wavelet(
    signal_norm: np.ndarray,
    signal_raw: np.ndarray,
    sampling_rate: int = 100,
    amplitude_thresh: float = 0.05,
    min_duration_ms: float = 30,
    max_duration_ms: float = 2000,
    refractory_ms: float = 100
) -> List[Dict]:
    """
    基于一阶差分与形态学的眨眼事件检测
    
    改进点：
    1. 使用 scipy 中值滤波替代纯 Python 实现
    2. 增加伪影识别（基于波形对称性和斜率合理性）
    3. 动态基线追踪
    4. 使用原始信号幅值判断不完全眨眼
    """
    events = []
    n = len(signal_norm)
    refractory_samples = int(refractory_ms * sampling_rate / 1000)
    min_duration_samples = int(min_duration_ms * sampling_rate / 1000)
    max_duration_samples = int(max_duration_ms * sampling_rate / 1000)

    # 使用 scipy 中值滤波（C语言实现，性能提升10x+）
    window_size = max(3, int(sampling_rate * 0.02))
    if window_size % 2 == 0:
        window_size += 1
    smoothed = median_filter(signal_norm, size=window_size)
    
    # 计算差分和二阶差分（用于形态学分析）
    diff = np.diff(smoothed)
    diff2 = np.diff(diff)  # 二阶差分用于判断波形对称性

    # 动态基线追踪 - 使用滑动窗口中值
    baseline_window = int(sampling_rate * 0.5)  # 500ms 窗口
    baseline = signal.medfilt(signal_norm, baseline_window)

    i = 0
    while i < n - 1:
        # 不应期检查
        if i < refractory_samples:
            i += 1
            continue

        # 检测眨眼起始（负斜率）
        if diff[i] < -amplitude_thresh / 3:
            start = i
            
            # 寻找波谷
            valley = start
            while valley < n - 2 and smoothed[valley + 1] <= smoothed[valley]:
                valley += 1
            
            # 寻找恢复点（使用动态基线）
            end = valley
            target_level = baseline[start] - amplitude_thresh * 0.3
            while end < n - 1 and smoothed[end] < target_level:
                end += 1

            # 检查持续时间是否在合理范围
            duration_samples = end - start
            if duration_samples > max_duration_samples or duration_samples < min_duration_samples:
                i = valley + 1
                continue

            # 计算振幅（同时使用归一化信号和原始信号）
            norm_amplitude = smoothed[start] - smoothed[valley]
            raw_amplitude = np.max(signal_raw[start:end+1]) - np.min(signal_raw[start:end+1])
            
            # 形态学过滤 - 检测伪影
            # 1. 检查波形对称性（上升沿与下降沿时长比例）
            rise_time = valley - start
            fall_time = end - valley
            symmetry_ratio = min(rise_time, fall_time) / (max(rise_time, fall_time) + 1e-6)
            
            # 2. 检查斜率合理性（使用二阶差分方差判断平滑度）
            segment_diff2 = diff2[start:end] if end - start > 2 else np.array([])
            slope_variance = np.var(segment_diff2) if len(segment_diff2) > 0 else 0
            
            # 3. 检查是否为有效眨眼
            is_valid_blink = (
                norm_amplitude >= amplitude_thresh and
                symmetry_ratio > 0.3 and  # 至少有一定对称性
                slope_variance < 0.1       # 斜率变化不应过于剧烈
            )

            if is_valid_blink:
                duration_sec = duration_samples / sampling_rate
                events.append({
                    'start': start,
                    'valley': valley,
                    'end': end,
                    'amplitude': norm_amplitude,
                    'raw_amplitude': raw_amplitude,
                    'duration_sec': duration_sec,
                    'duration_ms': duration_sec * 1000,
                    'symmetry_ratio': symmetry_ratio,
                    'is_incomplete': raw_amplitude < 0.5  # 使用原始信号判断不完全眨眼
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
    """
    计算干眼症相关指标
    """
    n_blinks = len(events)
    if n_blinks == 0:
        return {
            'blink_rate_per_min': 0,
            'avg_blink_duration_ms': 0,
            'eye_closure_ratio_pct': 0,
            'incomplete_blink_ratio_pct': 100.0,
            'long_blink_ratio_pct': 0,
            'total_blinks': 0,
            'incomplete_blinks': 0,
            'long_blinks': 0,
            'avg_symmetry_ratio': 0.0
        }

    durations_ms = [e['duration_ms'] for e in events]
    amplitudes = [e['amplitude'] for e in events]
    raw_amplitudes = [e['raw_amplitude'] for e in events]
    symmetries = [e['symmetry_ratio'] for e in events]

    avg_dur_ms = np.mean(durations_ms)
    avg_symmetry = np.mean(symmetries)
    rate_per_min = n_blinks / (total_duration_sec / 60)
    total_blink_sec = sum(e['duration_sec'] for e in events)
    closure_ratio = (total_blink_sec / total_duration_sec) * 100
    closure_ratio = min(closure_ratio, 100.0)

    # 使用原始信号幅值判断不完全眨眼（而非归一化后的值）
    # 不完全眨眼的判定基于原始信号的物理特性
    avg_raw_amplitude = np.mean(raw_amplitudes) if raw_amplitudes else 0
    # 动态阈值：基于所有眨眼的平均幅值来判断
    incomplete_thresh = avg_raw_amplitude * 0.6  # 低于平均幅值60%视为不完全眨眼
    incomplete_count = sum(1 for a in raw_amplitudes if a < incomplete_thresh)
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
        'long_blinks': long_blink_count,
        'avg_symmetry_ratio': round(avg_symmetry, 3),
        'avg_raw_amplitude': round(avg_raw_amplitude, 3)
    }
    
    print(f"[ALGO] 检测到 {n_blinks} 次眨眼 | 频率={result['blink_rate_per_min']}/min | 闭合={result['eye_closure_ratio_pct']}% | 不完全={result['incomplete_blink_ratio_pct']}%")
    return result


def assess_dry_eye_risk(
    blink_rate: float,
    avg_dur_ms: float,
    closure_ratio: float,
    incomplete_ratio_pct: float,
    long_blink_ratio_pct: float = 0,
    avg_symmetry_ratio: float = 0.5
) -> Tuple[float, str, Dict]:
    """
    评估干眼症风险
    
    改进点：使用 Sigmoid 函数替代硬编码分段函数，实现平滑过渡
    """
    
    # 1. 频率得分 (U型曲线：正常 15-25次/分钟)
    # 使用两个 Sigmoid 函数组合实现 U 型曲线
    freq_low = sigmoid(blink_rate, midpoint=15, steepness=-0.3)  # 低于15时风险增加
    freq_high = sigmoid(blink_rate, midpoint=25, steepness=0.2)  # 高于25时风险增加
    freq_score = 100 * (freq_low * freq_high + (1 - freq_low) * (1 - freq_high))
    # 调整：正常范围内得分低，两端得分高
    freq_score = 100 * (sigmoid(blink_rate, 10, -0.4) + sigmoid(blink_rate, 30, 0.4)) / 2

    # 2. 时长得分 (U型曲线：正常 100-250ms)
    dur_low = sigmoid(avg_dur_ms, midpoint=100, steepness=-0.02)
    dur_high = sigmoid(avg_dur_ms, midpoint=250, steepness=0.01)
    dur_score = 100 * (sigmoid(avg_dur_ms, 75, -0.03) + sigmoid(avg_dur_ms, 300, 0.015)) / 2

    # 3. 闭合比例得分 (U型曲线：正常 3% - 8%)
    closure_score = 100 * (sigmoid(closure_ratio, 2, -2) + sigmoid(closure_ratio, 10, 1.5)) / 2

    # 4. 不完全眨眼得分 (递增曲线)
    inc_score = 100 * sigmoid(incomplete_ratio_pct, midpoint=40, steepness=0.08)

    # 5. 长时间眨眼得分 (递增曲线)
    long_score = 100 * sigmoid(long_blink_ratio_pct, midpoint=20, steepness=0.15)

    # 6. 对称性得分 (波形质量)
    symmetry_score = 100 * (1 - sigmoid(avg_symmetry_ratio, midpoint=0.6, steepness=10))

    weights = {
        'freq': 0.15,
        'duration': 0.15,
        'closure': 0.25,
        'incomplete': 0.25,
        'long': 0.10,
        'symmetry': 0.10
    }
    
    risk_score = (
        freq_score * weights['freq'] +
        dur_score * weights['duration'] +
        closure_score * weights['closure'] +
        inc_score * weights['incomplete'] +
        long_score * weights['long'] +
        symmetry_score * weights['symmetry']
    )

    # 如果频率为0，强制高风险
    if blink_rate == 0:
        risk_score = max(risk_score, 90.0)

    risk_score = min(100.0, max(0.0, risk_score))

    # 风险等级（使用平滑过渡）
    risk_levels = ["低风险", "中风险", "高风险"]
    level_index = np.digitize(risk_score, [30, 60])
    level = risk_levels[min(level_index, 2)]

    detail = {
        "blink_rate_per_min": blink_rate,
        "avg_blink_duration_ms": avg_dur_ms,
        "closure_sec_per_min": round(closure_ratio / 100 * 60, 2),
        "incomplete_blink_ratio_pct": incomplete_ratio_pct,
        "long_blink_ratio_pct": long_blink_ratio_pct,
        "avg_symmetry_ratio": avg_symmetry_ratio,
        "dry_eye_risk_score": round(risk_score, 1),
        "dry_eye_risk_level": level,
        "debug_scores": (
            f"F:{int(freq_score)} D:{int(dur_score)} C:{int(closure_score)} "
            f"I:{int(inc_score)} L:{int(long_score)} S:{int(symmetry_score)}"
        )
    }
    
    return risk_score, level, detail


def preprocess_and_calibrate(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    highpass_cutoff: float = 0.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    预处理和校准信号
    
    改进点：
    1. 分位数归一化替代全局极值归一化
    2. 高通滤波去除基线漂移
    3. 保留原始信号用于后续分析
    """
    # 保存原始信号副本用于不完全眨眼判断
    signal_raw = raw_signal.copy()
    
    # 高通滤波去除基线漂移
    filtered = highpass_filter(raw_signal, sampling_rate, highpass_cutoff)
    
    # 分位数归一化（使用5%和95%分位数）
    normalized = quantile_normalize(filtered, lower_quantile=0.05, upper_quantile=0.95)

    # 校正极性：确保眨眼特征表现为向下的波谷
    if len(normalized) > 1:
        diff = np.diff(normalized)
        neg_ratio = np.sum(diff < 0) / len(diff)
        if neg_ratio < 0.4:
            normalized = 1 - normalized

    return normalized, signal_raw


def run_dry_eye_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    duration_sec: float = None
) -> Dict:
    """
    运行完整的干眼症检测流程
    """
    # 预处理（返回归一化信号和原始信号）
    signal_norm, signal_raw = preprocess_and_calibrate(raw_signal, sampling_rate)
    
    # 检测眨眼事件（传入原始信号用于不完全眨眼判断）
    events = detect_blink_events_wavelet(signal_norm, signal_raw, sampling_rate)

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
        long_blink_ratio_pct=metrics['long_blink_ratio_pct'],
        avg_symmetry_ratio=metrics['avg_symmetry_ratio']
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
        "avgSymmetryRatio": metrics['avg_symmetry_ratio'],
        "details": detail
    }
    return result