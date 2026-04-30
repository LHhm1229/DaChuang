import numpy as np
from scipy import signal
from typing import Tuple, List, Dict, Optional

# ---------- 包含以下形态学辅助函数 ----------
def grey_opening(signal: np.ndarray, size: int) -> np.ndarray:
    """灰度形态学开运算（腐蚀+膨胀）"""
    from scipy.ndimage import grey_erosion, grey_dilation
    structure = np.ones(size)
    eroded = grey_erosion(signal, footprint=structure)
    opened = grey_dilation(eroded, footprint=structure)
    return opened

def grey_closing(signal: np.ndarray, size: int) -> np.ndarray:
    """灰度形态学闭运算（膨胀+腐蚀）"""
    from scipy.ndimage import grey_dilation, grey_erosion
    structure = np.ones(size)
    dilated = grey_dilation(signal, footprint=structure)
    closed = grey_erosion(dilated, footprint=structure)
    return closed

"""
灰度腐蚀：取窗口内的局部最小值，作用是“削平”信号中的正向尖峰
灰度膨胀：取窗口内的局部最大值，作用是“填平”信号中的负向凹陷
开运算（先腐蚀后膨胀）：能够消除信号中比结构元素更窄的正向脉冲，而保持整体趋势形状
"""


# ---------- 预处理函数 ----------
def preprocess_eyelid_signal(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    drift_window_sec: float = 2.0, #基线漂移通常由头部缓慢移动等引起，频率在 0.05 Hz 以下，2秒的窗口正好大于绝大多数眨眼持续时间，远小于漂移周期
    smooth_cutoff_hz: float = 6.5 #截止频率
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    针对眼皮传感器的专用预处理
    返回: (滤波后信号, 归一化信号, 基线漂移趋势)
    """
    x = np.asarray(raw_signal, dtype=float)
    if x.ndim != 1 or x.size < max(50, sampling_rate):
        centered = x - np.mean(x) if x.size > 0 else x
        return centered, centered, centered

    centered_signal = x - np.mean(x)   #去直流：消除传感器可能的固定偏置电压，使信号围绕零值波动，便于后续形态学处理

    size_drift = int(max(3, round(drift_window_sec * sampling_rate)))
    trend_open = grey_opening(centered_signal, size=size_drift)
    trend_base = grey_closing(trend_open, size=size_drift)
    baseline_removed = centered_signal - trend_base

    nyquist = sampling_rate / 2.0
    cutoff = smooth_cutoff_hz / nyquist
    cutoff = float(min(max(cutoff, 1e-6), 0.999999))

    b, a = signal.butter(8, cutoff, "lowpass")
    filtered_signal = signal.filtfilt(b, a, baseline_removed)

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
    """兼容旧接口"""
    return preprocess_eyelid_signal(raw_signal, sampling_rate)


# ========== 衔接部分：眼动特征提取（微调参数以适应预处理输出） ==========
def extract_eye_movement_bands(
    preprocessed_signal: np.ndarray,   # 直接使用 preprocess_eyelid_signal 返回的 filtered_signal
    fs: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    从已去除基线漂移的信号中分离 SEM 和 REM 频带
    注意：输入信号已经过你的预处理（去直流+去漂移+低通6.5Hz），
    这里只需进一步高通0.1Hz去除残留慢漂，然后分频带。
    """
    # 高通0.1Hz，进一步确保只保留眼动成分（去除眼皮缓慢开合趋势）
    sos_highpass = signal.butter(4, 0.1, btype='high', fs=fs, output='sos')
    eye_signal = signal.sosfilt(sos_highpass, preprocessed_signal)

    # SEM 频带 0.1-0.5 Hz
    sos_sem = signal.butter(4, [0.1, 0.5], btype='band', fs=fs, output='sos')
    sem_signal = signal.sosfilt(sos_sem, eye_signal)

    # REM 频带 1-5 Hz（你的低通截止6.5Hz，所以1-5Hz信息完整保留）
    sos_rem = signal.butter(4, [1, 5], btype='band', fs=fs, output='sos')
    rem_signal = signal.sosfilt(sos_rem, eye_signal)

    return sem_signal, rem_signal


def detect_sem_events(
    sem_signal: np.ndarray,
    time: np.ndarray,
    fs: int,
    amp_thresh: float = 0.05,
    min_dur: float = 0.5
) -> List[Tuple[float, float, float]]:
    """检测慢速眼动事件（同前，略作优化）"""
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
    """检测快速眼动事件（返回正负峰值索引）"""
    from scipy.signal import find_peaks
    min_dist = int(min_dist_sec * fs)
    peaks_pos, _ = find_peaks(rem_signal, height=amp_thresh, distance=min_dist)
    peaks_neg, _ = find_peaks(-rem_signal, height=amp_thresh, distance=min_dist)
    return peaks_pos, peaks_neg


def compute_epoch_eye_features(
    epoch_signal: np.ndarray,
    epoch_time: np.ndarray,
    fs: int
) -> Dict[str, float]:
    """计算一个30秒纪元的眼动特征"""
    sem_sig, rem_sig = extract_eye_movement_bands(epoch_signal, fs)
    rem_pos, rem_neg = detect_rem_events(rem_sig, epoch_time, fs)
    sem_events = detect_sem_events(sem_sig, epoch_time, fs)

    feats = {
        'rem_density': (len(rem_pos) + len(rem_neg)) / 30.0,
        'sem_count': len(sem_events),
        'rem_energy': np.sum(rem_sig ** 2),
        'sem_energy': np.sum(sem_sig ** 2),
        'rem_sem_ratio': np.sum(rem_sig ** 2) / (np.sum(sem_sig ** 2) + 1e-6),
        'signal_std': np.std(epoch_signal),
    }
    return feats


# ========== 基于规则的睡眠分期（无需修改） ==========
def rule_based_sleep_staging(features: Dict[str, float], prev_stage: Optional[int] = None) -> int:
    """
    基于AASM眼动规则的睡眠分期
    输入: 一个纪元的特征字典
    返回: 0=Wake, 1=N1, 2=N2, 3=N3, 4=REM
    """
    # 阈值可根据实际传感器信号强度微调
    if features['rem_density'] > 0.5 or features['sem_count'] > 2:
        return 0  # Wake
    if features['rem_density'] > 0.3 and features['rem_sem_ratio'] > 2.0:
        return 4  # REM
    if features['sem_count'] >= 1 and features['rem_density'] < 0.2:
        return 1  # N1
    if features['signal_std'] < 0.05:
        return 3  # N3
    else:
        return 2  # N2


# ========== 完整流程示例 ==========
def analyze_sleep_from_eyelid_sensor(
    raw_signal: np.ndarray,
    sampling_rate: int = 100,
    epoch_duration_sec: int = 30
) -> Tuple[np.ndarray, List[Dict]]:
    """
    从原始传感器信号到睡眠分期的完整流水线
    """
    # 1. 预处理
    filtered, normalized, baseline = preprocess_eyelid_signal(raw_signal, sampling_rate)

    # 2. 生成等间隔时间轴
    total_duration = len(normalized) / sampling_rate
    time_axis = np.linspace(0, total_duration, len(normalized))

    # 3. 切分为30秒一周期并逐周期分析
    epoch_samples = epoch_duration_sec * sampling_rate
    n_epochs = len(normalized) // epoch_samples

    stage_sequence = []
    epoch_features_list = []

    prev_stage = None
    for i in range(n_epochs):
        start_idx = i * epoch_samples
        end_idx = start_idx + epoch_samples
        epoch_sig = normalized[start_idx:end_idx]   # 或使用 filtered 均可
        epoch_t = time_axis[start_idx:end_idx]

        feats = compute_epoch_eye_features(epoch_sig, epoch_t, sampling_rate)
        epoch_features_list.append(feats)

        stage = rule_based_sleep_staging(feats, prev_stage)
        stage_sequence.append(stage)
        prev_stage = stage

    return np.array(stage_sequence), epoch_features_list


# ========== 可视化辅助（可选） ==========
# def plot_hypnogram(stage_sequence: np.ndarray, epoch_duration_sec: int = 30):
#     import matplotlib.pyplot as plt
#     hours = np.arange(len(stage_sequence)) * epoch_duration_sec / 3600
#     stage_names = {0: 'Wake', 1: 'N1', 2: 'N2', 3: 'N3', 4: 'REM'}
#     colors = {0: 'red', 1: 'lightblue', 2: 'blue', 3: 'darkblue', 4: 'purple'}
#
#     fig, ax = plt.subplots(figsize=(14, 3))
#     for i, s in enumerate(stage_sequence):
#         ax.fill_between([hours[i], hours[i+1]], 0, 1, color=colors[s], alpha=0.6)
#     ax.set_yticks([])
#     ax.set_xlabel('Time (hours)')
#     ax.set_title('Sleep Hypnogram from Eyelid Sensor')
#     # 图例
#     import matplotlib.patches as mpatches
#     patches = [mpatches.Patch(color=c, label=stage_names[k]) for k, c in colors.items()]
#     ax.legend(handles=patches, bbox_to_anchor=(1.01, 1), loc='upper left')
#     plt.tight_layout()
#     return fig



def main(raw_signal: np.ndarray, sampling_rate: int = 100):
    """
    主函数：分析原始信号，输出可直接用于网页显示的关键睡眠指标。

    参数
    ----------
    raw_signal : np.ndarray
        原始传感器数据（一维数组）
    sampling_rate : int
        采样频率，默认100Hz

    输出（打印）
    ----------
    - 睡眠总时长（分钟）
    - 各睡眠阶段时长及占比
    - 睡眠效率（%）
    - 睡眠阶段时间轴（阶段序列列表）
    - 简易睡眠质量评分（0-100）
    - 当前睡眠阶段（若为实时流最后一纪元）
    """
    # 1. 调用完整分析流水线，获得阶段序列
    stage_sequence, _ = analyze_sleep_from_eyelid_sensor(raw_signal, sampling_rate)

    # 2. 计算基本指标
    epoch_duration_sec = 30
    n_epochs = len(stage_sequence)
    total_minutes = n_epochs * epoch_duration_sec / 60.0

    # 各阶段计数
    wake_epochs = np.sum(stage_sequence == 0)
    n1_epochs = np.sum(stage_sequence == 1)
    n2_epochs = np.sum(stage_sequence == 2)
    n3_epochs = np.sum(stage_sequence == 3)
    rem_epochs = np.sum(stage_sequence == 4)

    def to_minutes(epochs): return epochs * epoch_duration_sec / 60.0

    tst_min = to_minutes(n1_epochs + n2_epochs + n3_epochs + rem_epochs)  # 总睡眠时间
    se = (tst_min / total_minutes * 100) if total_minutes > 0 else 0.0

    # 3. 简易睡眠质量评分（权重：深睡+REM 有利，清醒+浅睡减分）
    #    公式可自定义，这里只是一个示例
    score = (n3_epochs * 3 + rem_epochs * 2 - wake_epochs * 1) / max(n_epochs, 1)
    score = max(0, min(100, 50 + score * 50))  # 映射到0-100区间

    # 4. 当前睡眠阶段（取最后一个纪元）
    current_stage = stage_sequence[-1] if len(stage_sequence) > 0 else None
    stage_names = {0: "清醒", 1: "浅睡N1", 2: "浅睡N2", 3: "深睡", 4: "REM"}

    # 5. 输出到控制台（网页后端可通过JSON获取）
    print("========== 睡眠分析结果 ==========")
    print(f"记录总时长: {total_minutes:.1f} 分钟")
    print(f"总睡眠时间: {tst_min:.1f} 分钟")
    print(f"睡眠效率: {se:.1f}%")
    print(f"睡眠质量评分: {score:.1f} / 100")
    print(f"当前睡眠阶段: {stage_names.get(current_stage, '未知')}")
    print("\n各阶段时长:")
    print(f"  清醒  : {to_minutes(wake_epochs):.1f} 分钟 ({wake_epochs/n_epochs*100:.1f}%)")
    print(f"  浅睡N1: {to_minutes(n1_epochs):.1f} 分钟 ({n1_epochs/n_epochs*100:.1f}%)")
    print(f"  浅睡N2: {to_minutes(n2_epochs):.1f} 分钟 ({n2_epochs/n_epochs*100:.1f}%)")
    print(f"  深睡  : {to_minutes(n3_epochs):.1f} 分钟 ({n3_epochs/n_epochs*100:.1f}%)")
    print(f"  REM  : {to_minutes(rem_epochs):.1f} 分钟 ({rem_epochs/n_epochs*100:.1f}%)")
    print("\n睡眠阶段时间轴（每30秒一个阶段）:")
    print(stage_sequence.tolist())  # 可直接序列化为JSON

    # 如果需要返回给Web框架（如Flask），可构造字典
    result = {
        "total_minutes": round(total_minutes, 1),
        "tst_minutes": round(tst_min, 1),
        "sleep_efficiency": round(se, 1),
        "quality_score": round(score, 1),
        "current_stage": current_stage,
        "stage_sequence": stage_sequence.tolist(),
        "stage_durations": {
            "wake": round(to_minutes(wake_epochs), 1),
            "n1": round(to_minutes(n1_epochs), 1),
            "n2": round(to_minutes(n2_epochs), 1),
            "n3": round(to_minutes(n3_epochs), 1),
            "rem": round(to_minutes(rem_epochs), 1)
        }
    }
    return result


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 假设您已经用传感器采集了一段信号，存入变量 raw_data
    # 这里用随机噪声模拟（实际使用时请替换为真实数据）
    duration_sec = 8 * 3600  # 8小时
    sampling_rate = 100
    simulated_signal = np.random.randn(duration_sec * sampling_rate) * 0.1 + 0.5
    # 模拟入睡后信号波动减小
    simulated_signal[int(0.5 * len(simulated_signal)):] *= 0.3

    output = main(simulated_signal, sampling_rate)
    # 若使用Flask，可直接 return jsonify(output)