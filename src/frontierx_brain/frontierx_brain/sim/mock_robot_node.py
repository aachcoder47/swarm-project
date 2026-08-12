"""
Component 14 Helper: Mock Multi-Robot ROS 2 Node
================================================
Simulates 3+ physical robot bodies over ROS 2 topics and actions
for testing the Central AI Brain without physical hardware attached.
"""

from __future__ import annotations

import math
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped

from frontierx_brain.observability.observability import brain_logger


class MockRobotNode(Node):
    """Simulates multi-body telemetry heartbeats and action server execution."""

    def __init__(self, robot_id: str = "ugv_scout_01") -> None:
        super().__init__(f"mock_robot_{robot_id}")
        self.robot_id = robot_id
        self._x = 0.0
        self._y = 0.0
        self._battery = 95.0

        self.publisher_ = self.create_publisher(String, f"/{self.robot_id}/telemetry", 10)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info(f"Mock Robot Node initialized for body: {self.robot_id}")

    def timer_callback(self) -> None:
        msg = String()
        # Simulate slight position jitter/movement
        self._x += 0.01 * math.sin(time.time())
        self._y += 0.01 * math.cos(time.time())

        payload = f'{{"robot_id": "{self.robot_id}", "battery_percentage": {self.battery:.1f}, "x": {self._x:.3f}, "y": {self._y:.3f}}}'
        msg.data = payload
        self.publisher_.publish(msg)

    @property
    def battery(self) -> float:
        self._battery = max(10.0, self._battery - 0.001)
        return self._battery


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockRobotNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
