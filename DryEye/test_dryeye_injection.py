import time
import json
import random
import urllib.request
import urllib.error

API_URL = "http://127.0.0.1:3000/api/bluetooth-data"
ROOT_URL = "http://127.0.0.1:3000/"
HEADERS = {'Content-Type': 'application/json'}

def check_server():
    try:
        print(f"🔍 正在检查后端服务: {ROOT_URL}")
        with urllib.request.urlopen(ROOT_URL, timeout=2) as response:
            if response.status == 200:
                print("✅ 后端服务连接成功！")
                return True
    except urllib.error.URLError as e:
        print(f"❌ 无法连接后端服务: {e}")
        print("💡 请确保干眼症后端正在运行（python app.py）。")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False

def send_data(payload):
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(API_URL, data=data, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        print(f"\n❌ 发送失败: HTTP {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\n❌ 连接失败: {e.reason}")
        return False

class DryEyeSimulator:
    """持续状态模拟器，保证眨眼信号在多个 chunk 间连贯不断"""
    def __init__(self, sampling_rate=100):
        self.sr = sampling_rate
        self.t_total = 0.0          # 累计时间
        self.in_blink = False       # 眨眼状态标记
        self.blink_start_t = 0.0
        self.current_blink_dur = 0.0
        self.current_valley = 0.0
        self.next_blink_time = 1.0  # 第一秒开始第一次眨眼
        self.baseline = 0.8         # 高电平基线，眨眼表现为向下的波谷 (V型)

    def generate_chunk(self, duration_sec, state="normal"):
        num_samples = int(duration_sec * self.sr)
        values = []

        # 配置不同阶段的参数
        if state == "normal":
            blink_rate = 20
            base_dur = 0.15
            inc_prob = 0.05
            long_prob = 0.02
        elif state == "dry_eye":
            blink_rate = 6
            base_dur = 0.06
            inc_prob = 0.80  # 提高不完全眨眼概率
            long_prob = 0.40 # 提高长眨眼概率
        else: # poor_signal (完全随机噪声)
            for _ in range(num_samples):
                self.t_total += 1.0 / self.sr
                values.append(random.uniform(0.1, 0.9))
            return values

        # 动态计算眨眼间隔
        interval_sec = 60.0 / blink_rate if blink_rate > 0 else 999.0

        for _ in range(num_samples):
            self.t_total += 1.0 / self.sr
            noise = random.uniform(-0.02, 0.02)

            # 触发新的眨眼
            if not self.in_blink and self.t_total >= self.next_blink_time:
                self.in_blink = True
                self.blink_start_t = self.t_total
                
                is_inc = random.random() < inc_prob
                is_long = random.random() < long_prob
                
                # 新算法要求：长眨眼至少 >= 500ms
                self.current_blink_dur = 0.6 if is_long else base_dur
                
                # 新算法阈值：大于 0.4 算完全眨眼。
                # 从 0.8 跌至 0.1 (振幅0.7) = 完全眨眼
                # 从 0.8 跌至 0.6 (振幅0.2) = 不完全眨眼
                self.current_valley = 0.6 if is_inc else 0.1

            # 绘制眨眼波形
            if self.in_blink:
                elapsed = self.t_total - self.blink_start_t
                progress = elapsed / self.current_blink_dur

                if progress >= 1.0:
                    self.in_blink = False
                    val = self.baseline
                    # 安排下一次眨眼时间（加入一定随机性 ±20%）
                    self.next_blink_time = self.t_total + interval_sec * random.uniform(0.8, 1.2)
                else:
                    # 生成完美生理 V 型波谷
                    if progress < 0.3: # 下降沿 (闭眼阶段，电位下降)
                        val = self.baseline - (self.baseline - self.current_valley) * (progress / 0.3)
                    else:              # 上升沿 (睁眼阶段，电位恢复)
                        val = self.baseline - (self.baseline - self.current_valley) * ((1.0 - progress) / 0.7)
            else:
                val = self.baseline

            # 限制在 [0.0, 1.0] 并加入底噪
            values.append(max(0.0, min(1.0, val + noise)))

        return values

def run_test():
    print("🚀 开始干眼症数据传输连贯性测试...")
    print(f"🎯 目标地址: {API_URL}")
    print("-" * 50)

    scenarios = [
        {"name": "🟢 阶段一：正常状态", "state": "normal", "duration": 30, "quality": 95, "desc": "预期：各项指标正常，综合风险分 < 30"},
        {"name": "🔴 阶段二：干眼模拟", "state": "dry_eye", "duration": 30, "quality": 85, "desc": "预期：不完全眨眼激增、频率下降，风险分 > 70"},
        {"name": "⚠️ 阶段三：信号不稳定", "state": "poor_signal", "duration": 15, "quality": 30, "desc": "预期：抗干扰测试，分数不应剧烈跳变"},
    ]

    simulator = DryEyeSimulator(sampling_rate=100)

    for scenario in scenarios:
        print(f"\n{scenario['name']} - 持续 {scenario['duration']} 秒")
        print(f" 📝 {scenario['desc']}")
        start_time = time.time()

        while time.time() - start_time < scenario['duration']:
            # 每次生成 0.2 秒的数据切片
            chunk = simulator.generate_chunk(0.2, scenario['state'])

            payload = {
                "rawData": chunk,
                "timestamp": int(time.time() * 1000),
                "signalQuality": max(0, min(100, scenario['quality'] + random.randint(-5, 5))),
                "values": chunk
            }

            success = send_data(payload)
            if success:
                print("🟩", end="", flush=True)  # 用绿色方块代替小圆点更直观
            else:
                print("❌", end="", flush=True)

            time.sleep(0.2)  # 等待0.2秒，模拟真实硬件节奏
        print(" [阶段完成]")

    print("\n" + "-" * 50)
    print("✅ 全部测试结束！请观察前端界面是否按照预期的红绿黄三色进行了变化。")

if __name__ == "__main__":
    if check_server():
        run_test()