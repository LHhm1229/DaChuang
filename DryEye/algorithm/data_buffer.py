"""
data_buffer.py - 统一缓冲区管理模块
基于《新项目数据传输方案与设计思路》的双缓冲+滑动窗口设计
"""

import numpy as np
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class BufferConfig:
    """缓冲区配置"""
    max_size: int = 1000              # 原始数据缓冲区最大容量
    window_seconds: int = 10           # 计算窗口秒数
    sampling_rate: int = 100           # 采样率 Hz
    min_samples: int = 50              # 最小启动计算样本数 (降低以提高响应速度)
    auto_trim: bool = True            # 自动裁剪超长数据


class DataBuffer:
    """
    双缓冲架构：
    - raw_buffer: 存储原始数据点（用于调试和追溯）
    - signal_buffer: 滑动窗口信号数据（用于算法计算）
    """

    def __init__(self, config: Optional[BufferConfig] = None):
        self.config = config or BufferConfig()
        self.raw_buffer: list = []           # 原始数据缓冲
        self.signal_buffer: list = []       # 信号数据缓冲（滑动窗口）
        self.last_compute_time: Optional[float] = None
        self.compute_count: int = 0

    def add_data(self, data_point: dict) -> bool:
        """
        添加数据点到缓冲区

        Args:
            data_point: 包含 rawData, timestamp, signalQuality 的字典

        Returns:
            True 如果触发了计算
        """
        # 1. 原始数据缓冲（固定容量，自动裁剪）
        self.raw_buffer.append(data_point)
        if len(self.raw_buffer) > self.config.max_size:
            self.raw_buffer = self.raw_buffer[-self.config.max_size:]

        # 2. 信号数据缓冲（滑动窗口）
        signal_data = data_point.get("rawData", [])
        if signal_data:
            self.signal_buffer.extend(signal_data)

            max_len = self.config.window_seconds * self.config.sampling_rate
            if len(self.signal_buffer) > max_len:
                self.signal_buffer = self.signal_buffer[-max_len:]

        # 3. 检查是否满足计算条件
        if self.can_compute():
            self.last_compute_time = time.time()
            self.compute_count += 1
            return True
        return False

    def can_compute(self) -> bool:
        """是否有足够数据进行计算（带冷却：每 window_seconds 最多触发一次）"""
        if len(self.signal_buffer) < self.config.min_samples:
            return False
        if self.last_compute_time is None:
            return True
        return (time.time() - self.last_compute_time) >= self.config.window_seconds

    def get_signal_array(self) -> np.ndarray:
        """获取信号数据数组"""
        return np.asarray(self.signal_buffer, dtype=float)

    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        if not self.signal_buffer:
            return {
                "raw_buffer_size": len(self.raw_buffer),
                "signal_buffer_size": 0,
                "duration_sec": 0,
                "can_compute": False,
                "compute_count": self.compute_count
            }

        duration = len(self.signal_buffer) / self.config.sampling_rate
        return {
            "raw_buffer_size": len(self.raw_buffer),
            "signal_buffer_size": len(self.signal_buffer),
            "duration_sec": round(duration, 1),
            "can_compute": self.can_compute(),
            "compute_count": self.compute_count,
            "buffer_fill_ratio": round(len(self.signal_buffer) / (self.config.window_seconds * self.config.sampling_rate) * 100, 1)
        }

    def clear(self):
        """清空所有缓冲区"""
        self.raw_buffer.clear()
        self.signal_buffer.clear()
        self.last_compute_time = None
        self.compute_count = 0


class DataBroadcaster:
    """
    WebSocket 广播器
    基于《新项目数据传输方案与设计思路》的安全广播+心跳机制
    """

    def __init__(self):
        self.clients: set = set()
        self.heartbeat_interval: float = 15.0  # 心跳间隔秒
        self.last_heartbeat: Optional[float] = None

    def add_client(self, ws) -> None:
        """添加客户端连接"""
        self.clients.add(ws)

    def remove_client(self, ws) -> None:
        """移除客户端连接"""
        self.clients.discard(ws)

    def safe_send(self, ws, payload: dict) -> bool:
        """
        安全发送消息，失败返回False

        Args:
            ws: WebSocket 连接
            payload: 要发送的数据（会被JSON序列化）

        Returns:
            True 发送成功，False 发送失败
        """
        import json
        try:
            ws.send(json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:
            return False

    def broadcast(self, payload: dict, msg_type: str = "broadcast") -> dict:
        """
        广播消息到所有客户端，自动清理失效连接

        Args:
            payload: 要广播的数据
            msg_type: 消息类型（用于日志）

        Returns:
            广播结果统计 {"sent": 数量, "failed": 数量, "total": 数量}
        """
        dead_clients = []
        sent = 0
        failed = 0

        for client in list(self.clients):
            if self.safe_send(client, payload):
                sent += 1
            else:
                dead_clients.append(client)
                failed += 1

        # 清理失效连接
        for client in dead_clients:
            self.clients.discard(client)

        return {"sent": sent, "failed": failed, "total": len(self.clients) + len(dead_clients)}

    def broadcast_if_valid(self, condition: bool, payload: dict) -> bool:
        """
        条件广播（仅当条件满足时才广播）

        Args:
            condition: 布尔条件
            payload: 要广播的数据

        Returns:
            广播是否执行
        """
        if condition:
            self.broadcast(payload)
            return True
        return False

    def update_heartbeat(self):
        """更新心跳时间戳"""
        self.last_heartbeat = time.time()

    def should_send_heartbeat(self) -> bool:
        """检查是否应该发送心跳"""
        if self.last_heartbeat is None:
            return True
        return (time.time() - self.last_heartbeat) >= self.heartbeat_interval

    def get_client_count(self) -> int:
        """获取当前客户端数量"""
        return len(self.clients)

    def clear_clients(self):
        """清空所有客户端"""
        self.clients.clear()
