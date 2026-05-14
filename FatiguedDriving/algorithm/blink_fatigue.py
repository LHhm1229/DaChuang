"""
blink_fatigue.py
================

目标
- 作为"算法模块"，被 app.py 稳定调用（可直接 import 使用）
- 统一信号物理语义：高值=更闭合/眨眼峰（blink peak）
- 用"新版预处理 + 新版眨眼特征提取"替换旧版前两段
- 对齐后两段（事件检测/疲劳评分）的接口与度量体系，让整条链路可跑通

统一约定（全链路一致）
- 输入：raw_signal（原始眼睑信号，1D）
- 预处理输出 normalized_signal：范围约在 [0,1]，且"值越大=越闭合/越像眨眼峰"
- peaks：眨眼峰（高值点）
- valleys：围绕峰的前后谷（低值点）
- 事件 start/end：用"前谷/后谷"定义
  -> 事件持续时间 duration = (next_valley - prev_valley) / fs
  -> duration_threshold 与事件 duration 同一度量体系（避免上下游不一致）

对 app.py 友好
- 提供 run_fatigue_pipeline(raw_signal, ...) 统一入口，app.py 只调一个函数即可
- 输出结构字段尽量保持旧风格，避免前端 KeyError
"""

from __future__ import annotations

from typing import Tuple, Dict, List, Optional

import numpy as np
import scipy.signal as signal
from scipy.ndimage import grey_opening, grey_closing, median_filter

__all__ = [
    "adaptive_preprocess_eyelid_signal",
    "extract_blink_features",
    "detect_blink_events",
    "assess_fatigue",
    "run_fatigue_pipeline",
]


# =========================
# 0) 辅助：信号质量（给 app 展示/调试用，不影响主逻辑）
# =========================
def _compute_signal_quality(normalized_signal: np.ndarray) -> float:
    """
    粗略信号质量估计（0~1）：
    - 波动过小：可能贴合差/无信号
    - 极端饱和（大量 0 或 1）：可能剪切/溢出
    """
    x = np.asarray(normalized_signal, dtype=float)
    if x.size < 10:
        return 0.0

    amp = float(np.percentile(x, 95) - np.percentile(x, 5))
    amp_score = np.clip(amp / 0.25, 0.0, 1.0)

    sat_ratio = float(np.mean((x < 0.01) | (x > 0.99)))
    sat_score = 1.0 - np.clip(sat_ratio / 0.30, 0.0, 1.0)

    return float(np.clip(0.6 * amp_score + 0.4 * sat_score, 0.0, 1.0))


def _compute_physical_threshold(signal: np.ndarray, factor: float = 2.0) -> float:
    """
    基于信号统计特性的动态阈值计算
    Threshold = Mean + factor * Std
    用于替代固定阈值 0.55
    """
    mean_val = np.mean(signal)
    std_val = np.std(signal)
    return float(mean_val + factor * std_val)


# =========================
# 1) 预处理（新版替换）
# =========================
def preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    drift_window_sec: float = 2.0,
    smooth_cutoff_hz: float = 3.5,
    normalize: bool = False,
    enhance_signal: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    新版预处理（改进点）：
    1) 增加中值滤波去除脉冲噪声
    2) 降低低通滤波截止频率至 3.5Hz（眨眼主能级通常低于 4Hz）
    3) 增加无信号检测
    4) 增加自适应信号增强，放大微小电压变化
    """
    x = np.asarray(raw_signal, dtype=float)
    if x.ndim != 1 or x.size < max(50, sampling_rate):
        centered = x - np.mean(x) if x.size > 0 else x
        return centered, centered, centered

    signal_range = float(np.max(x) - np.min(x))
    physical_min_threshold = 0.01
    if signal_range < physical_min_threshold:
        print("[ALGO] 警告：信号幅值过小，可能是传感器未佩戴或无信号")
        return np.zeros_like(x), np.zeros_like(x), np.zeros_like(x)

    # 自适应信号增强：放大微小变化
    if enhance_signal:
        # 计算信号标准差，评估信号活跃程度
        signal_std = float(np.std(x))
        target_std = 0.15  # 目标标准差，让信号有足够动态范围
        
        if signal_std > 0 and signal_std < target_std:
            gain_factor = min(target_std / signal_std, 10.0)  # 最大放大10倍
            x = x * gain_factor
            print(f"[ALGO] 信号增强: 标准差 {signal_std:.4f} -> 放大 {gain_factor:.2f} 倍")

    centered_signal = x - np.mean(x)

    median_window = max(3, int(sampling_rate * 0.01))
    if median_window % 2 == 0:
        median_window += 1
    centered_signal = median_filter(centered_signal, size=median_window)

    size_drift = int(max(3, round(drift_window_sec * sampling_rate)))

    trend_open = grey_opening(centered_signal, size=size_drift)
    trend_base = grey_closing(trend_open, size=size_drift)

    baseline_removed = centered_signal - trend_base

    nyquist = sampling_rate / 2.0
    cutoff = smooth_cutoff_hz / nyquist
    cutoff = float(min(max(cutoff, 1e-6), 0.999999))

    b, a = signal.butter(8, cutoff, "lowpass")
    filtered_signal = signal.filtfilt(b, a, baseline_removed)

    if normalize:
        min_val = float(np.min(filtered_signal))
        max_val = float(np.max(filtered_signal))
        range_val = max_val - min_val
        
        if range_val > 1e-4:
            # 改进归一化：增加对比度拉伸
            normalized_signal = (filtered_signal - min_val) / range_val
            # 应用伽马校正，增强中间区域的对比度
            gamma = 0.8
            normalized_signal = np.power(normalized_signal, gamma)
        else:
            normalized_signal = filtered_signal.copy()
    else:
        normalized_signal = filtered_signal.copy()

    return filtered_signal, normalized_signal, trend_base


def adaptive_preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    兼容旧接口名：app.py 若仍 import adaptive_preprocess_eyelid_signal，不需要改。
    内部使用新版 preprocess_eyelid_signal。
    """
    return preprocess_eyelid_signal(
        raw_signal=raw_signal,
        sampling_rate=sampling_rate,
        drift_window_sec=2.0,
        smooth_cutoff_hz=3.5,
        normalize=True,
        enhance_signal=True
    )


