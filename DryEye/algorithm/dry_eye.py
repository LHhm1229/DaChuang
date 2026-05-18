from __future__ import annotations

from typing import Tuple, Dict, List, Optional
import numpy as np
from scipy import signal
from scipy.ndimage import median_filter

__all__ = [
    "preprocess_and_calibrate",
    "detect_blink_events_wavelet",
    "compute_dry_eye_metrics",
    "assess_dry_eye_risk",
    "run_dry_eye_pipeline",
    "reset_dry_eye_state",
]


# =========================
# 辅助函数
# =========================

def sigmoid(x: np.ndarray, midpoint: float = 0.0, steepness: float = 1.0) -> np.ndarray:
    return 1 / (1 + np.exp(-steepness * (x - midpoint)))


def quantile_normalize(sig: np.ndarray, lower_q: float = 0.05, upper_q: float = 0.95) -> np.ndarray:
    """分位数归一化，用 5%/95% 分位数代替绝对极值，避免单个尖峰压缩整体范围"""
    lower = float(np.quantile(sig, lower_q))
    upper = float(np.quantile(sig, upper_q))
    range_val = upper - lower
    if range_val < 1e-6:
        # 信号基本平坦，返回近零值；后续极性翻转后得到全1，检测器不会找到事件
        return (sig - np.mean(sig)) / (float(np.std(sig)) + 1e-6)
    normalized = (sig - lower) / range_val
    return np.clip(normalized, 0.0, 1.0)


def highpass_filter(sig: np.ndarray, sampling_rate: int, cutoff_freq: float = 0.5) -> np.ndarray:
    """Butterworth 高通滤波，去除基线漂移（参数名 sig 避免覆盖 scipy.signal 模块名）"""
    nyquist = 0.5 * sampling_rate
    b, a = signal.butter(4, cutoff_freq / nyquist, btype='high')
    return signal.filtfilt(b, a, sig)


def _compute_signal_quality(sig: np.ndarray) -> float:
    """信号质量估计 [0,1]：波动过小或饱和均扣分"""
    if sig.size < 10:
        return 0.0
    amp = float(np.percentile(sig, 95) - np.percentile(sig, 5))
    amp_score = float(np.clip(amp / 0.25, 0.0, 1.0))
    sat_ratio = float(np.mean((sig < 0.01) | (sig > 0.99)))
    sat_score = 1.0 - float(np.clip(sat_ratio / 0.30, 0.0, 1.0))
    return float(np.clip(0.6 * amp_score + 0.4 * sat_score, 0.0, 1.0))


# =========================
# 预处理
# =========================

