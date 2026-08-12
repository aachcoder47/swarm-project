#!/usr/bin/env python3
"""
FrontierX World Model Node
===========================
Maintains persistent 3D spatial object registry and state.
Subscribes to /perception/detections and /perception/tracks,
publishes /world_model snapshot and provides /query_world_model service.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import PoseWithCovarianceStamped, TwistStamped
from frontierx_interfaces.msg import Detection, DetectionArray, WorldModel, WorldObject
from frontierx_interfaces.srv import QueryWorldModel


class WorldModelNode(Node):
    def __init__(self) -> None:
        super().__init__("frontierx_world_model")

        self._objects: Dict[str, WorldObject] = {}
        self._session_id = 1

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)
        reliable_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, depth=10)

        # Subscribers
        self.create_subscription(
            DetectionArray, "/perception/tracks", self._on_tracks, sensor_qos
        )

        # Publishers
        self._world_pub = self.create_publisher(WorldModel, "/world_model", reliable_qos)

        # Services
        self.create_service(
            QueryWorldModel, "/query_world_model", self._on_query_world_model
        )

        # Publisher timer (1 Hz)
        self.create_timer(1.0, self._publish_world_model)

        self.get_logger().info("World Model node initialized.")

    def _on_tracks(self, msg: DetectionArray) -> None:
        now = self.get_clock().now().to_msg()
        for det in msg.detections:
            obj_id = f"{det.class_name}_{det.track_id}" if det.track_id >= 0 else f"{det.class_name}_{det.detection_id}"
            
            if obj_id in self._objects:
                wo = self._objects[obj_id]
                wo.last_seen = now
                wo.observation_count += 1
                wo.currently_visible = True
                wo.is_stale = False
            else:
                wo = WorldObject()
                wo.object_id = obj_id
                wo.label = det.class_name
                wo.class_name = det.class_name
                wo.first_seen = now
                wo.last_seen = now
                wo.observation_count = 1
                wo.confidence = det.confidence
                wo.currently_visible = True
                wo.is_stale = False
                wo.object_state = WorldObject.STATIC
                self._objects[obj_id] = wo

    def _on_query_world_model(
        self, request: QueryWorldModel.Request, response: QueryWorldModel.Response
    ) -> QueryWorldModel.Response:
        q = request.query.lower()
        matched: List[WorldObject] = []

        for obj in self._objects.values():
            if q in ("all", "*") or q in obj.label.lower() or q in obj.class_name.lower():
                matched.append(obj)

        response.found = len(matched) > 0
        response.objects = matched
        response.summary = f"Found {len(matched)} matching objects for query '{request.query}'."
        return response

    def _publish_world_model(self) -> None:
        wm = WorldModel()
        wm.header.stamp = self.get_clock().now().to_msg()
        wm.header.frame_id = "map"
        wm.objects = list(self._objects.values())
        wm.session_id = self._session_id
        wm.loaded_from_disk = False
        self._world_pub.publish(wm)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WorldModelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
