import numpy as np
import requests
import time
import json

API_URL = "http://localhost:3000/api/bluetooth-data"
DRY_EYE_LATEST_URL = "http://localhost:3000/api/dry-eye-latest"

# 生成模拟眨眼信号
def generate_blink_signal(duration_sec=10, fs=100, blink_rate_per_min=18):
    t = np.linspace(0, duration_sec, duration_sec * fs)
    baseline = 0.85
    signal_sim = np.full_like(t, baseline)

    blink_rate = blink_rate_per_min / 60
    blink_dur_sec = 0.15

    for i in range(int(duration_sec * blink_rate)):
        start_t = i / blink_rate
        idx = np.where((t >= start_t) & (t <= start_t + blink_dur_sec))[0]
        if len(idx) > 0:
            for j, pos in enumerate(idx):
                progress = j / len(idx)
                if progress < 0.3:
                    signal_sim[pos] = baseline - (baseline - 0.2) * (progress / 0.3)
                else:
                    signal_sim[pos] = 0.2 + (baseline - 0.2) * ((progress - 0.3) / 0.7)

    noise = np.random.normal(0, 0.03, len(t))
    signal_sim += noise
    return signal_sim.tolist()

# 发送数据到API
def send_batch(raw_data, batch_id, signal_quality=95):
    payload = {
        "rawData": raw_data,
        "timestamp": int(time.time() * 1000),
        "signalQuality": signal_quality,
        "values": raw_data
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# 测试API连通性
def test_api_connectivity():
    print("\n=== 测试 API 连通性 ===")
    try:
        # 测试健康检查
        resp = requests.get("http://localhost:3000/", timeout=3)
        if resp.status_code == 200:
            print("[OK] 健康检查成功")
            print(f"   响应: {resp.json()}")
        else:
            print(f"[FAIL] 健康检查失败: {resp.status_code}")
            return False
        
        # 测试统计接口
        resp = requests.get("http://localhost:3000/api/stats", timeout=3)
        if resp.status_code == 200:
            print("[OK] 统计接口测试成功")
            stats = resp.json()
            print(f"   总接收数据: {stats.get('totalReceived', 0)}")
            print(f"   缓冲区大小: {stats.get('bufferSize', 0)}")
        else:
            print(f"[FAIL] 统计接口测试失败: {resp.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] API 连通性测试失败: {e}")
        return False

# 主测试函数
def test_project():
    print("=" * 60)
    print("[项目测试] 数据传输和连通性测试")
    print("=" * 60)

    # 1. 测试API连通性
    api_ok = test_api_connectivity()
    if not api_ok:
        print("\n❌ API 连通性测试失败，终止测试")
        return

    # 2. 生成和发送测试数据
    print("\n=== 生成和发送测试数据 ===")
    print("生成模拟眨眼信号...")
    signal = generate_blink_signal(duration_sec=10, fs=100, blink_rate_per_min=18)
    print(f"信号长度: {len(signal)} 样本 ({len(signal)/100:.1f} 秒)")

    chunk_size = 100
    total_samples = len(signal)
    num_batches = (total_samples + chunk_size - 1) // chunk_size

    print(f"\n分批次发送数据 ({num_batches} 批次，每批 {chunk_size} 样本)...")
    print("-" * 60)

    success_count = 0
    for i in range(num_batches):
        start = i * chunk_size
        end = min(start + chunk_size, total_samples)
        chunk = signal[start:end]

        result = send_batch(chunk, batch_id=i+1)
        ts = time.strftime("%H:%M:%S")

        if "error" in result:
            print(f"  [{ts}] 批次 {i+1}/{num_batches} [FAIL] 错误: {result['error']}")
        else:
            print(f"  [{ts}] 批次 {i+1}/{num_batches} [OK] {result.get('message', 'OK')} ({len(chunk)} 样本)")
            success_count += 1

        time.sleep(0.1)

    print("-" * 60)
    print(f"\n数据发送完成: {success_count}/{num_batches} 批次成功")

    # 3. 等待算法处理
    print("\n等待算法处理数据...")
    time.sleep(3)

    # 4. 查询干眼检测结果
    print("\n=== 查询干眼检测结果 ===")
    try:
        resp = requests.get(DRY_EYE_LATEST_URL, timeout=5)
        result = resp.json()
        if result.get('success'):
            print("[OK] 干眼检测结果查询成功")
            data = result.get('data')
            print(f"   风险评分: {data.get('dryEyeRiskScore')}")
            print(f"   风险等级: {data.get('dryEyeRiskLevel')}")
            print(f"   眨眼频率: {data.get('blinkRate')} 次/分钟")
            print(f"   眼部状态: {data.get('eyeState')}")
        else:
            print(f"[INFO] 干眼检测结果: {result.get('reason')}")
    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")

    print("\n" + "=" * 60)
    print("[测试完成] 总结")
    print("=" * 60)
    print(f"API 连通性: {'[OK] 成功' if api_ok else '[FAIL] 失败'}")
    print(f"数据传输: {'[OK] 成功' if success_count == num_batches else '[WARN] 部分失败'}")

    if api_ok and success_count > 0:
        print("\n[OK] 测试通过！项目数据传输和连通性正常")
    else:
        print("\n[FAIL] 测试失败，需要检查相关服务")

if __name__ == "__main__":
    test_project()
