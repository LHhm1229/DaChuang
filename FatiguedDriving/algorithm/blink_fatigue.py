"""
blink_fatigue.py
================

目标
- 作为“算法模块”，被 app.py 稳定调用（可直接 import 使用）
- 统一信号物理语义：高值=更闭合/眨眼峰（blink peak）
- 用“新版预处理 + 新版眨眼特征提取”替换旧版前两段
- 对齐后两段（事件检测/疲劳评分）的接口与度量体系，让整条链路可跑通

统一约定（全链路一致）
- 输入：raw_signal（原始眼睑信号，1D）
- 预处理输出 normalized_signal：范围约在 [0,1]，且“值越大=越闭合/越像眨眼峰”
- peaks：眨眼峰（高值点）
- valleys：围绕峰的前后谷（低值点）
- 事件 start/end：用“前谷/后谷”定义
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
from scipy.ndimage import grey_opening, grey_closing

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


# =========================
# 1) 预处理（新版替换）
# =========================
def preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    drift_window_sec: float = 2.0,
    smooth_cutoff_hz: float = 6.5,
    normalize: bool = False  # 添加参数控制是否归一化
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    新版预处理（来自你提供的版本，微调：返回 trend_base 以便链路兼容）

    目标：去除驾驶过程的基线漂移，同时保留慢眨眼/长闭眼这类低频但“有意义”的事件

    改动要点：
    1) 形态学滤波结构元素按秒换算，并扩大到秒级窗口
       慢眨眼（0.4~2.0s）不会被当成基线消掉
    2) 形态学只用于估计漂移基线
    3) 保留低通滤波与归一化输出形式
    """
    x = np.asarray(raw_signal, dtype=float)
    if x.ndim != 1 or x.size < max(50, sampling_rate):
        centered = x - np.mean(x) if x.size > 0 else x
        return centered, centered, centered

    # 1) 去直流
    centered_signal = x - np.mean(x)

    # 2) 大窗口形态学估计基线漂移
    size_drift = int(max(3, round(drift_window_sec * sampling_rate)))

    trend_open = grey_opening(centered_signal, size=size_drift)
    trend_base = grey_closing(trend_open, size=size_drift)

    baseline_removed = centered_signal - trend_base

    # 3) 低通滤波
    nyquist = sampling_rate / 2.0
    cutoff = smooth_cutoff_hz / nyquist
    cutoff = float(min(max(cutoff, 1e-6), 0.999999))

    b, a = signal.butter(8, cutoff, "lowpass")
    filtered_signal = signal.filtfilt(b, a, baseline_removed)

    # 4) 可选归一化到 [0,1]
    if normalize:
        min_val = float(np.min(filtered_signal))
        max_val = float(np.max(filtered_signal))
        if max_val - min_val > 1e-12:
            normalized_signal = (filtered_signal - min_val) / (max_val - min_val)
        else:
            normalized_signal = filtered_signal.copy()
    else:
        # 不归一化，保持原始幅度信息
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
        smooth_cutoff_hz=6.5,
        normalize=True  # 恢复归一化
    )


