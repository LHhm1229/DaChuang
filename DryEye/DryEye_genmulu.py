import json
import numpy as np
import scipy.signal as signal
from typing import Tuple, Dict, List

# ========================= 1. 信号预处理与方向校准 =========================
def preprocess_and_calibrate(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    lowpass_cutoff: float = 6.0
) -> np.ndarray:
    """
    预处理并自动校准信号方向（确保眨眼时信号下降，睁眼时上升）
    """
    # 去除直流分量
    centered = raw_signal - np.mean(raw_signal)
    
    # 低通滤波
    nyq = sampling_rate / 2
    b, a = signal.butter(4, lowpass_cutoff / nyq, btype='lowpass')
    filtered = signal.filtfilt(b, a, centered)
    
    # 归一化到 [0, 1]
    min_val, max_val = np.min(filtered), np.max(filtered)
    if max_val - min_val > 1e-6:
        normalized = (filtered - min_val) / (max_val - min_val)
    else:
        normalized = filtered.copy()
    
    # 自动校准方向：正常眨眼时信号应短暂下降（产生一个向下的尖峰）
    # 计算信号的一阶差分，统计负值占比。若大多数差分是正的（上升沿多），则可能需要翻转。
    diff = np.diff(normalized)
    neg_ratio = np.sum(diff < 0) / len(diff)
    # 如果负向差分比例 < 0.4，说明信号以下降为主，眨眼可能是上升波形 -> 翻转
    if neg_ratio < 0.4:
        normalized = 1 - normalized
    
    return normalized

# ========================= 2. 基于波形的眨眼事件检测 =========================
def detect_blink_events_wavelet(
    signal_norm: np.ndarray,
    sampling_rate: int = 100,
    amplitude_thresh: float = 0.15,
    min_duration_sec: float = 0.05,
    max_duration_sec: float = 1.0,
    refractory_sec: float = 0.2
) -> List[Dict]:
    """
    通过检测下降沿-谷底-上升沿来识别眨眼事件
    
    返回每个眨眼事件的字典，包含：
        start_idx, valley_idx, end_idx, amplitude, duration_sec
    """
    events = []
    n = len(signal_norm)
    refractory_samples = int(refractory_sec * sampling_rate)
    
    # 使用平滑后的一阶差分检测显著下降沿
    # 先做一次轻度平滑
    window = max(3, int(sampling_rate * 0.02))  # 20ms平滑窗口
    if window % 2 == 0:
        window += 1
    smoothed = signal.medfilt(signal_norm, kernel_size=window)
    diff = np.diff(smoothed)
    
    # 寻找下降沿起点：差分 < -threshold_diff
    threshold_diff = amplitude_thresh / 2  # 粗略阈值
    i = 0
    while i < n - 1:
        # 跳过已经检测过的区域
        if i < refractory_samples:
            i += 1
            continue
        
        # 找下降沿起点（信号开始快速下降）
        if diff[i] < -threshold_diff:
            start = i
            # 继续向前找到谷底（信号最低点）
            valley = start
            while valley < n-1 and smoothed[valley+1] <= smoothed[valley]:
                valley += 1
            # 谷底之后找上升沿终点（信号回升到接近起点水平）
            end = valley
            # 回升阈值：回升到起点幅度的80%
            target_level = smoothed[start] - amplitude_thresh * 0.5
            while end < n-1 and smoothed[end] < target_level:
                end += 1
            # 限制最大搜索长度
            if end - start > max_duration_sec * sampling_rate:
                i = valley + 1
                continue
            
            # 计算幅度和持续时间
            amplitude = smoothed[start] - smoothed[valley]
            duration_sec = (end - start) / sampling_rate
            
            # 有效性检查
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
                # 跳过这段事件的 refractory 区间
                i = end + refractory_samples
            else:
                i = valley + 1
        else:
            i += 1
    return events