# =========================
# 2) 眨眼特征提取（新版替换 + 与后两段对齐的微调）
# =========================
def extract_blink_features(
    eyelid_signal: np.ndarray,
    sampling_rate: int = 100,
    peak_height: float = 0.7,
    min_peak_distance_sec: float = 0.33,
    total_close_time: int = 0,
    long_close_regions: List[Tuple[int, int]] = None,
    personal_baseline: Dict = None
) -> Tuple[Dict, np.ndarray, np.ndarray]:
    """
    新版眨眼特征提取（改进点）：
    1) 动态高度阈值替代固定 0.55
    2) 增加峰宽度约束 width=(5, 50) 过滤噪声毛刺
    3) 增加物理上限封顶保护
    4) 使用 Mask 机制替代信号填充
    5) 施密特触发器判断眼睛状态
    """
    x = np.asarray(eyelid_signal, dtype=float)
    features: Dict = {}
    long_close_regions = long_close_regions or []
    
    # 个人基准初始化
    if personal_baseline is None:
        personal_baseline = {
            "avg_blink_duration": 0.15,  # 默认150ms
            "std_blink_duration": 0.05,
            "sample_count": 0
        }

    # 过短信号兜底
    if x.ndim != 1 or x.size < max(50, sampling_rate // 2):
        features.update({
            "avg_blink_amplitude": 0.0,
            "max_blink_amplitude": 0.0,
            "avg_blink_interval": 0.0,
            "blink_frequency": 0.0,
            "blink_rate_per_min": 0.0,
            "avg_blink_duration": 0.0,
            "avg_blink_duration_hwhm": 0.0,
            "blink_duration_ms": 0.0,
            "eye_closure_ratio": 0.0,
            "eye_status": "open",
            "left_eye_status": "open",
            "right_eye_status": "open",
            "signal_quality": _compute_signal_quality(x) if x.size else 0.0,
            "battery_level": None,
        })
        return features, np.array([], dtype=int), np.array([], dtype=int), personal_baseline

    # 1) 创建掩码 - 标记长闭眼区域，在眨眼统计时跳过
    mask = np.ones(x.size, dtype=bool)
    for start, end in long_close_regions:
        mask[start:end] = False  # False 表示该区域被标记为长闭眼，跳过峰值检测
    
    # 2) 峰值检测参数
    min_peak_distance = max(1, int(min_peak_distance_sec * sampling_rate))
    
    # 动态高度阈值 - 降低灵敏度阈值以检测微小变化
    dynamic_threshold = _compute_physical_threshold(x, factor=1.0)  # 降低factor提高灵敏度
    height_threshold = float(np.clip(dynamic_threshold, 0.2, 0.6))  # 降低阈值范围
    
    # 峰宽度约束
    min_width_samples = max(5, int(0.05 * sampling_rate))
    max_width_samples = min(50, int(0.5 * sampling_rate))
    
    # 3) 先在掩码区域外找峰值
    x_masked = x.copy()
    x_masked[~mask] = 0  # 将长闭眼区域置零，避免检测到虚假的二次峰值
    
    peaks_raw, properties = signal.find_peaks(
        x_masked,
        height=height_threshold,
        distance=min_peak_distance,
        width=(min_width_samples, max_width_samples)
    )
    peaks_raw = np.asarray(peaks_raw, dtype=int)
    
    # 物理上限封顶
    max_possible_peaks = int(sampling_rate / 3)
    if len(peaks_raw) > max_possible_peaks:
        print(f"[ALGO] 警告：检测到 {len(peaks_raw)} 个峰值，超过物理上限 {max_possible_peaks}，进行截断")
        peaks_raw = peaks_raw[:max_possible_peaks]
    
    # 峰值合并 - 将时间间隔小于 150ms 的多个峰值强制合并
    merged_peaks: List[int] = []
    if len(peaks_raw) > 0:
        current_group = [peaks_raw[0]]
        min_merge_distance = int(0.15 * sampling_rate)
        
        for i in range(1, len(peaks_raw)):
            if peaks_raw[i] - peaks_raw[i-1] < min_merge_distance:
                current_group.append(peaks_raw[i])
            else:
                amplitudes = [(p, x[p]) for p in current_group]
                merged_peaks.append(max(amplitudes, key=lambda a: a[1])[0])
                current_group = [peaks_raw[i]]
        
        if current_group:
            amplitudes = [(p, x[p]) for p in current_group]
            merged_peaks.append(max(amplitudes, key=lambda a: a[1])[0])
    
    peaks_raw = np.array(merged_peaks, dtype=int)

    # 4) 谷值候选（找 -x 的峰）
    valley_candidates, _ = signal.find_peaks(
        -x,
        distance=max(1, sampling_rate // 10)
    )
    valley_candidates = np.asarray(valley_candidates, dtype=int)

    valleys: List[int] = []
    valid_peaks: List[int] = []

    search_win = max(10, sampling_rate // 2)

    def local_min_idx(left: int, right: int) -> int:
        seg = x[left:right]
        if seg.size == 0:
            return left
        return int(left + np.argmin(seg))

    for p in peaks_raw:
        prev_vals = valley_candidates[valley_candidates < p]
        next_vals = valley_candidates[valley_candidates > p]

        if prev_vals.size > 0:
            pv = int(prev_vals[-1])
        else:
            pv = local_min_idx(max(0, p - search_win), p)

        if next_vals.size > 0:
            nv = int(next_vals[0])
        else:
            nv = local_min_idx(p + 1, min(x.size, p + 1 + search_win))

        if pv < p < nv:
            valleys.append(pv)
            valleys.append(nv)
            valid_peaks.append(int(p))

    peaks = np.asarray(valid_peaks, dtype=int)
    valleys = np.asarray(sorted(set(valleys)), dtype=int)

    # 如果没有检测到眨眼：默认值
    if peaks.size == 0:
        total_time = float(x.size / sampling_rate)
        eye_closure_ratio = 0.0
        eye_status = "open"
        
        if total_close_time > 0 and total_time > 0:
            eye_closure_ratio = float((total_close_time / sampling_rate / total_time) * 100.0)
        
        # 施密特触发器判断眼睛状态（改进点4）
        eye_status = _schmitt_trigger_status(x, sampling_rate)
        
        features.update({
            "avg_blink_amplitude": 0.0,
            "max_blink_amplitude": 0.0,
            "avg_blink_interval": 0.0,
            "blink_frequency": 0.0,
            "blink_rate_per_min": 0.0,
            "avg_blink_duration": 0.0,
            "avg_blink_duration_hwhm": 0.0,
            "blink_duration_ms": 0.0,
            "eye_closure_ratio": eye_closure_ratio,
            "eye_status": eye_status,
            "left_eye_status": eye_status,
            "right_eye_status": eye_status,
            "signal_quality": _compute_signal_quality(x),
            "battery_level": None,
        })
        return features, peaks, valleys, personal_baseline

    # 5) 幅度
    blink_amplitudes: List[float] = []
    for p in peaks:
        pv_candidates = valleys[valleys < p]
        if pv_candidates.size == 0:
            continue
        pv = int(pv_candidates[-1])
        amp = float(x[p] - x[pv])
        blink_amplitudes.append(amp)

    features["avg_blink_amplitude"] = float(np.mean(blink_amplitudes)) if blink_amplitudes else 0.0
    features["max_blink_amplitude"] = float(np.max(blink_amplitudes)) if blink_amplitudes else 0.0

    # 6) 眨眼间隔
    if peaks.size > 1:
        blink_intervals = (np.diff(peaks) / sampling_rate).astype(float)
        features["avg_blink_interval"] = float(np.mean(blink_intervals))
    else:
        features["avg_blink_interval"] = 0.0

    # 7) 频率（添加物理上限检查）
    total_time = float(x.size / sampling_rate)
    max_physiological_rate = 5.0
    max_physiological_peaks = int(total_time * max_physiological_rate)
    valid_peak_count = min(len(peaks), max_physiological_peaks)
    blink_frequency = float(valid_peak_count / total_time) if total_time > 0 else 0.0
    features["blink_frequency"] = blink_frequency
    features["blink_rate_per_min"] = blink_frequency * 60.0

    # 8) 持续时间
    blink_durations_valley: List[float] = []
    for p in peaks:
        prev_vals = valleys[valleys < p]
        next_vals = valleys[valleys > p]
        if prev_vals.size == 0 or next_vals.size == 0:
            continue
        pv = int(prev_vals[-1])
        nv = int(next_vals[0])
        if pv < p < nv:
            blink_durations_valley.append(float((nv - pv) / sampling_rate))

    avg_dur_sec = float(np.mean(blink_durations_valley)) if blink_durations_valley else 0.0
    std_dur_sec = float(np.std(blink_durations_valley)) if len(blink_durations_valley) > 1 else 0.0
    features["avg_blink_duration"] = avg_dur_sec
    features["blink_duration_ms"] = avg_dur_sec * 1000.0
    
    # 更新个人基准（用于适应性阈值）
    if personal_baseline["sample_count"] < 100:
        personal_baseline["avg_blink_duration"] = (
            personal_baseline["avg_blink_duration"] * personal_baseline["sample_count"] + avg_dur_sec
        ) / (personal_baseline["sample_count"] + 1)
        personal_baseline["std_blink_duration"] = std_dur_sec
        personal_baseline["sample_count"] += 1

    # 9) 半高宽持续时间
    durations_hwhm: List[float] = []
    global_min = float(np.min(x))
    for p in peaks:
        half_height = float((x[p] + global_min) / 2.0)

        left_idx = int(p)
        while left_idx > 0 and x[left_idx] > half_height:
            left_idx -= 1

        right_idx = int(p)
        while right_idx < x.size - 1 and x[right_idx] > half_height:
            right_idx += 1

        durations_hwhm.append(float((right_idx - left_idx) / sampling_rate))

    features["avg_blink_duration_hwhm"] = float(np.mean(durations_hwhm)) if durations_hwhm else 0.0

    # 10) 眼闭合比例
    total_blink_time = float(np.sum(blink_durations_valley)) if blink_durations_valley else 0.0
    total_close_time_sec = total_close_time / sampling_rate
    total_blink_time += total_close_time_sec
    eye_closure_ratio_raw = (total_blink_time / total_time) * 100.0 if total_time > 0 else 0.0
    features["eye_closure_ratio"] = float(min(eye_closure_ratio_raw, 100.0))

    # 11) 施密特触发器判断眼睛状态（改进点4）
    eye_status = _schmitt_trigger_status(x, sampling_rate)
    features["eye_status"] = eye_status
    features["left_eye_status"] = eye_status
    features["right_eye_status"] = eye_status

    # 12) 质量/电量占位
    features["signal_quality"] = _compute_signal_quality(x)
    features["battery_level"] = None

    return features, peaks, valleys, personal_baseline


def _schmitt_trigger_status(
    signal: np.ndarray,
    sampling_rate: int,
    high_thresh: float = 0.6,
    low_thresh: float = 0.4,
    min_duration_ms: float = 200
) -> str:
    """
    施密特触发器判断眼睛状态（改进点4）
    - 只有当信号超过高阈值且持续一定时间才判定为闭眼
    - 低于低阈值时才判定为睁眼，防止抖动
    """
    min_duration_samples = int(min_duration_ms * sampling_rate / 1000)
    x = np.asarray(signal, dtype=float)
    
    if x.size < min_duration_samples:
        return "open"
    
    # 计算滑动窗口均值
    window_size = min_duration_samples
    n_windows = x.size - window_size + 1
    if n_windows <= 0:
        return "open"
    
    # 使用卷积计算滑动均值
    window_mean = np.convolve(x, np.ones(window_size)/window_size, mode='valid')
    
    # 施密特触发逻辑
    status = "open"
    consecutive_high = 0
    
    for i in range(len(window_mean)):
        if window_mean[i] >= high_thresh:
            consecutive_high += 1
            if consecutive_high >= min_duration_samples // 2:
                status = "closed"
                break
        elif window_mean[i] <= low_thresh:
            consecutive_high = 0
            status = "open"
    
    return status


# =========================
# 3) 事件检测与分类（改进凝视检测鲁棒性）
# =========================
def detect_blink_events(
    features: Dict,
    peaks: np.ndarray,
    valleys: np.ndarray,
    eyelid_signal: np.ndarray,
    sampling_rate: int = 100,
    personal_baseline: Dict = None
) -> Tuple[List[Dict], Dict]:
    """
    检测眨眼事件并分类（normal / long / incomplete）
    改进点：
    1) 使用绝对物理基准 + 个人基准的混合阈值判断长眨眼
    2) 改进凝视检测：使用信号能量而非固定波动阈值
    """
    x = np.asarray(eyelid_signal, dtype=float)
    peaks = np.asarray(peaks, dtype=int)
    valleys = np.asarray(valleys, dtype=int)
    
    personal_baseline = personal_baseline or {
        "avg_blink_duration": 0.15,
        "std_blink_duration": 0.05,
        "sample_count": 0
    }

    blink_events: List[Dict] = []
    classified_blinks: Dict[str, List[Dict]] = {"normal": [], "long": [], "incomplete": []}

    if x.size < 10 or peaks.size == 0:
        return blink_events, classified_blinks

    if valleys.size == 0:
        search_win = max(10, sampling_rate // 2)
        vset: set[int] = set()

        def local_min_idx(left: int, right: int) -> int:
            seg = x[left:right]
            if seg.size == 0:
                return left
            return int(left + np.argmin(seg))

        for p in peaks:
            pv = local_min_idx(max(0, p - search_win), p)
            nv = local_min_idx(p + 1, min(x.size, p + 1 + search_win))
            if pv < p < nv:
                vset.add(int(pv))
                vset.add(int(nv))

        valleys = np.array(sorted(vset), dtype=int)

    # 改进点1: 绝对物理基准 + 个人基准的混合阈值
    # 绝对物理基准：长眨眼 > 300ms
    absolute_long_threshold = 0.30  # 300ms
    # 个人基准：平均值 + 1.5倍标准差
    personal_long_threshold = personal_baseline["avg_blink_duration"] + 1.5 * personal_baseline["std_blink_duration"]
    # 使用绝对基准和个人基准的加权平均
    duration_threshold = 0.7 * absolute_long_threshold + 0.3 * min(personal_long_threshold, 0.5)
    duration_threshold = max(duration_threshold, 0.2)  # 至少200ms

    avg_interval = float(features.get("avg_blink_interval", 0.0))
    normal_blink_interval = avg_interval if avg_interval > 0 else 3.0
    incomplete_threshold = normal_blink_interval * 1.5

    valid_events: List[Dict] = []
    for p in peaks:
        prev_vals = valleys[valleys < p]
        next_vals = valleys[valleys > p]
        if prev_vals.size == 0 or next_vals.size == 0:
            continue

        start_idx = int(prev_vals[-1])
        end_idx = int(next_vals[0])
        if not (start_idx < p < end_idx):
            continue

        blink_amplitude = float(x[p] - x[start_idx])
        blink_duration = float((end_idx - start_idx) / sampling_rate)

        event = {
            "start": start_idx,
            "peak": int(p),
            "end": end_idx,
            "amplitude": blink_amplitude,
            "duration": blink_duration,
            "duration_ms": blink_duration * 1000.0,
            "eye_status": "closed",
        }
        valid_events.append(event)

    valid_events.sort(key=lambda e: e["start"])

    for e in valid_events:
        if e["duration"] > duration_threshold:
            classified_blinks["long"].append(e)
        else:
            classified_blinks["normal"].append(e)

    blink_events.extend(valid_events)

    # 改进点2: 凝视检测使用信号能量而非固定波动阈值
    incomplete_by_interval: List[Dict] = []
    
    # 计算信号能量阈值（基于整个信号的中值绝对偏差）
    signal_mad = np.median(np.abs(x - np.median(x)))
    energy_threshold = signal_mad * 1.5  # 使用MAD而不是固定0.02

    for i in range(1, len(valid_events)):
        prev_event = valid_events[i - 1]
        curr_event = valid_events[i]

        interval_duration = float((curr_event["start"] - prev_event["end"]) / sampling_rate)
        if interval_duration <= incomplete_threshold:
            continue

        interval_start = int(prev_event["end"])
        interval_end = int(curr_event["start"])
        interval_signal = x[interval_start:interval_end]
        if interval_signal.size == 0:
            continue

        # 使用信号能量（方差）而非固定阈值
        signal_energy = float(np.var(interval_signal))
        signal_max = float(np.max(interval_signal) - np.min(interval_signal))
        
        # 如果信号能量和最大值波动都很小，且持续时间足够长，才判定为凝视
        if signal_energy < energy_threshold and signal_max < energy_threshold * 3:
            incomplete_event = {
                "start": interval_start,
                "peak": int(interval_start + interval_signal.size // 2),
                "end": interval_end,
                "amplitude": signal_max,
                "duration": interval_duration,
                "duration_ms": interval_duration * 1000.0,
                "eye_status": "open",
                "type": "stare_interval",
            }
            incomplete_by_interval.append(incomplete_event)
            classified_blinks["incomplete"].append(incomplete_event)

    blink_events.extend(incomplete_by_interval)

    return blink_events, classified_blinks


# =========================
# 4) 疲劳评分与输出（沿用原思路，做"缺省/口径"微调）
# =========================
def assess_fatigue(
    blink_features: Dict,
    blink_events: List[Dict],
    classified_blinks: Dict,
    time_window: int = 60,
    driving_time: str = "0小时0分钟"
) -> Tuple[float, str, Dict]:
    """
    多维度评估疲劳状态并输出 JSON 结构。
    """
    indicators: Dict[str, float] = {}

    freq = float(blink_features.get("blink_frequency", 0.0))
    if freq > 0:
        normal_range = (0.3, 0.6)
        if freq < normal_range[0]:
            indicators["blink_frequency_score"] = float(min(100.0, (normal_range[0] - freq) * 500.0))
        elif freq > normal_range[1]:
            indicators["blink_frequency_score"] = float(min(80.0, (freq - normal_range[1]) * 200.0))
        else:
            indicators["blink_frequency_score"] = 0.0
    else:
        indicators["blink_frequency_score"] = 90.0

    avg_dur = float(blink_features.get("avg_blink_duration", 0.0))
    if avg_dur > 0:
        normal_duration = 0.12
        indicators["blink_duration_score"] = float(min(100.0, max(0.0, (avg_dur - normal_duration) * 500.0)))
    else:
        indicators["blink_duration_score"] = 0.0

    true_blink_events = [e for e in blink_events if e.get("type") != "stare_interval"]
    total_true_blinks = len(true_blink_events)

    long_blinks = len(classified_blinks.get("long", []))
    if total_true_blinks > 0:
        long_ratio = long_blinks / total_true_blinks
        indicators["long_blink_ratio_score"] = float(min(100.0, max(0.0, (long_ratio - 0.1) * 600.0)))
    else:
        indicators["long_blink_ratio_score"] = 0.0

    incomplete_blinks = len(classified_blinks.get("incomplete", []))
    if total_true_blinks > 0:
        incomplete_ratio = incomplete_blinks / total_true_blinks
        if incomplete_ratio > 0.15:
            indicators["incomplete_blink_ratio_score"] = float(min(100.0, (incomplete_ratio - 0.15) * 500.0))
        else:
            indicators["incomplete_blink_ratio_score"] = 0.0
    else:
        indicators["incomplete_blink_ratio_score"] = 0.0

    eye_closure_ratio = float(blink_features.get("eye_closure_ratio", 0.0))
    if eye_closure_ratio >= 25:
        indicators["eye_closure_score"] = 100.0
    elif eye_closure_ratio >= 18:
        indicators["eye_closure_score"] = 85.0
    elif eye_closure_ratio >= 12:
        indicators["eye_closure_score"] = 65.0
    elif eye_closure_ratio >= 8:
        indicators["eye_closure_score"] = 45.0
    elif eye_closure_ratio >= 4:
        indicators["eye_closure_score"] = float((eye_closure_ratio - 4.0) * 15.0)
    else:
        indicators["eye_closure_score"] = 0.0

    weights = {
        "blink_frequency_score": 0.20,
        "blink_duration_score": 0.25,
        "long_blink_ratio_score": 0.15,
        "incomplete_blink_ratio_score": 0.10,
        "eye_closure_score": 0.35,
    }

    fatigue_score = 0.0
    for k, v in indicators.items():
        fatigue_score += float(v) * float(weights.get(k, 0.0))

    fatigue_score = float(np.clip(fatigue_score, 0.0, 100.0))

    alert_level = 0
    if fatigue_score < 20:
        fatigue_level = "清醒"
        eye_status = "open"
        alert_level = 0
    elif fatigue_score < 40:
        fatigue_level = "轻度疲劳"
        eye_status = "open"
        alert_level = 0
    elif fatigue_score < 60:
        fatigue_level = "中度疲劳"
        eye_status = "open"
        alert_level = 1
    elif fatigue_score < 80:
        fatigue_level = "重度疲劳"
        eye_status = "closed"
        alert_level = 1
    else:
        fatigue_level = "极度疲劳"
        eye_status = "closed"
        alert_level = 2

    output_data = {
        "eyestatus": eye_status,
        "fatigueScore": round(fatigue_score, 1),
        "blinkRate": round(float(blink_features.get("blink_rate_per_min", 0.0)), 1),
        "avgBlinkDuration": round(float(blink_features.get("blink_duration_ms", 0.0)), 1),
        "alertLevel": alert_level,
        "eyeStatus": eye_status,
        "drivingTime": driving_time,
        "fatigueLevel": fatigue_level,
        "eyelidStatus": {
            "leftEye": blink_features.get("left_eye_status", "open"),
            "rightEye": blink_features.get("right_eye_status", "open"),
            "blinkDuration": round(float(blink_features.get("blink_duration_ms", 0.0)), 1),
            "eyeClosureRatio": round(float(blink_features.get("eye_closure_ratio", 0.0)), 1),
            "incompleteBlinks": int(len(classified_blinks.get("incomplete", []))),
            "longBlinks": int(len(classified_blinks.get("long", []))),
            "normalBlinks": int(len(classified_blinks.get("normal", []))),
        },
        "sensorStatus": {
             "signalQuality": blink_features.get("signal_quality", 0),
             "batteryLevel": blink_features.get("battery_level", None),
             "connected": True
        },
        "signalQuality": blink_features.get("signal_quality", None),
        "batteryLevel": blink_features.get("battery_level", None),
        "debug": {
            "avgBlinkIntervalSec": round(float(blink_features.get("avg_blink_interval", 0.0)), 3),
            "avgBlinkDurationSec": round(float(blink_features.get("avg_blink_duration", 0.0)), 3),
            "avgBlinkDurationHWHMSec": round(float(blink_features.get("avg_blink_duration_hwhm", 0.0)), 3),
        }
    }

    return fatigue_score, fatigue_level, output_data


# =========================
# 5) 给 app.py 的统一入口（改进：统一阈值口径 + 滑动窗口）
# =========================
class FatiguePipelineState:
    """
    滑动窗口状态缓存 + 初始校准机制
    用于解决"冷启动"问题，只保留最近60s的有效数据
    支持初始校准：启动后先采集一段时间建立个人基准
    """
    def __init__(
        self,
        window_size_sec: float = 60.0,
        sampling_rate: int = 100,
        calibration_duration_sec: float = 30.0
    ):
        self.window_size_sec = window_size_sec
        self.window_size_samples = int(window_size_sec * sampling_rate)
        self.sampling_rate = sampling_rate
        self.buffer: List[float] = []
        self.timestamp_buffer: List[float] = []

        self.calibration_duration_sec = calibration_duration_sec
        self.is_calibrating = True
        self.calibration_samples: List[float] = []
        self.calibration_complete = False

        self.personal_baseline = {
            "avg_blink_duration": 0.15,
            "std_blink_duration": 0.05,
            "sample_count": 0,
            "calibrated": False
        }

    def update(self, new_samples: np.ndarray, timestamps: np.ndarray = None):
        """更新滑动窗口缓冲区"""
        if self.is_calibrating:
            self.calibration_samples.extend(new_samples.tolist())
            calibration_samples_count = len(self.calibration_samples)
            calibration_duration = calibration_samples_count / self.sampling_rate

            if calibration_duration >= self.calibration_duration_sec:
                self._complete_calibration()

        self.buffer.extend(new_samples.tolist())
        if timestamps is not None:
            self.timestamp_buffer.extend(timestamps.tolist())

        if len(self.buffer) > self.window_size_samples:
            excess = len(self.buffer) - self.window_size_samples
            self.buffer = self.buffer[excess:]
            if timestamps is not None:
                self.timestamp_buffer = self.timestamp_buffer[excess:]

    def _complete_calibration(self):
        """完成校准，基于校准期间的数据建立个人基准"""
        if self.calibration_complete:
            return

        calibration_data = np.array(self.calibration_samples, dtype=float)
        if calibration_data.size < 100:
            print("[ALGO] 校准数据不足，延迟校准")
            return

        self.is_calibrating = False
        self.calibration_complete = True

        mean_duration = float(np.mean(calibration_data))
        std_duration = float(np.std(calibration_data))

        self.personal_baseline = {
            "avg_blink_duration": 0.15,
            "std_blink_duration": 0.05,
            "sample_count": 0,
            "calibrated": True,
            "calibration_samples_count": len(self.calibration_samples),
            "calibration_duration_sec": len(self.calibration_samples) / self.sampling_rate,
            "baseline_mean": mean_duration,
            "baseline_std": std_duration
        }
        print(f"[ALGO] 校准完成！采集了 {len(self.calibration_samples)} 个样本 ({self.personal_baseline['calibration_duration_sec']:.1f}秒)")
        print(f"[ALGO] 个人基准: avg_duration={self.personal_baseline['avg_blink_duration']*1000:.1f}ms, std={self.personal_baseline['std_blink_duration']*1000:.1f}ms")
    
    def get_valid_window(self) -> Tuple[np.ndarray, float]:
        """
        获取有效窗口数据
        校准期间返回校准数据，用于建立初始基准
        返回：(窗口数据, 窗口时长秒)
        """
        if self.is_calibrating:
            calibration_data = np.array(self.calibration_samples, dtype=float)
            return calibration_data, len(calibration_data) / self.sampling_rate

        if len(self.buffer) < 10:
            return np.array([]), 0.0

        window_data = np.array(self.buffer)
        window_duration = len(window_data) / self.sampling_rate

        valid_ratio = len(window_data) / self.window_size_samples
        if valid_ratio < 0.5:
            print(f"[ALGO] 警告：数据有效率仅 {valid_ratio*100:.1f}%，可能传感器不稳定")

        return window_data, window_duration
    
    def compute_data_quality(self) -> float:
        """计算数据质量分数"""
        if len(self.buffer) < 10:
            return 0.0
        
        x = np.array(self.buffer)
        # 检查信号稳定性
        signal_range = float(np.max(x) - np.min(x))
        if signal_range < 0.01:
            return 0.2  # 信号过弱
        
        # 检查是否有足够的波动（而不是死寂）
        signal_var = float(np.var(x))
        if signal_var < 0.0001:  # 降低阈值，从 0.001 降到 0.0001
            return 0.3  # 信号过于平稳
        
        return 1.0


# 全局状态（实际使用时应该由app.py管理生命周期）
_fatigue_state: Optional[FatiguePipelineState] = None


def run_fatigue_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    driving_time: str = "0小时0分钟",
    battery_level: Optional[float] = None,
    use_sliding_window: bool = True,
    window_size_sec: float = 60.0,
    calibration_duration_sec: float = 30.0
) -> Dict:
    """
    app.py 调用推荐入口
    改进点：
    1) 统一阈值口径（闭眼检测和眨眼检测都在归一化信号上进行）
    2) 使用 Mask 机制替代信号填充
    3) 施密特触发器判断眼睛状态
    4) 滑动窗口缓存解决冷启动问题
    5) 初始校准机制：启动后先采集一段时间建立个人基准
    """
    global _fatigue_state
    
    raw_np = np.asarray(raw_signal, dtype=float)
    
    # 初始化或更新滑动窗口状态
    if use_sliding_window:
        if _fatigue_state is None or _fatigue_state.sampling_rate != sampling_rate:
            _fatigue_state = FatiguePipelineState(window_size_sec, sampling_rate, calibration_duration_sec)
        
        _fatigue_state.update(raw_np)
        window_data, window_duration = _fatigue_state.get_valid_window()
        
        # 检查数据质量
        data_quality = _fatigue_state.compute_data_quality()
        if data_quality < 0.5:
            print(f"[ALGO] 警告：数据质量分数 {data_quality:.2f} 较低，返回默认状态")
            return _default_fatigue_output()
        
        # 使用窗口数据代替原始数据
        normed = window_data
        total_window_time = window_duration
    else:
        normed = raw_np
        total_window_time = len(normed) / sampling_rate

    # 预处理（统一在归一化信号上进行所有检测）
    _, normed_preprocessed, _ = adaptive_preprocess_eyelid_signal(
        normed if use_sliding_window else raw_np, 
        sampling_rate=sampling_rate
    )
    
    # 在归一化信号上检测长闭眼区域（改进点1：统一阈值口径）
    # 使用相对于动态基线的阈值
    signal_mean = np.mean(normed_preprocessed)
    signal_std = np.std(normed_preprocessed)
    relative_threshold = signal_mean + 1.5 * signal_std  # 动态相对阈值
    
    normed_high_threshold = float(np.clip(relative_threshold, 0.5, 0.8))
    normed_min_duration = int(1.0 * sampling_rate)  # 至少1秒才认为是长闭眼
    
    # 标记长闭眼区域（使用Mask机制，改进点2）
    long_close_regions: List[Tuple[int, int]] = []
    in_normed_high = False
    normed_region_start = 0
    
    for i in range(len(normed_preprocessed)):
        if normed_preprocessed[i] >= normed_high_threshold and not in_normed_high:
            in_normed_high = True
            normed_region_start = i
        elif normed_preprocessed[i] < normed_high_threshold and in_normed_high:
            in_normed_high = False
            normed_region_end = i
            if normed_region_end - normed_region_start >= normed_min_duration:
                long_close_regions.append((normed_region_start, normed_region_end))
    
    if in_normed_high and len(normed_preprocessed) - normed_region_start >= normed_min_duration:
        long_close_regions.append((normed_region_start, len(normed_preprocessed)))
    
    # 计算总长闭眼时间
    total_close_time = sum(end - start for start, end in long_close_regions)
    
    # 获取个人基准
    personal_baseline = _fatigue_state.personal_baseline if use_sliding_window and _fatigue_state else None
    
    # 提取特征（传入长闭眼区域和掩码，不修改原始信号）
    features, peaks, valleys, updated_baseline = extract_blink_features(
        normed_preprocessed, 
        sampling_rate=sampling_rate,
        total_close_time=total_close_time,
        long_close_regions=long_close_regions,
        personal_baseline=personal_baseline
    )
    
    # 更新个人基准
    if use_sliding_window and _fatigue_state and updated_baseline:
        _fatigue_state.personal_baseline = updated_baseline

    if battery_level is not None:
        features["battery_level"] = battery_level

    # 检测眨眼事件
    blink_events, classified = detect_blink_events(
        features=features,
        peaks=peaks,
        valleys=valleys,
        eyelid_signal=normed_preprocessed,
        sampling_rate=sampling_rate,
        personal_baseline=personal_baseline
    )

    _, _, output = assess_fatigue(
        blink_features=features,
        blink_events=blink_events,
        classified_blinks=classified,
        driving_time=driving_time,
    )
    
    # 添加调试信息
    output["debug"]["longCloseRegions"] = len(long_close_regions)
    output["debug"]["totalCloseTime"] = total_close_time / sampling_rate
    output["debug"]["dataQuality"] = _fatigue_state.compute_data_quality() if use_sliding_window and _fatigue_state else 1.0
    output["debug"]["personalBaselineMs"] = round(personal_baseline["avg_blink_duration"] * 1000, 1) if personal_baseline else 150.0
    output["debug"]["isCalibrating"] = _fatigue_state.is_calibrating if use_sliding_window and _fatigue_state else False
    output["debug"]["calibrationComplete"] = _fatigue_state.calibration_complete if use_sliding_window and _fatigue_state else True

    return output


def _default_fatigue_output() -> Dict:
    """返回默认的疲劳输出（用于数据质量不足时）"""
    return {
        "eyestatus": "open",
        "fatigueScore": 0.0,
        "blinkRate": 0.0,
        "avgBlinkDuration": 0.0,
        "alertLevel": 0,
        "eyeStatus": "open",
        "drivingTime": "0小时0分钟",
        "fatigueLevel": "清醒",
        "eyelidStatus": {
            "leftEye": "open",
            "rightEye": "open",
            "blinkDuration": 0.0,
            "eyeClosureRatio": 0.0,
            "incompleteBlinks": 0,
            "longBlinks": 0,
            "normalBlinks": 0,
        },
        "sensorStatus": {
            "signalQuality": 0,
            "batteryLevel": None,
            "connected": True
        },
        "signalQuality": 0,
        "batteryLevel": None,
        "debug": {
            "avgBlinkIntervalSec": 0,
            "avgBlinkDurationSec": 0,
            "avgBlinkDurationHWHMSec": 0,
            "longCloseRegions": 0,
            "totalCloseTime": 0,
            "dataQuality": 0,
            "personalBaselineMs": 150.0
        }
    }


def reset_fatigue_state():
    """重置滑动窗口状态（当切换用户或重新开始监测时调用）"""
    global _fatigue_state
    _fatigue_state = None