def preprocess_and_calibrate(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    highpass_cutoff: float = 0.5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    返回 (normalized_signal, raw_signal_copy)。
    normalized 用于检测，raw_signal_copy 用于不完全眨眼振幅判断。

    平坦信号检测：
      对滤波后的信号，若峰峰值 < 5 × 噪声基底（MAD），视为无意义信号，
      直接返回全 0.5（检测器得到 diff=0，不会找到任何事件）。
    """
    signal_raw = raw_signal.copy()

    # 高通滤波去除基线漂移
    filtered = highpass_filter(raw_signal, sampling_rate, highpass_cutoff)

    # 平坦信号判断（MAD 估计噪声基底）
    noise_floor = float(np.median(np.abs(np.diff(filtered)))) + 1e-9
    signal_range = float(np.max(filtered) - np.min(filtered))
    if signal_range < 5.0 * noise_floor:
        return np.full_like(filtered, 0.5), signal_raw

    # 分位数归一化
    normalized = quantile_normalize(filtered)

    # 极性校正：确保眨眼特征为向下波谷
    if len(normalized) > 1:
        diff = np.diff(normalized)
        neg_ratio = float(np.sum(diff < 0) / len(diff))
        if neg_ratio < 0.4:
            normalized = 1.0 - normalized

    return normalized, signal_raw


# =========================
# 眨眼事件检测
# =========================

def detect_blink_events_wavelet(
    signal_norm: np.ndarray,
    signal_raw: np.ndarray,
    sampling_rate: int = 100,
    amplitude_thresh: float = 0.15,
    min_duration_ms: float = 50.0,
    max_duration_ms: float = 2000.0,
    refractory_ms: float = 100.0
) -> List[Dict]:
    """
    基于一阶差分 + 形态学过滤的眨眼检测。

    改进点：
    - scipy median_filter（C 实现，比纯 Python 快 10x）
    - 动态基线追踪（500ms 滑动中值）
    - 对称性检查（symmetry_ratio > 0.3）过滤伪影
    - 斜率方差检查（slope_variance < 0.1）过滤尖峰噪声
    - amplitude_thresh = 0.15（高于典型噪声 < 0.1）
    """
    events: List[Dict] = []
    n = len(signal_norm)
    refractory_samples = int(refractory_ms * sampling_rate / 1000)
    min_dur_samples = int(min_duration_ms * sampling_rate / 1000)
    max_dur_samples = int(max_duration_ms * sampling_rate / 1000)

    # 中值平滑（窗口必须为奇数）
    win = max(3, int(sampling_rate * 0.02))
    if win % 2 == 0:
        win += 1
    smoothed = median_filter(signal_norm, size=win)

    diff1 = np.diff(smoothed)
    diff2 = np.diff(diff1)

    # 动态基线（500ms 窗口，必须奇数）
    bl_win = int(sampling_rate * 0.5)
    if bl_win % 2 == 0:
        bl_win += 1
    baseline = signal.medfilt(signal_norm, bl_win)

    i = 0
    while i < n - 1:
        if i < refractory_samples:
            i += 1
            continue

        # 下降沿触发
        if diff1[i] < -amplitude_thresh / 3:
            start = i

            # 寻找波谷
            valley = start
            while valley < n - 2 and smoothed[valley + 1] <= smoothed[valley]:
                valley += 1

            # 寻找恢复点
            end = valley
            target = baseline[start] - amplitude_thresh * 0.3
            while end < n - 1 and smoothed[end] < target:
                end += 1

            dur_samples = end - start
            if dur_samples < min_dur_samples or dur_samples > max_dur_samples:
                i = valley + 1
                continue

            norm_amp = float(smoothed[start] - smoothed[valley])
            safe_end = min(end + 1, len(signal_raw))
            raw_amp = float(np.max(signal_raw[start:safe_end]) - np.min(signal_raw[start:safe_end]))

            # 对称性：上升沿 vs 下降沿时长比
            rise_time = valley - start
            fall_time = end - valley
            symmetry_ratio = float(min(rise_time, fall_time) / (max(rise_time, fall_time) + 1e-6))

            # 斜率平滑度（二阶差分方差）
            seg = diff2[start:end] if end - start > 2 else np.array([])
            slope_var = float(np.var(seg)) if seg.size > 0 else 0.0

            if norm_amp >= amplitude_thresh and symmetry_ratio > 0.3 and slope_var < 0.1:
                dur_sec = dur_samples / sampling_rate
                events.append({
                    'start': start,
                    'valley': valley,
                    'end': end,
                    'amplitude': norm_amp,
                    'raw_amplitude': raw_amp,
                    'duration_sec': dur_sec,
                    'duration_ms': dur_sec * 1000.0,
                    'symmetry_ratio': symmetry_ratio,
                })
                i = end + refractory_samples
            else:
                i = valley + 1
        else:
            i += 1

    return events


# =========================
# 指标计算
# =========================

def compute_dry_eye_metrics(events: List[Dict], total_duration_sec: float) -> Dict:
    n_blinks = len(events)
    if n_blinks == 0:
        return {
            'blink_rate_per_min': 0, 'avg_blink_duration_ms': 0,
            'eye_closure_ratio_pct': 0, 'incomplete_blink_ratio_pct': 100.0,
            'long_blink_ratio_pct': 0, 'total_blinks': 0,
            'incomplete_blinks': 0, 'long_blinks': 0, 'avg_symmetry_ratio': 0.0,
        }

    durations_ms = [e['duration_ms'] for e in events]
    raw_amplitudes = [e['raw_amplitude'] for e in events]
    symmetries = [e['symmetry_ratio'] for e in events]

    avg_dur_ms = float(np.mean(durations_ms))
    avg_symmetry = float(np.mean(symmetries))
    rate_per_min = n_blinks / (total_duration_sec / 60.0)
    total_blink_sec = sum(e['duration_sec'] for e in events)
    closure_ratio = min((total_blink_sec / total_duration_sec) * 100.0, 100.0)

    # 不完全眨眼：动态阈值（低于平均振幅 60% 视为不完全）
    avg_raw_amp = float(np.mean(raw_amplitudes)) if raw_amplitudes else 0.0
    incomplete_thresh = avg_raw_amp * 0.6
    incomplete_count = sum(1 for a in raw_amplitudes if a < incomplete_thresh)
    incomplete_ratio = incomplete_count / n_blinks

    long_blink_count = sum(1 for d in durations_ms if d >= 500.0)
    long_blink_ratio = long_blink_count / n_blinks

    result = {
        'blink_rate_per_min': round(rate_per_min, 1),
        'avg_blink_duration_ms': round(avg_dur_ms, 1),
        'eye_closure_ratio_pct': round(closure_ratio, 1),
        'incomplete_blink_ratio_pct': round(incomplete_ratio * 100.0, 1),
        'long_blink_ratio_pct': round(long_blink_ratio * 100.0, 1),
        'total_blinks': n_blinks,
        'incomplete_blinks': incomplete_count,
        'long_blinks': long_blink_count,
        'avg_symmetry_ratio': round(avg_symmetry, 3),
    }
    print(f"[ALGO-DRY] {n_blinks} 次眨眼 | 频率={result['blink_rate_per_min']}/min | "
          f"闭合={result['eye_closure_ratio_pct']}% | 不完全={result['incomplete_blink_ratio_pct']}%")
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
    avg_symmetry_ratio: float = 0.5,
) -> Tuple[float, str, Dict]:
    """
    用 Sigmoid 函数实现平滑 U 型/递增曲线，避免硬编码分段带来的跳变。
    """
    # 频率 U 型（正常 15~25 次/分钟）
    freq_score = 100.0 * (sigmoid(blink_rate, 10, -0.4) + sigmoid(blink_rate, 30, 0.4)) / 2.0
    # 时长 U 型（正常 100~250ms）
    dur_score = 100.0 * (sigmoid(avg_dur_ms, 75, -0.03) + sigmoid(avg_dur_ms, 300, 0.015)) / 2.0
    # 闭合比例 U 型（正常 3%~8%）
    closure_score = 100.0 * (sigmoid(closure_ratio, 2, -2) + sigmoid(closure_ratio, 10, 1.5)) / 2.0
    # 不完全眨眼（递增）
    inc_score = 100.0 * sigmoid(incomplete_ratio_pct, midpoint=40, steepness=0.08)
    # 长眨眼（递增）
    long_score = 100.0 * sigmoid(long_blink_ratio_pct, midpoint=20, steepness=0.15)
    # 对称性（越高越好，低对称 = 可疑噪声）
    symmetry_score = 100.0 * (1.0 - sigmoid(avg_symmetry_ratio, midpoint=0.6, steepness=10))

    weights = {
        'freq': 0.15, 'duration': 0.15, 'closure': 0.25,
        'incomplete': 0.25, 'long': 0.10, 'symmetry': 0.10,
    }
    risk_score = (
        freq_score * weights['freq'] + dur_score * weights['duration'] +
        closure_score * weights['closure'] + inc_score * weights['incomplete'] +
        long_score * weights['long'] + symmetry_score * weights['symmetry']
    )
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
        "avg_symmetry_ratio": avg_symmetry_ratio,
        "dry_eye_risk_score": round(risk_score, 1),
        "dry_eye_risk_level": level,
        "debug_scores": (
            f"F:{int(freq_score)} D:{int(dur_score)} C:{int(closure_score)} "
            f"I:{int(inc_score)} L:{int(long_score)} S:{int(symmetry_score)}"
        ),
    }
    return risk_score, level, detail


# =========================
# 状态机（滑动窗口 + 校准）
# =========================

class DryEyePipelineState:
    """
    滑动窗口缓存 + 冷启动校准。
    算法内部维护最近 window_size_sec 秒的数据，
    app.py 每次只传当前批次新样本，无需外部管理缓冲。
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

    def update(self, new_samples: np.ndarray) -> None:
        samples = new_samples.tolist()

        if self.is_calibrating:
            self.calibration_samples.extend(samples)
            cal_sec = len(self.calibration_samples) / self.sampling_rate
            if cal_sec >= self.calibration_duration_sec:
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
        print(f"[ALGO-DRY] 校准完成！{len(self.calibration_samples)} 个样本 ({dur:.1f}s)")

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
        x = np.array(src)
        if float(np.max(x) - np.min(x)) < 0.01:
            return 0.2
        if float(np.var(x)) < 0.0001:
            return 0.3
        return 1.0


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
        "isCalibrating": is_calibrating,
        "dataQuality": 0.0,
        "details": {
            "dry_eye_risk_score": 0.0,
            "dry_eye_risk_level": "低风险",
            "debug_scores": "校准中..." if is_calibrating else "数据不足",
        },
    }