# ========================= 3. 干眼症核心指标计算 =========================
def compute_dry_eye_metrics(
    events: List[Dict],
    total_duration_sec: float
) -> Dict:
    """
    根据眨眼事件列表计算：
        - blink_rate_per_min      眨眼频率（次/分钟）
        - avg_blink_duration_ms   平均眨眼持续时间（毫秒）
        - eye_closure_ratio_pct   眼闭合比例（%）
        - incomplete_blink_ratio_pct  不完全眨眼比例（%）
        - long_blink_ratio_pct    极长时间眨眼比例（≥0.5秒）
    """
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
    
    # 平均眨眼持续时间
    avg_dur_ms = np.mean(durations_ms)
    # 眨眼频率 (次/分钟)
    rate_per_min = n_blinks / (total_duration_sec / 60)
    # 总眨眼时间（秒）
    total_blink_sec = sum(e['duration_sec'] for e in events)
    # 眼闭合比例（%）
    closure_ratio = (total_blink_sec / total_duration_sec) * 100
    closure_ratio = min(closure_ratio, 100.0)  # 上限100%
    
    # 不完全眨眼判断：幅度低于平均幅度的40%
    avg_amp = np.mean(amplitudes)
    incomplete_thresh = avg_amp * 0.4
    incomplete_count = sum(1 for a in amplitudes if a < incomplete_thresh)
    incomplete_ratio = incomplete_count / n_blinks
    
    # 极长时间眨眼（≥0.5秒）
    long_blink_count = sum(1 for d in durations_ms if d >= 500)  # 500ms
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

# ========================= 4. 干眼症风险评估 =========================
def assess_dry_eye_risk(
    blink_rate: float,
    avg_dur_ms: float,
    closure_ratio: float,
    incomplete_ratio_pct: float,
    long_blink_ratio_pct: float = 0
) -> Tuple[float, str, Dict]:
    """
    基于临床文献的干眼症风险评分（0-100）
    参考阈值：
        - 眨眼频率：正常15-25；过低<12或过高>30有风险
        - 眨眼持续时间：正常100-200ms；>250ms风险增加
        - 每分钟闭眼时间：正常0.5-1.5秒/分钟 → 对应 closure_ratio 0.8%-2.5%
        - 不完全眨眼比例：风险阈值 ≥40%
        - 极长时间眨眼比例：>5% 提示风险
    """
    # 1. 眨眼频率评分
    if blink_rate < 12:
        freq_score = 60 + (12 - blink_rate) * 5   # 极低频率
    elif blink_rate < 15:
        freq_score = (15 - blink_rate) * 20       # 12~15 线性 0~60
    elif blink_rate <= 25:
        freq_score = 0
    elif blink_rate <= 30:
        freq_score = (blink_rate - 25) * 12       # 25~30 0~60
    else:
        freq_score = min(80, 60 + (blink_rate - 30) * 2)
    
    # 2. 持续时间评分
    if avg_dur_ms <= 200:
        dur_score = 0
    elif avg_dur_ms <= 400:
        dur_score = (avg_dur_ms - 200) / 2        # 200->0, 400->100
    else:
        dur_score = min(100, 100 + (avg_dur_ms - 400) * 0.2)
    
    # 3. 眼闭合比例评分（单位%）
    # 正常期望 <2.5%，超过5%明显异常
    if closure_ratio <= 2.5:
        closure_score = 0
    elif closure_ratio <= 10:
        closure_score = (closure_ratio - 2.5) * 10   # 2.5->0, 10->75
    else:
        closure_score = min(100, 75 + (closure_ratio - 10) * 3)
    
    # 4. 不完全眨眼比例评分
    incomplete_pct = incomplete_ratio_pct
    if incomplete_pct < 30:
        inc_score = 0
    elif incomplete_pct < 40:
        inc_score = (incomplete_pct - 30) * 3       # 30->0, 40->30
    elif incomplete_pct < 60:
        inc_score = 30 + (incomplete_pct - 40) * 2  # 40->30, 60->70
    else:
        inc_score = min(95, 70 + (incomplete_pct - 60) * 0.5)
    
    # 5. 极长时间眨眼比例评分（可选）
    long_score = 0
    if long_blink_ratio_pct > 5:
        long_score = min(60, (long_blink_ratio_pct - 5) * 3)
    
    # 加权综合（可调权重）
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

