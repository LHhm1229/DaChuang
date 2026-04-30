import requests
import time
import json

API_URL = "http://localhost:3000/api/bluetooth-data"
DRY_EYE_LATEST_URL = "http://localhost:3000/api/dry-eye-latest"

# 测试健康检查
def test_health_check():
    print("测试健康检查...")
    try:
        resp = requests.get("http://localhost:3000/")
        if resp.status_code == 200:
            print("健康检查成功:", resp.json())
            return True
        else:
            print("健康检查失败:", resp.status_code)
            return False
    except Exception as e:
        print("健康检查异常:", e)
        return False

# 测试统计接口
def test_stats():
    print("测试统计接口...")
    try:
        resp = requests.get("http://localhost:3000/api/stats")
        if resp.status_code == 200:
            data = resp.json()
            print("统计接口成功:")
            print("  总接收数据:", data.get('totalReceived', 0))
            print("  缓冲区大小:", data.get('bufferSize', 0))
            return True
        else:
            print("统计接口失败:", resp.status_code)
            return False
    except Exception as e:
        print("统计接口异常:", e)
        return False

# 发送测试数据
def send_test_data():
    print("发送测试数据...")
    try:
        # 生成简单的测试数据
        test_data = {
            "rawData": [0.85, 0.86, 0.84, 0.2, 0.1, 0.2, 0.85, 0.86, 0.87],
            "timestamp": int(time.time() * 1000),
            "signalQuality": 95,
            "values": [0.85, 0.86, 0.84, 0.2, 0.1, 0.2, 0.85, 0.86, 0.87]
        }
        
        resp = requests.post(API_URL, json=test_data)
        if resp.status_code == 200:
            print("数据发送成功:", resp.json())
            return True
        else:
            print("数据发送失败:", resp.status_code)
            return False
    except Exception as e:
        print("数据发送异常:", e)
        return False

# 测试干眼检测结果
def test_dryeye_result():
    print("测试干眼检测结果...")
    try:
        resp = requests.get(DRY_EYE_LATEST_URL)
        if resp.status_code == 200:
            data = resp.json()
            print("干眼检测结果:")
            print("  成功:", data.get('success'))
            if data.get('success'):
                result = data.get('data')
                print("  风险评分:", result.get('dryEyeRiskScore'))
                print("  风险等级:", result.get('dryEyeRiskLevel'))
                print("  眨眼频率:", result.get('blinkRate'))
            else:
                print("  原因:", data.get('reason'))
            return True
        else:
            print("干眼检测结果失败:", resp.status_code)
            return False
    except Exception as e:
        print("干眼检测结果异常:", e)
        return False

# 主测试函数
def main():
    print("开始测试项目数据传输和连通性...")
    print("=" * 50)
    
    # 1. 测试健康检查
    health_ok = test_health_check()
    print()
    
    # 2. 测试统计接口
    stats_ok = test_stats()
    print()
    
    # 3. 发送测试数据
    data_ok = send_test_data()
    print()
    
    # 4. 等待算法处理
    print("等待算法处理数据...")
    time.sleep(2)
    print()
    
    # 5. 测试干眼检测结果
    result_ok = test_dryeye_result()
    print()
    
    # 6. 再次测试统计接口，确认数据已接收
    print("再次测试统计接口，确认数据已接收...")
    test_stats()
    print()
    
    # 总结
    print("=" * 50)
    print("测试总结:")
    print("健康检查:", "成功" if health_ok else "失败")
    print("统计接口:", "成功" if stats_ok else "失败")
    print("数据发送:", "成功" if data_ok else "失败")
    print("结果查询:", "成功" if result_ok else "失败")
    
    if health_ok and stats_ok and data_ok:
        print("\n测试通过！项目数据传输和连通性正常")
    else:
        print("\n测试失败，需要检查相关服务")

if __name__ == "__main__":
    main()
