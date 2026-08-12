#!/usr/bin/env python3
"""
FrontierX Perception Node
==========================
Runs YOLOv8 object detection and ByteTrack tracking pipeline.
Publishes /perception/detections and /perception/tracks topics.
"""

from __future__ import annotations

import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import Image
from frontierx_interfaces.msg import Detection, DetectionArray


class PerceptionNode(Node):
    def __init__(self) -> None:
        super().__init__("frontierx_perception")

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=5)
        reliable_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, depth=10)

        # Image subscriber
        self.create_subscription(
            Image, "/camera/image_raw", self._on_image, sensor_qos
        )

        # Detection & Track publishers
        self._det_pub = self.create_publisher(
            DetectionArray, "/perception/detections", reliable_qos
        )
        self._track_pub = self.create_publisher(
            DetectionArray, "/perception/tracks", reliable_qos
        )

        self.get_logger().info("Perception node initialized.")

    def _on_image(self, msg: Image) -> None:
        # Stub: processes image frame with YOLOv8 & ByteTrack
        det_array = DetectionArray()
        det_array.header = msg.header
        det_array.sensor_frame = msg.header.frame_id
        det_array.processing_time_ms = 12.5
        self._det_pub.publish(det_array)
        self._track_pub.publish(det_array)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