# ========================= 5. 主函数（输出键名改为中文） =========================
def dry_eye_detection(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    duration_sec: float = None
) -> Dict:
    """
    干眼症检测主入口
    
    参数:
        raw_signal: 原始传感器信号（一维数组）
        sampling_rate: 采样率 (Hz)
        duration_sec: 信号时长（秒），若为None则自动计算
    返回:
        包含所有核心指标和风险评估的字典，键名为中文
    """
    # 1. 预处理与方向校准
    signal_norm = preprocess_and_calibrate(raw_signal, sampling_rate)
    
    # 2. 检测眨眼事件
    events = detect_blink_events_wavelet(signal_norm, sampling_rate)
    
    # 3. 计算总时长
    if duration_sec is None:
        total_sec = len(raw_signal) / sampling_rate
    else:
        total_sec = duration_sec
    
    # 4. 计算干眼症核心指标
    metrics = compute_dry_eye_metrics(events, total_sec)
    
    # 5. 风险评估
    risk_score, risk_level, detail = assess_dry_eye_risk(
        blink_rate=metrics['blink_rate_per_min'],
        avg_dur_ms=metrics['avg_blink_duration_ms'],
        closure_ratio=metrics['eye_closure_ratio_pct'],
        incomplete_ratio_pct=metrics['incomplete_blink_ratio_pct'],
        long_blink_ratio_pct=metrics['long_blink_ratio_pct']
    )
    
    # 6. 组装最终输出（键名改为中文）
    result = {
        "眨眼频率(次/分)": metrics['blink_rate_per_min'],
        "平均眨眼持续时间(毫秒)": metrics['avg_blink_duration_ms'],
        "眼闭合比例(%)": metrics['eye_closure_ratio_pct'],
        "不完全眨眼比例(%)": metrics['incomplete_blink_ratio_pct'],
        "极长时间眨眼比例(%)": metrics['long_blink_ratio_pct'],
        "干眼症风险评分": round(risk_score, 1),
        "干眼症风险等级": risk_level,
        "原始特征": {
            "总眨眼次数": metrics['total_blinks'],
            "不完全眨眼次数": metrics['incomplete_blinks'],
            "极长时间眨眼次数": metrics['long_blinks']
        }
    }
    return result

# ========================= 6. 示例与测试 =========================
if __name__ == "__main__":
    # 生成模拟信号：眨眼频率 ~20次/分，每次眨眼持续150ms，幅度0.6（归一化后）
    fs = 100
    duration = 60
    t = np.linspace(0, duration, duration * fs)
    baseline = 0.85  # 睁眼时信号高
    signal_sim = np.full_like(t, baseline)
    
    # 添加眨眼（信号下降）
    blink_rate = 20 / 60  # 0.333 Hz
    blink_dur_sec = 0.15
    for i in range(int(duration * blink_rate)):
        start_t = i / blink_rate
        idx = np.where((t >= start_t) & (t <= start_t + blink_dur_sec))[0]
        if len(idx) > 0:
            # 模拟眨眼波形：快速下降到0.2，再回升
            for j, pos in enumerate(idx):
                progress = j / len(idx)
                if progress < 0.3:
                    signal_sim[pos] = baseline - (baseline - 0.2) * (progress / 0.3)
                else:
                    signal_sim[pos] = 0.2 + (baseline - 0.2) * ((progress - 0.3) / 0.7)
    
    # 添加噪声
    noise = np.random.normal(0, 0.03, len(t))
    signal_sim += noise
    
    # 运行检测
    result = dry_eye_detection(signal_sim, sampling_rate=fs)
    print("干眼症检测结果（模拟数据）：")
    print(json.dumps(result, indent=2, ensure_ascii=False))