def reset_dry_eye_state() -> None:
    """切换用户或重新开始监测时调用，重置滑动窗口和校准状态"""
    global _dry_eye_state
    _dry_eye_state = None
    print("[ALGO-DRY] 状态已重置")


# =========================
# 主入口
# =========================

def run_dry_eye_pipeline(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    duration_sec: float = None,
    window_size_sec: float = 10.0,
    calibration_duration_sec: float = 5.0,
) -> Dict:
    """
    app.py 调用入口：每次只传当前批次新样本，算法内部维护滑动窗口。

    流程：
      new_samples → DryEyePipelineState（滑动窗口）
                  → preprocess_and_calibrate（高通 + 分位数归一化 + 平坦检测 + 极性）
                  → detect_blink_events_wavelet（差分检测 + 对称/斜率过滤）
                  → compute_dry_eye_metrics
                  → assess_dry_eye_risk（Sigmoid 评分）
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
    signal_norm, signal_raw = preprocess_and_calibrate(window_data, sampling_rate)

    # 眨眼检测
    events = detect_blink_events_wavelet(signal_norm, signal_raw, sampling_rate)

    total_sec = window_duration if duration_sec is None else duration_sec
    metrics = compute_dry_eye_metrics(events, total_sec)
    risk_score, risk_level, detail = assess_dry_eye_risk(
        blink_rate=metrics['blink_rate_per_min'],
        avg_dur_ms=metrics['avg_blink_duration_ms'],
        closure_ratio=metrics['eye_closure_ratio_pct'],
        incomplete_ratio_pct=metrics['incomplete_blink_ratio_pct'],
        long_blink_ratio_pct=metrics['long_blink_ratio_pct'],
        avg_symmetry_ratio=metrics['avg_symmetry_ratio'],
    )

    return {
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
        "isCalibrating": _dry_eye_state.is_calibrating,
        "dataQuality": round(data_quality, 2),
        "details": detail,
    }
