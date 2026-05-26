"""
dry_eye.py - 干眼症检测算法（优化版 v2）

与 blink_fatigue.py 对齐的信号处理水平。

统一约定（全链路一致，与 blink_fatigue.py 对齐）：
  - 预处理输出 normalized_signal：范围约在 [0,1]，值越大=越闭合/越像眨眼峰
  - peaks：眨眼峰（高值点）
  - 事件 duration 使用 HWHM（半高宽），不依赖噪声谷值

改进要点（v2 相对 v1）：
  1. 长闭眼区域检测 + Mask机制（对齐疲劳算法）：>500ms高值区域不计入正常眨眼统计
  2. 不完全眨眼判断：改用归一化振幅中位数的55%作为阈值，替代原始振幅均值60%
  3. 长眨眼阈值：混合绝对基准（400ms）+ 个人基准（+2σ），自适应调整
  4. 评分：不完全眨眼权重从0.25→0.30，时长权重从0.15→0.10，闭合Sigmoid参数校准
  5. 输出：增加 eyeStatus、debug 字段，对齐疲劳算法输出格式
"""

from __future__ import annotations

from typing import Tuple, Dict, List, Optional

import numpy as np
from scipy import signal as sp_signal
from scipy.ndimage import grey_opening, grey_closing, median_filter

__all__ = [
    "preprocess_dry_eye_signal",
    "detect_blink_events",
    "compute_dry_eye_metrics",
    "assess_dry_eye_risk",
    "run_dry_eye_pipeline",
    "reset_dry_eye_state",
]


# =========================
# 辅助函数
# =========================

def sigmoid(x, midpoint: float = 0.0, steepness: float = 1.0):
    return 1.0 / (1.0 + np.exp(-steepness * (x - midpoint)))


def _compute_signal_quality(sig: np.ndarray) -> float:
    """信号质量估计 [0,1]：波动过小或饱和均扣分。"""
    x = np.asarray(sig, dtype=float)
    if x.size < 10:
        return 0.0
    amp = float(np.percentile(x, 95) - np.percentile(x, 5))
    amp_score = float(np.clip(amp / 0.25, 0.0, 1.0))
    sat_ratio = float(np.mean((x < 0.01) | (x > 0.99)))
    sat_score = 1.0 - float(np.clip(sat_ratio / 0.30, 0.0, 1.0))
    return float(np.clip(0.6 * amp_score + 0.4 * sat_score, 0.0, 1.0))


def _compute_physical_threshold(sig: np.ndarray, factor: float = 1.0) -> float:
    """动态阈值 = 均值 + factor × 标准差。"""
    return float(np.mean(sig) + factor * np.std(sig))


def _schmitt_trigger_status(
    sig: np.ndarray,
    sampling_rate: int,
    high_thresh: float = 0.6,
    low_thresh: float = 0.4,
    min_duration_ms: float = 200,
) -> str:
    """施密特触发器判断当前眼睛状态，防止抖动误判。"""
    min_dur_samples = int(min_duration_ms * sampling_rate / 1000)
    x = np.asarray(sig, dtype=float)
    if x.size < min_dur_samples:
        return "open"
    window = min_dur_samples
    if x.size < window:
        return "open"
    win_mean = np.convolve(x, np.ones(window) / window, mode="valid")
    status = "open"
    consec_high = 0
    for v in win_mean:
        if v >= high_thresh:
            consec_high += 1
            if consec_high >= window // 2:
                status = "closed"
                break
        elif v <= low_thresh:
            consec_high = 0
            status = "open"
    return status