# =========================
# 2) 眨眼特征提取（新版替换 + 与后两段对齐的微调）
# =========================
def extract_blink_features(
    eyelid_signal: np.ndarray,
    sampling_rate: int = 100,
    peak_height: float = 0.7,
    min_peak_distance_sec: float = 0.33,
    total_close_time: int = 0
) -> Tuple[Dict, np.ndarray, np.ndarray]:
    """
    新版眨眼特征提取（来自你提供的版本，微调点如下）：
    - valleys 仍基于 peaks 推导
    - “平均眨眼间隔”改为使用 peaks 间距（更稳定、物理意义更直观）
    - “眨眼持续时间”对齐事件检测：以“前谷->后谷”定义为主（avg_blink_duration）
      同时保留你原先半高宽估计作为补充字段 avg_blink_duration_hwhm
    - 增加 signal_quality / battery_level 占位，保证 app.py / 前端字段稳定

    统一语义：
    - 高值 = 闭眼/眨眼峰（blink peak）
    - peaks：眨眼峰值点
    - valleys：每个峰前后对应的谷值点（低值点）
    """
    x = np.asarray(eyelid_signal, dtype=float)
    features: Dict = {}

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
        return features, np.array([], dtype=int), np.array([], dtype=int)

    # 1) 峰值（眨眼时刻）
    # 使用合理的阈值（适用于归一化到[0,1]的信号）
    min_peak_distance = max(1, int(min_peak_distance_sec * sampling_rate))
    
    peaks_raw, _ = signal.find_peaks(
        x,
        height=0.55,  # 高度阈值
        distance=min_peak_distance,
        width=1  # 要求峰值有一定宽度
    )
    peaks_raw = np.asarray(peaks_raw, dtype=int)
    
    # 2) 谷值候选（找 -x 的峰）
    valley_candidates, _ = signal.find_peaks(
        -x,
        distance=max(1, sampling_rate // 10)
    )
    valley_candidates = np.asarray(valley_candidates, dtype=int)

    # 3) 为每个 peak 找前后 valley（若候选不足，做局部最小兜底）
    valleys: List[int] = []
    valid_peaks: List[int] = []

    search_win = max(10, sampling_rate // 2)  # 0.5s 窗口兜底

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
        # 计算眼闭合比例（基于长时间闭眼区域）
        total_time = float(x.size / sampling_rate)
        eye_closure_ratio = 0.0
        eye_status = "open"
        
        if total_close_time > 0 and total_time > 0:
            eye_closure_ratio = float((total_close_time / sampling_rate / total_time) * 100.0)
        
        # 如果有长时间闭眼区域，眼睛状态应该是closed
        if total_close_time > sampling_rate * 0.5:  # 超过0.5秒闭眼
            eye_status = "closed"
        
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
        return features, peaks, valleys

    # 4) 幅度（峰-前谷，统一为正值）
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

    # 5) 眨眼间隔（用 peaks 间距：更直观、更稳定）
    if peaks.size > 1:
        blink_intervals = (np.diff(peaks) / sampling_rate).astype(float)
        features["avg_blink_interval"] = float(np.mean(blink_intervals))
    else:
        features["avg_blink_interval"] = 0.0

    # 6) 频率
    total_time = float(x.size / sampling_rate)
    blink_frequency = float(peaks.size / total_time) if total_time > 0 else 0.0
    features["blink_frequency"] = blink_frequency
    features["blink_rate_per_min"] = blink_frequency * 60.0

    # 7) 持续时间：对齐事件检测/分类（主口径：谷到谷）
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

    features["avg_blink_duration"] = float(np.mean(blink_durations_valley)) if blink_durations_valley else 0.0
    features["blink_duration_ms"] = features["avg_blink_duration"] * 1000.0

    # 8) 半高宽持续时间（保留你原逻辑为补充字段，不参与下游门槛）
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

    # 9) 眼闭合比例：累计（谷到谷持续时间 + 长时间闭眼区域）/ 总时长
    total_blink_time = float(np.sum(blink_durations_valley)) if blink_durations_valley else 0.0
    # 加上长时间闭眼区域的时间
    total_close_time_samples = total_close_time  # 从前面的高值区域检测得到
    total_close_time_sec = total_close_time_samples / sampling_rate
    total_blink_time += total_close_time_sec
    # 确保眼闭合比例不超过100%
    eye_closure_ratio_raw = (total_blink_time / total_time) * 100.0 if total_time > 0 else 0.0
    features["eye_closure_ratio"] = float(min(eye_closure_ratio_raw, 100.0))

    # 10) 眼睛状态（最近 1 秒均值）：高=更闭合
    recent = x[-sampling_rate:] if x.size >= sampling_rate else x
    recent_avg = float(np.mean(recent))
    features["eye_status"] = "closed" if recent_avg >= 0.5 else "open"
    features["left_eye_status"] = features["eye_status"]
    features["right_eye_status"] = features["eye_status"]

    # 11) 质量/电量占位
    features["signal_quality"] = _compute_signal_quality(x)
    features["battery_level"] = None

    return features, peaks, valleys


# =========================
# 3) 事件检测与分类（沿用原思路，做“接口/口径”微调）
# =========================
def detect_blink_events(
    features: Dict,
    peaks: np.ndarray,
    valleys: np.ndarray,
    eyelid_signal: np.ndarray,
    sampling_rate: int = 100
) -> Tuple[List[Dict], Dict]:
    """
    检测眨眼事件并分类（normal / long / incomplete）

    关键点（保持原思路）：
    - 不把 valleys 作为“是否工作”的硬门槛：如果 peaks 有但 valleys 空，会兜底生成 valleys
    - 事件 start/end：前谷/后谷
    - duration：谷到谷（与 features['avg_blink_duration'] 一致）
    - 幅度：peak - prev_valley（统一为正）
    - incomplete：保留“间隔过长 + 区间信号几乎不变”的思想，标记 type='stare_interval'
    """
    x = np.asarray(eyelid_signal, dtype=float)
    peaks = np.asarray(peaks, dtype=int)
    valleys = np.asarray(valleys, dtype=int)

    blink_events: List[Dict] = []
    classified_blinks: Dict[str, List[Dict]] = {"normal": [], "long": [], "incomplete": []}

    if x.size < 10 or peaks.size == 0:
        return blink_events, classified_blinks

    # valleys 兜底：若空，按每个峰左右窗口找局部最小点
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

    # 阈值：与“谷到谷 duration”同口径
    avg_dur = float(features.get("avg_blink_duration", 0.0))
    duration_threshold = (avg_dur * 1.5) if avg_dur > 0 else 0.2

    # “间隔过长”阈值（优先用 features['avg_blink_interval']，否则默认 3 秒）
    avg_interval = float(features.get("avg_blink_interval", 0.0))
    normal_blink_interval = avg_interval if avg_interval > 0 else 3.0
    incomplete_threshold = normal_blink_interval * 1.5

    # 逐峰构造事件：start/end = 前谷/后谷
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

    # 分类 normal / long
    for e in valid_events:
        if e["duration"] > duration_threshold:
            classified_blinks["long"].append(e)
        else:
            classified_blinks["normal"].append(e)

    blink_events.extend(valid_events)

    # incomplete（凝视/长时间无明显波动区间）
    signal_variation_threshold = 0.02
    incomplete_by_interval: List[Dict] = []

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

        max_variation = float(np.max(interval_signal) - np.min(interval_signal))
        if max_variation < signal_variation_threshold:
            incomplete_event = {
                "start": interval_start,
                "peak": int(interval_start + interval_signal.size // 2),
                "end": interval_end,
                "amplitude": max_variation,
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
# 4) 疲劳评分与输出（沿用原思路，做“缺省/口径”微调）
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

    说明：
    - time_window 作为接口保留（未来做滑窗统计可用）
    - 为保证与 app.py 对接稳定：对缺失字段使用 .get() 兜底
    """
    indicators: Dict[str, float] = {}

    # 1) 眨眼频率得分 - 疲劳时眨眼频率明显下降
    freq = float(blink_features.get("blink_frequency", 0.0))
    if freq > 0:
        normal_range = (0.25, 0.45)  # 次/秒 = 15-27次/分钟
        if freq < normal_range[0]:
            # 频率越低，得分越高（越疲劳）
            indicators["blink_frequency_score"] = float(min(100.0, (normal_range[0] - freq) * 400.0))
        elif freq > normal_range[1]:
            # 频率过高也可能是疲劳表现
            indicators["blink_frequency_score"] = float(min(60.0, (freq - normal_range[1]) * 150.0))
        else:
            indicators["blink_frequency_score"] = 0.0
    else:
        indicators["blink_frequency_score"] = 90.0

    # 2) 平均眨眼持续时间得分 - 疲劳时眨眼持续时间变长
    avg_dur = float(blink_features.get("avg_blink_duration", 0.0))
    if avg_dur > 0:
        normal_duration = 0.15  # 正常眨眼持续时间约150ms
        indicators["blink_duration_score"] = float(min(100.0, max(0.0, (avg_dur - normal_duration) * 300.0)))
    else:
        indicators["blink_duration_score"] = 0.0

    # 3) 长眨眼比例得分
    true_blink_events = [e for e in blink_events if e.get("type") != "stare_interval"]
    total_true_blinks = len(true_blink_events)

    long_blinks = len(classified_blinks.get("long", []))
    if total_true_blinks > 0:
        long_ratio = long_blinks / total_true_blinks
        # 长眨眼比例超过10%就开始计分
        indicators["long_blink_ratio_score"] = float(min(100.0, max(0.0, (long_ratio - 0.1) * 600.0)))
    else:
        indicators["long_blink_ratio_score"] = 0.0

    # 4) 不完全眨眼比例得分
    incomplete_blinks = len(classified_blinks.get("incomplete", []))
    if total_true_blinks > 0:
        incomplete_ratio = incomplete_blinks / total_true_blinks
        if incomplete_ratio > 0.15:
            indicators["incomplete_blink_ratio_score"] = float(min(100.0, (incomplete_ratio - 0.15) * 500.0))
        else:
            indicators["incomplete_blink_ratio_score"] = 0.0
    else:
        indicators["incomplete_blink_ratio_score"] = 0.0

    # 5) 眼闭合比例得分 - 最直接的疲劳指标
    eye_closure_ratio = float(blink_features.get("eye_closure_ratio", 0.0))
    # 正常眼闭合比例约2-5%，超过5%开始计分，更敏感的计分
    if eye_closure_ratio >= 30:
        indicators["eye_closure_score"] = 100.0
    elif eye_closure_ratio >= 20:
        indicators["eye_closure_score"] = 80.0
    elif eye_closure_ratio >= 10:
        indicators["eye_closure_score"] = 50.0
    elif eye_closure_ratio >= 5:
        indicators["eye_closure_score"] = float((eye_closure_ratio - 5.0) * 10.0)
    else:
        indicators["eye_closure_score"] = 0.0

    # 6) 加权融合
    weights = {
        "blink_frequency_score": 0.25,    # 提高权重
        "blink_duration_score": 0.20,     # 提高权重
        "long_blink_ratio_score": 0.15,
        "incomplete_blink_ratio_score": 0.10,
        "eye_closure_score": 0.30,        # 保持主要权重
    }

    fatigue_score = 0.0
    for k, v in indicators.items():
        fatigue_score += float(v) * float(weights.get(k, 0.0))

    fatigue_score = float(np.clip(fatigue_score, 0.0, 100.0))

    # 7) 疲劳等级
    alert_level = 0  # 0: normal, 1: warning, 2: danger
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

    # 8) 输出 JSON 结构（字段稳定）
    output_data = {
        "eyestatus": eye_status,
        "fatigueScore": round(fatigue_score, 1),
        "blinkRate": round(float(blink_features.get("blink_rate_per_min", 0.0)), 1),
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
        "drivingTime": driving_time,
        "fatigueLevel": fatigue_level,
        "alertLevel": alert_level,
        # 可选：把关键中间量透传给前端/日志（不影响旧字段）
        "debug": {
            "avgBlinkIntervalSec": round(float(blink_features.get("avg_blink_interval", 0.0)), 3),
            "avgBlinkDurationSec": round(float(blink_features.get("avg_blink_duration", 0.0)), 3),
            "avgBlinkDurationHWHMSec": round(float(blink_features.get("avg_blink_duration_hwhm", 0.0)), 3),
        }
    }

    return fatigue_score, fatigue_level, output_data


# =========================
# 5) 给 app.py 的统一入口
# =========================
def run_fatigue_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    driving_time: str = "0小时0分钟",
    battery_level: Optional[float] = None
) -> Dict:
    """
    app.py 调用推荐入口：
    raw_signal -> preprocess -> features -> events -> fatigue output_data
    """
    # 在原始信号上检测长时间闭眼区域
    # 原始信号语义：高值=闭眼/眨眼峰，低值=睁眼
    # 使用合适的阈值来区分眨眼和长时间闭眼
    high_threshold_raw = 0.72  # 原始信号高于此值认为是闭眼状态（低于严重疲劳的0.85）
    min_duration_samples = int(0.8 * sampling_rate)  # 最小持续时间0.8秒（比眨眼时间长很多）
    
    high_value_regions_raw = []
    in_high_region = False
    region_start = 0
    
    raw_np = np.asarray(raw_signal, dtype=float)
    for i in range(len(raw_np)):
        if raw_np[i] >= high_threshold_raw and not in_high_region:
            in_high_region = True
            region_start = i
        elif raw_np[i] < high_threshold_raw and in_high_region:
            in_high_region = False
            region_end = i
            if region_end - region_start >= min_duration_samples:
                high_value_regions_raw.append((region_start, region_end))
    
    if in_high_region and len(raw_np) - region_start >= min_duration_samples:
        high_value_regions_raw.append((region_start, len(raw_np)))
    
    # 计算总闭眼时间
    total_close_time_samples = sum(end - start for start, end in high_value_regions_raw)
    
    # 对原始信号进行预处理
    _, normed, _ = adaptive_preprocess_eyelid_signal(raw_signal, sampling_rate=sampling_rate)
    
    # 在归一化信号上标记长时间闭眼区域，并进行平滑处理
    # 使用较低的阈值来检测归一化后的闭眼区域
    normed_high_threshold = 0.65
    normed_min_duration = int(1.2 * sampling_rate)
    
    normed_high_regions = []
    in_normed_high = False
    normed_region_start = 0
    
    for i in range(len(normed)):
        if normed[i] >= normed_high_threshold and not in_normed_high:
            in_normed_high = True
            normed_region_start = i
        elif normed[i] < normed_high_threshold and in_normed_high:
            in_normed_high = False
            normed_region_end = i
            if normed_region_end - normed_region_start >= normed_min_duration:
                normed_high_regions.append((normed_region_start, normed_region_end))
    
    if in_normed_high and len(normed) - normed_region_start >= normed_min_duration:
        normed_high_regions.append((normed_region_start, len(normed)))
    
    # 对长时间闭眼区域进行平滑处理，使用固定值填充消除噪声产生的虚假峰值
    normed_processed = normed.copy()
    for (start, end) in normed_high_regions:
        normed_processed[start:end] = 0.7  # 使用固定值填充，避免噪声产生虚假峰值
    
    # 更新归一化信号为处理后的信号
    normed = normed_processed
    features, peaks, valleys = extract_blink_features(
        normed, 
        sampling_rate=sampling_rate,
        total_close_time=total_close_time_samples
    )

    if battery_level is not None:
        features["battery_level"] = battery_level

    blink_events, classified = detect_blink_events(
        features=features,
        peaks=peaks,
        valleys=valleys,
        eyelid_signal=normed,
        sampling_rate=sampling_rate,
    )

    _, _, output = assess_fatigue(
        blink_features=features,
        blink_events=blink_events,
        classified_blinks=classified,
        driving_time=driving_time,
    )

    return output