def _detect_long_close_regions(
    normalized_signal: np.ndarray,
    sampling_rate: int,
    threshold: float = 0.70,
    min_duration_sec: float = 0.5,
) -> Tuple[List[Tuple[int, int]], float]:
    """
    检测归一化信号中的长闭眼区域（持续高值 > threshold 且时长 > min_duration_sec）。
    返回 (long_close_regions, total_long_close_time_sec)。
    """
    x = np.asarray(normalized_signal, dtype=float)
    min_samples = int(min_duration_sec * sampling_rate)
    regions: List[Tuple[int, int]] = []

    in_high = False
    region_start = 0
    for i in range(x.size):
        if x[i] >= threshold and not in_high:
            in_high = True
            region_start = i
        elif x[i] < threshold and in_high:
            in_high = False
            if i - region_start >= min_samples:
                regions.append((region_start, i))

    if in_high and x.size - region_start >= min_samples:
        regions.append((region_start, x.size))

    total_sec = sum((e - s) / sampling_rate for s, e in regions)
    return regions, total_sec


# =========================
# 预处理
# =========================

def preprocess_dry_eye_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    drift_window_sec: float = 2.0,
    smooth_cutoff_hz: float = 8.0,
    enhance_signal: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    干眼症信号预处理（对齐 blink_fatigue.preprocess_eyelid_signal）。

    返回 (normalized_signal, raw_copy)：
      - normalized_signal：[0,1]，高值 = 眨眼峰（眼睑闭合时信号大）
      - raw_copy：原始信号副本（用于振幅比较）

    处理链路：
      无信号检测 → 自适应信号增强 → 去均值 → 中值滤波去脉冲噪声
      → 形态学基线去除 → 低通滤波 → 平坦检测 → 分位数归一化 → 极性校正
    """
    x = np.asarray(raw_signal, dtype=float)
    raw_copy = x.copy()

    if x.ndim != 1 or x.size < max(50, sampling_rate):
        return np.full_like(x, 0.5), raw_copy

    # 无信号检测
    if float(np.max(x) - np.min(x)) < 0.01:
        print("[ALGO-DRY] 警告：信号幅值过小，传感器可能未佩戴")
        return np.zeros_like(x), raw_copy

    # 1. 自适应信号增强（放大微小变化，对齐疲劳算法）
    if enhance_signal:
        sig_std = float(np.std(x))
        target_std = 0.15
        if 0 < sig_std < target_std:
            gain = min(target_std / sig_std, 10.0)
            x = x * gain
            print(f"[ALGO-DRY] 信号增强: std={sig_std:.4f} → 放大 {gain:.2f} 倍")

    # 2. 去均值
    x = x - np.mean(x)

    # 3. 中值滤波去脉冲噪声（~10ms 窗口，必须奇数）
    med_win = max(3, int(sampling_rate * 0.01))
    if med_win % 2 == 0:
        med_win += 1
    x = median_filter(x, size=med_win)

    # 4. 形态学基线去除（2 秒窗口，grey_opening+closing 估计基线漂移）
    size_drift = int(max(3, round(drift_window_sec * sampling_rate)))
    trend_open = grey_opening(x, size=size_drift)
    baseline = grey_closing(trend_open, size=size_drift)
    x = x - baseline

    # 5. 低通滤波（8Hz 保留眨眼细节，Butterworth 4 阶）
    nyquist = sampling_rate / 2.0
    cutoff = float(np.clip(smooth_cutoff_hz / nyquist, 1e-6, 0.9999))
    b, a = sp_signal.butter(4, cutoff, "lowpass")
    x = sp_signal.filtfilt(b, a, x)

    # 6. 平坦信号检测（峰峰值 < 5 × MAD 噪声基底视为无效）
    noise_floor = float(np.median(np.abs(np.diff(x)))) + 1e-9
    if float(np.max(x) - np.min(x)) < 5.0 * noise_floor:
        return np.full_like(x, 0.5), raw_copy

    # 7. 分位数归一化（5%/95% 抗尖峰）
    lo = float(np.percentile(x, 5))
    hi = float(np.percentile(x, 95))
    rng = hi - lo
    if rng < 1e-6:
        return np.full_like(x, 0.5), raw_copy
    normalized = np.clip((x - lo) / rng, 0.0, 1.0)

    # 8. 极性校正：确保眨眼特征为高值峰（与 blink_fatigue.py 统一）
    if normalized.size > 1:
        diff = np.diff(normalized)
        pos_ratio = float(np.sum(diff > 0) / len(diff))
        if pos_ratio < 0.4:
            normalized = 1.0 - normalized

    return normalized, raw_copy


# =========================
# 眨眼事件检测
# =========================

def detect_blink_events(
    normalized_signal: np.ndarray,
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    personal_baseline: Optional[Dict] = None,
    long_close_regions: Optional[List[Tuple[int, int]]] = None,
) -> Tuple[List[Dict], np.ndarray, np.ndarray]:
    """
    基于 find_peaks + HWHM 的眨眼事件检测（对齐 blink_fatigue.extract_blink_features）。

    改进点（v2）：
    - Mask 机制：长闭眼区域（由调用方传入）置零，不参与峰值检测
    - 不完全眨眼：归一化振幅 < 中位振幅×55% 标记为不完全（替代原始振幅均值60%）
    - 长眨眼阈值：自适应混合（0.7×400ms + 0.3×个人基准），替代固定500ms
    - 事件dict新增 is_incomplete / is_long 标志，供 compute_dry_eye_metrics 使用

    返回 (events, peaks_idx, valleys_idx)
    """
    x = np.asarray(normalized_signal, dtype=float)
    raw = np.asarray(raw_signal, dtype=float)

    if personal_baseline is None:
        personal_baseline = {
            "avg_blink_duration": 0.15,
            "std_blink_duration": 0.05,
            "sample_count": 0,
        }

    events: List[Dict] = []

    if x.size < max(50, sampling_rate // 2):
        return events, np.array([], dtype=int), np.array([], dtype=int)

    # --- Mask 机制：长闭眼区域置零 ---
    x_masked = x.copy()
    for s, e in (long_close_regions or []):
        x_masked[s:e] = 0.0

    # 动态高度阈值
    dyn_thresh = _compute_physical_threshold(x, factor=0.8)
    height_threshold = float(np.clip(dyn_thresh, 0.20, 0.65))

    # 峰宽度约束（30ms ~ 1500ms）
    min_width = max(3, int(0.03 * sampling_rate))
    max_width = min(150, int(1.5 * sampling_rate))

    # 最小峰间距（不应期 100ms）
    min_distance = max(1, int(0.10 * sampling_rate))

    # find_peaks（在 masked 信号上）
    raw_peaks, _ = sp_signal.find_peaks(
        x_masked,
        height=height_threshold,
        distance=min_distance,
        width=(min_width, max_width),
    )
    raw_peaks = np.asarray(raw_peaks, dtype=int)

    # 物理上限（≤ 4 次/秒，生理极限）
    max_peaks = max(1, int(x.size / sampling_rate * 4))
    if len(raw_peaks) > max_peaks:
        raw_peaks = raw_peaks[:max_peaks]

    # 150ms 峰合并（一次眨眼不应被分裂）
    merge_win = int(0.15 * sampling_rate)
    merged: List[int] = []
    if len(raw_peaks) > 0:
        group = [int(raw_peaks[0])]
        for i in range(1, len(raw_peaks)):
            if raw_peaks[i] - raw_peaks[i - 1] < merge_win:
                group.append(int(raw_peaks[i]))
            else:
                merged.append(max(group, key=lambda p: float(x[p])))
                group = [int(raw_peaks[i])]
        merged.append(max(group, key=lambda p: float(x[p])))
    peaks = np.array(merged, dtype=int)

    if peaks.size == 0:
        return events, peaks, np.array([], dtype=int)

    # 谷值检测
    valley_cands, _ = sp_signal.find_peaks(-x, distance=max(1, sampling_rate // 10))
    valley_cands = np.asarray(valley_cands, dtype=int)
    search_win = max(10, sampling_rate // 2)

    def local_min_idx(l: int, r: int) -> int:
        seg = x[l:r]
        return l if seg.size == 0 else int(l + np.argmin(seg))

    all_valleys: List[int] = []
    valid_peaks: List[int] = []

    for p in peaks:
        pv_cands = valley_cands[(valley_cands < p) & (valley_cands >= p - search_win)]
        nv_cands = valley_cands[(valley_cands > p) & (valley_cands <= p + search_win)]
        pv = int(pv_cands[-1]) if pv_cands.size > 0 else local_min_idx(max(0, p - search_win), p)
        nv = int(nv_cands[0]) if nv_cands.size > 0 else local_min_idx(p + 1, min(x.size, p + 1 + search_win))
        if pv < p < nv:
            all_valleys.extend([pv, nv])
            valid_peaks.append(int(p))

    peaks = np.array(valid_peaks, dtype=int)
    valleys_arr = np.array(sorted(set(all_valleys)), dtype=int)

    if peaks.size == 0:
        return events, peaks, valleys_arr

    # --- 自适应长眨眼阈值（对齐疲劳算法混合阈值策略）---
    abs_long_ms = 400.0
    personal_dur_ms = personal_baseline["avg_blink_duration"] * 1000.0
    personal_std_ms = personal_baseline["std_blink_duration"] * 1000.0
    personal_long_ms = personal_dur_ms + 2.0 * personal_std_ms
    long_thresh_ms = max(200.0, 0.7 * abs_long_ms + 0.3 * min(personal_long_ms, 700.0))

    # HWHM 持续时间 + 对称性检查
    global_min = float(np.min(x))

    # 先收集所有峰的归一化振幅，用于不完全眨眼的中位数阈值
    norm_amps: List[float] = []
    for p in peaks:
        pv_cands_tmp = valleys_arr[valleys_arr < p]
        pv_tmp = int(pv_cands_tmp[-1]) if pv_cands_tmp.size > 0 else max(0, p - search_win)
        norm_amps.append(float(x[p] - x[pv_tmp]))

    amp_median = float(np.median(norm_amps)) if norm_amps else 0.0
    incomplete_thresh = amp_median * 0.55  # 低于中位振幅55%视为不完全眨眼

    for idx, p in enumerate(peaks):
        # HWHM
        half_h = (float(x[p]) + global_min) / 2.0
        li = int(p)
        while li > 0 and x[li] > half_h:
            li -= 1
        ri = int(p)
        while ri < x.size - 1 and x[ri] > half_h:
            ri += 1
        hwhm_sec = (ri - li) / sampling_rate

        # 对称性（上升沿 vs 下降沿时长比，过滤伪影）
        rise = p - li
        fall = ri - p
        symmetry = float(min(rise, fall) / (max(rise, fall) + 1e-6))

        # 归一化幅度
        pv_cands2 = valleys_arr[valleys_arr < p]
        nv_cands2 = valleys_arr[valleys_arr > p]
        pv = int(pv_cands2[-1]) if pv_cands2.size > 0 else max(0, p - search_win)
        nv = int(nv_cands2[0]) if nv_cands2.size > 0 else min(x.size - 1, p + search_win)
        norm_amp = float(x[p] - x[pv])

        # 原始信号幅度
        safe_start = pv
        safe_end = min(nv + 1, raw.size)
        raw_amp = float(np.max(raw[safe_start:safe_end]) - np.min(raw[safe_start:safe_end]))

        # 过滤条件：幅度达标 + 对称性 > 0.25
        if norm_amp >= height_threshold * 0.7 and symmetry > 0.25:
            duration_ms = hwhm_sec * 1000.0
            events.append({
                "peak": int(p),
                "start": li,
                "end": ri,
                "amplitude": norm_amp,
                "raw_amplitude": raw_amp,
                "duration_sec": hwhm_sec,
                "duration_ms": duration_ms,
                "symmetry": symmetry,
                "is_incomplete": norm_amp < incomplete_thresh,
                "is_long": duration_ms >= long_thresh_ms,
            })

    return events, peaks, valleys_arr


# =========================
# 干眼指标计算
# =========================

def compute_dry_eye_metrics(
    events: List[Dict],
    total_duration_sec: float,
    normalized_signal: Optional[np.ndarray] = None,
    long_close_time_sec: float = 0.0,
) -> Dict:
    """
    计算干眼症核心指标。

    改进点（v2）：
    - closure_ratio 加入长闭眼时间（对齐疲劳算法 eye_closure_ratio 计算方式）
    - 不完全眨眼/长眨眼统计改用事件 is_incomplete/is_long 标志
    """
    sig_quality = _compute_signal_quality(normalized_signal) if normalized_signal is not None and len(normalized_signal) > 0 else 0.5
    n_blinks = len(events)

    if n_blinks == 0:
        print("[ALGO-DRY] 未检测到眨眼事件")
        return {
            "blink_rate_per_min": 0.0,
            "avg_blink_duration_ms": 0.0,
            "eye_closure_ratio_pct": 0.0,
            "incomplete_blink_ratio_pct": 100.0,
            "long_blink_ratio_pct": 0.0,
            "total_blinks": 0,
            "incomplete_blinks": 0,
            "long_blinks": 0,
            "avg_symmetry": 0.0,
            "signal_quality": sig_quality,
        }

    durations_ms = [e["duration_ms"] for e in events]
    symmetries = [e["symmetry"] for e in events]

    avg_dur_ms = float(np.mean(durations_ms))
    avg_symmetry = float(np.mean(symmetries))
    rate_per_min = n_blinks / (total_duration_sec / 60.0)

    # 闭合比例：HWHM 总时长 + 长闭眼时长
    total_blink_sec = sum(e["duration_sec"] for e in events)
    closure_ratio = min((total_blink_sec + long_close_time_sec) / total_duration_sec * 100.0, 100.0)

    # 不完全眨眼：用事件标志（v2改进）
    incomplete_count = sum(1 for e in events if e.get("is_incomplete", False))

    # 长眨眼：用事件标志（v2改进，自适应阈值）
    long_count = sum(1 for e in events if e.get("is_long", False))

    result = {
        "blink_rate_per_min": round(rate_per_min, 1),
        "avg_blink_duration_ms": round(avg_dur_ms, 1),
        "eye_closure_ratio_pct": round(closure_ratio, 1),
        "incomplete_blink_ratio_pct": round(incomplete_count / n_blinks * 100.0, 1),
        "long_blink_ratio_pct": round(long_count / n_blinks * 100.0, 1),
        "total_blinks": n_blinks,
        "incomplete_blinks": incomplete_count,
        "long_blinks": long_count,
        "avg_symmetry": round(avg_symmetry, 3),
        "signal_quality": sig_quality,
    }
    print(
        f"[ALGO-DRY] {n_blinks} 次眨眼 | 频率={result['blink_rate_per_min']}/min | "
        f"HWHM均值={result['avg_blink_duration_ms']}ms | "
        f"闭合={result['eye_closure_ratio_pct']}% | 不完全={result['incomplete_blink_ratio_pct']}% | "
        f"长眨眼={result['long_blink_ratio_pct']}%"
    )
    return result


# =========================
# 风险评分
# =========================

def assess_dry_eye_risk(
    blink_rate: float,
    avg_dur_ms: float,
    closure_ratio: float,
    incomplete_ratio_pct: float,
    long_blink_ratio_pct: float = 0.0,
    signal_quality: float = 1.0,
) -> Tuple[float, str, Dict]:
    """
    6 维 Sigmoid 加权评分。

    改进（v2）：
    - 不完全眨眼权重 0.25→0.30（干眼核心指标，提高权重）
    - 时长权重 0.15→0.10（HWHM 时长区分度弱于不完全眨眼）
    - 不完全眨眼 Sigmoid 中点 40→30，让风险更早出现
    - 频率 U型中点对调至 12/25（正常区间更符合干眼患者实际）
    """
    # 频率 U 型（正常 12~25 次/分钟，偏低或偏高均有风险）
    freq_score = 100.0 * (sigmoid(blink_rate, 12.0, -0.35) + sigmoid(blink_rate, 25.0, 0.40)) / 2.0
    # 时长 U 型（HWHM 正常约 60~250ms）
    dur_score = 100.0 * (sigmoid(avg_dur_ms, 55.0, -0.05) + sigmoid(avg_dur_ms, 280.0, 0.015)) / 2.0
    # 闭合比例 U 型（正常 3~8%）
    closure_score = 100.0 * (sigmoid(closure_ratio, 2.0, -2.0) + sigmoid(closure_ratio, 10.0, 1.5)) / 2.0
    # 不完全眨眼（递增，干眼核心指标，中点下调至30%让风险更早出现）
    inc_score = 100.0 * sigmoid(incomplete_ratio_pct, midpoint=30.0, steepness=0.10)
    # 长眨眼（递增）
    long_score = 100.0 * sigmoid(long_blink_ratio_pct, midpoint=20.0, steepness=0.15)
    # 信号质量（越低 = 越可疑 = 风险越高）
    sq_score = 100.0 * (1.0 - float(np.clip(signal_quality, 0.0, 1.0)))

    weights = {
        "freq": 0.15,
        "duration": 0.10,
        "closure": 0.25,
        "incomplete": 0.30,
        "long": 0.10,
        "signal_quality": 0.10,
    }
    risk_score = (
        freq_score * weights["freq"]
        + dur_score * weights["duration"]
        + closure_score * weights["closure"]
        + inc_score * weights["incomplete"]
        + long_score * weights["long"]
        + sq_score * weights["signal_quality"]
    )

    # 完全没有眨眼 → 高风险兜底
    if blink_rate == 0:
        risk_score = max(risk_score, 90.0)

    risk_score = float(np.clip(risk_score, 0.0, 100.0))
    level = ["低风险", "中风险", "高风险"][min(int(np.digitize(risk_score, [30, 60])), 2)]

    detail = {
        "blink_rate_per_min": blink_rate,
        "avg_blink_duration_ms": avg_dur_ms,
        "closure_sec_per_min": round(closure_ratio / 100.0 * 60.0, 2),
        "incomplete_blink_ratio_pct": incomplete_ratio_pct,
        "long_blink_ratio_pct": long_blink_ratio_pct,
        "signal_quality": round(signal_quality, 2),
        "dry_eye_risk_score": round(risk_score, 1),
        "dry_eye_risk_level": level,
        "debug_scores": (
            f"F:{int(freq_score)} D:{int(dur_score)} C:{int(closure_score)} "
            f"I:{int(inc_score)} L:{int(long_score)} SQ:{int(sq_score)}"
        ),
    }
    return risk_score, level, detail


# =========================
# 状态机（滑动窗口 + 校准 + 个人基准）
# =========================

class DryEyePipelineState:
    """
    滑动窗口缓存 + 冷启动校准 + 个人基准（对齐 blink_fatigue.FatiguePipelineState）。
    """

    def __init__(
        self,
        window_size_sec: float = 10.0,
        sampling_rate: int = 100,
        calibration_duration_sec: float = 5.0,
    ):
        self.window_size_sec = window_size_sec
        self.window_size_samples = int(window_size_sec * sampling_rate)
        self.sampling_rate = sampling_rate
        self.buffer: List[float] = []

        self.calibration_duration_sec = calibration_duration_sec
        self.is_calibrating = True
        self.calibration_samples: List[float] = []
        self.calibration_complete = False

        self.personal_baseline: Dict = {
            "avg_blink_duration": 0.15,
            "std_blink_duration": 0.05,
            "sample_count": 0,
            "calibrated": False,
        }

    def update(self, new_samples: np.ndarray) -> None:
        samples = new_samples.tolist()

        if self.is_calibrating:
            self.calibration_samples.extend(samples)
            if len(self.calibration_samples) / self.sampling_rate >= self.calibration_duration_sec:
                self._complete_calibration()

        self.buffer.extend(samples)
        if len(self.buffer) > self.window_size_samples:
            excess = len(self.buffer) - self.window_size_samples
            self.buffer = self.buffer[excess:]

    def _complete_calibration(self) -> None:
        if self.calibration_complete:
            return
        self.is_calibrating = False
        self.calibration_complete = True
        dur = len(self.calibration_samples) / self.sampling_rate
        print(f"[ALGO-DRY] 校准完成：{len(self.calibration_samples)} 样本 ({dur:.1f}s)")
        self.personal_baseline["calibrated"] = True

    def get_valid_window(self) -> Tuple[np.ndarray, float]:
        if self.is_calibrating:
            data = np.array(self.calibration_samples, dtype=float)
            return data, float(len(data) / self.sampling_rate)
        if len(self.buffer) < 10:
            return np.array([]), 0.0
        data = np.array(self.buffer, dtype=float)
        return data, float(len(data) / self.sampling_rate)

    def compute_data_quality(self) -> float:
        src = self.buffer if not self.is_calibrating else self.calibration_samples
        if len(src) < 10:
            return 0.0
        x = np.array(src, dtype=float)
        if float(np.max(x) - np.min(x)) < 0.01:
            return 0.2
        if float(np.var(x)) < 0.0001:
            return 0.3
        return 1.0

    def update_personal_baseline(self, avg_dur_ms: float) -> None:
        """指数移动平均更新个人眨眼基线（慢速，避免短期噪声干扰）。"""
        alpha = 0.1
        n = self.personal_baseline["sample_count"]
        if n == 0:
            self.personal_baseline["avg_blink_duration"] = avg_dur_ms / 1000.0
        else:
            self.personal_baseline["avg_blink_duration"] = (
                (1.0 - alpha) * self.personal_baseline["avg_blink_duration"]
                + alpha * avg_dur_ms / 1000.0
            )
        self.personal_baseline["sample_count"] += 1


# 全局单例（生命周期由 app.py 通过 reset_dry_eye_state 管理）
_dry_eye_state: Optional[DryEyePipelineState] = None


def _default_dry_eye_output(is_calibrating: bool = True) -> Dict:
    return {
        "blinkRate": 0.0,
        "avgBlinkDuration": 0.0,
        "eyeClosureRatio": 0.0,
        "incompleteBlinkRatio": 0.0,
        "longBlinkRatio": 0.0,
        "dryEyeRiskScore": 0.0,
        "dryEyeRiskLevel": "低风险",
        "totalBlinks": 0,
        "incompleteBlinks": 0,
        "longBlinks": 0,
        "avgSymmetryRatio": 0.0,
        "signalQuality": 0.0,
        "eyeStatus": "open",
        "isCalibrating": is_calibrating,
        "dataQuality": 0.0,
        "details": {
            "dry_eye_risk_score": 0.0,
            "dry_eye_risk_level": "低风险",
            "debug_scores": "校准中..." if is_calibrating else "数据不足",
        },
        "debug": {
            "longCloseRegions": 0,
            "totalLongCloseTime": 0.0,
            "dataQuality": 0.0,
            "isCalibrating": is_calibrating,
            "personalBaselineMs": 150.0,
        },
    }


def reset_dry_eye_state() -> None:
    """切换用户或重新开始监测时调用，重置滑动窗口、校准和个人基准。"""
    global _dry_eye_state
    _dry_eye_state = None
    print("[ALGO-DRY] 状态已重置")


# =========================
# 主入口
# =========================

def run_dry_eye_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    duration_sec: Optional[float] = None,
    window_size_sec: float = 10.0,
    calibration_duration_sec: float = 5.0,
) -> Dict:
    """
    干眼症算法主入口（对齐 blink_fatigue.run_fatigue_pipeline 设计）。

    流程（v2 新增步骤标注 *）：
      new_samples → DryEyePipelineState（滑动窗口 + 个人基准）
                  → preprocess_dry_eye_signal（形态学基线 + 信号增强 + 低通 + 归一化）
                  → *_detect_long_close_regions（长闭眼Mask，对齐疲劳算法）
                  → detect_blink_events（find_peaks + HWHM + 动态阈值 + 峰合并 + Mask）
                  → compute_dry_eye_metrics（含长闭眼时间）
                  → assess_dry_eye_risk（6 维 Sigmoid）
    """
    global _dry_eye_state

    raw_np = np.asarray(raw_signal, dtype=float)
    finite_mask = np.isfinite(raw_np)
    if not np.all(finite_mask):
        raw_np = raw_np[finite_mask]

    # 初始化状态机
    if _dry_eye_state is None or _dry_eye_state.sampling_rate != sampling_rate:
        _dry_eye_state = DryEyePipelineState(window_size_sec, sampling_rate, calibration_duration_sec)

    _dry_eye_state.update(raw_np)
    window_data, window_duration = _dry_eye_state.get_valid_window()

    # 数据量不足
    if window_duration < 3.0:
        print(f"[ALGO-DRY] 数据不足 {window_duration:.1f}s，跳过")
        return _default_dry_eye_output(is_calibrating=_dry_eye_state.is_calibrating)

    # 数据质量检查
    data_quality = _dry_eye_state.compute_data_quality()
    if data_quality < 0.3:
        print(f"[ALGO-DRY] 数据质量过低 {data_quality:.2f}，跳过")
        return _default_dry_eye_output(is_calibrating=_dry_eye_state.is_calibrating)

    # 预处理
    signal_norm, signal_raw = preprocess_dry_eye_signal(window_data, sampling_rate)

    # 长闭眼区域检测（>0.5秒高值区域，对齐疲劳算法 Mask 机制）
    long_close_regions, total_long_close_time = _detect_long_close_regions(
        signal_norm, sampling_rate, threshold=0.70, min_duration_sec=0.5
    )
    if long_close_regions:
        print(f"[ALGO-DRY] 检测到 {len(long_close_regions)} 个长闭眼区域，总时长 {total_long_close_time:.2f}s")

    # 眨眼检测
    events, peaks, valleys = detect_blink_events(
        signal_norm, signal_raw, sampling_rate,
        personal_baseline=_dry_eye_state.personal_baseline,
        long_close_regions=long_close_regions,
    )

    total_sec = window_duration if duration_sec is None else duration_sec
    metrics = compute_dry_eye_metrics(events, total_sec, signal_norm, long_close_time_sec=total_long_close_time)

    # 更新个人基准
    if metrics["total_blinks"] > 0:
        _dry_eye_state.update_personal_baseline(metrics["avg_blink_duration_ms"])

    risk_score, risk_level, detail = assess_dry_eye_risk(
        blink_rate=metrics["blink_rate_per_min"],
        avg_dur_ms=metrics["avg_blink_duration_ms"],
        closure_ratio=metrics["eye_closure_ratio_pct"],
        incomplete_ratio_pct=metrics["incomplete_blink_ratio_pct"],
        long_blink_ratio_pct=metrics["long_blink_ratio_pct"],
        signal_quality=metrics["signal_quality"],
    )

    # 眼睛状态（施密特触发器，对齐疲劳算法）
    eye_status = _schmitt_trigger_status(signal_norm, sampling_rate)

    return {
        "blinkRate": metrics["blink_rate_per_min"],
        "avgBlinkDuration": metrics["avg_blink_duration_ms"],
        "eyeClosureRatio": metrics["eye_closure_ratio_pct"],
        "incompleteBlinkRatio": metrics["incomplete_blink_ratio_pct"],
        "longBlinkRatio": metrics["long_blink_ratio_pct"],
        "dryEyeRiskScore": round(risk_score, 1),
        "dryEyeRiskLevel": risk_level,
        "totalBlinks": metrics["total_blinks"],
        "incompleteBlinks": metrics["incomplete_blinks"],
        "longBlinks": metrics["long_blinks"],
        "avgSymmetryRatio": metrics["avg_symmetry"],
        "signalQuality": round(metrics["signal_quality"], 2),
        "eyeStatus": eye_status,
        "isCalibrating": _dry_eye_state.is_calibrating,
        "dataQuality": round(data_quality, 2),
        "details": detail,
        "debug": {
            "longCloseRegions": len(long_close_regions),
            "totalLongCloseTime": round(total_long_close_time, 3),
            "dataQuality": round(data_quality, 2),
            "isCalibrating": _dry_eye_state.is_calibrating,
            "personalBaselineMs": round(_dry_eye_state.personal_baseline["avg_blink_duration"] * 1000, 1),
            "debugScores": detail.get("debug_scores", ""),
        },
    }
