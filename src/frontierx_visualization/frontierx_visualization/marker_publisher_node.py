#!/usr/bin/env python3
"""
FrontierX Visual Marker Publisher
===================================
Publishes 3D visual markers (Red Box target, Scout robot body),
OccupancyGrid /map, and a LiDAR range ring to Foxglove Studio & RViz2.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Point


class MarkerPublisherNode(Node):
    def __init__(self) -> None:
        super().__init__("frontierx_marker_publisher")

        qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, depth=10)
        # TRANSIENT_LOCAL so latecomers (e.g. Foxglove) receive the map immediately
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )

        self._marker_pub = self.create_publisher(MarkerArray, "/visualization_marker_array", qos)
        self._single_pub = self.create_publisher(Marker, "/visualization_marker", qos)
        self._map_pub = self.create_publisher(OccupancyGrid, "/map", map_qos)

        # Publish map once at start (latched), then repeat at 0.5 Hz
        self._map_published = False
        self.create_timer(0.5, self._publish_markers)
        self.get_logger().info("Visual Marker Publisher active.")

    def _make_map(self) -> OccupancyGrid:
        """5m x 5m empty room with perimeter walls at 5 cm/cell resolution."""
        grid = OccupancyGrid()
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.header.frame_id = "map"
        grid.info.resolution = 0.05        # 5 cm per cell
        grid.info.width = 100              # 5 m wide
        grid.info.height = 100            # 5 m tall
        grid.info.origin.position.x = -2.5
        grid.info.origin.position.y = -2.5
        grid.info.origin.position.z = 0.0
        grid.info.origin.orientation.w = 1.0

        data = [0] * (100 * 100)          # 0 = free
        for i in range(100):
            data[i] = 100                  # bottom wall
            data[99 * 100 + i] = 100       # top wall
            data[i * 100] = 100            # left wall
            data[i * 100 + 99] = 100       # right wall
        grid.data = data
        return grid

    def _publish_markers(self) -> None:
        now = self.get_clock().now().to_msg()
        markers = MarkerArray()

        # ── 1. Target Red Box ────────────────────────────────────
        red_box = Marker()
        red_box.header.stamp = now
        red_box.header.frame_id = "map"
        red_box.ns = "target_objects"
        red_box.id = 1
        red_box.type = Marker.CUBE
        red_box.action = Marker.ADD
        red_box.pose.position.x = 2.0
        red_box.pose.position.y = 1.0
        red_box.pose.position.z = 0.15
        red_box.pose.orientation.w = 1.0
        red_box.scale.x = 0.30
        red_box.scale.y = 0.30
        red_box.scale.z = 0.30
        red_box.color.r = 1.0
        red_box.color.g = 0.1
        red_box.color.b = 0.1
        red_box.color.a = 0.9
        markers.markers.append(red_box)

        # ── 2. Scout Robot Body (Cyan) ────────────────────────────
        robot_body = Marker()
        robot_body.header.stamp = now
        robot_body.header.frame_id = "base_link"
        robot_body.ns = "robot"
        robot_body.id = 2
        robot_body.type = Marker.CUBE
        robot_body.action = Marker.ADD
        robot_body.pose.position.x = 0.0
        robot_body.pose.position.y = 0.0
        robot_body.pose.position.z = 0.05
        robot_body.pose.orientation.w = 1.0
        robot_body.scale.x = 0.588        # Scout mini dimensions (m)
        robot_body.scale.y = 0.490
        robot_body.scale.z = 0.235
        robot_body.color.r = 0.0
        robot_body.color.g = 0.78
        robot_body.color.b = 1.0
        robot_body.color.a = 0.85
        markers.markers.append(robot_body)

        # ── 3. Scout Wheels ───────────────────────────────────────
        wheel_positions = [
            (0.218, 0.276), (0.218, -0.276),
            (-0.218, 0.276), (-0.218, -0.276),
        ]
        for idx, (wx, wy) in enumerate(wheel_positions):
            wheel = Marker()
            wheel.header.stamp = now
            wheel.header.frame_id = "base_link"
            wheel.ns = "wheels"
            wheel.id = 10 + idx
            wheel.type = Marker.CYLINDER
            wheel.action = Marker.ADD
            wheel.pose.position.x = wx
            wheel.pose.position.y = wy
            wheel.pose.position.z = -0.05
            wheel.pose.orientation.x = 0.707
            wheel.pose.orientation.w = 0.707
            wheel.scale.x = 0.165
            wheel.scale.y = 0.165
            wheel.scale.z = 0.067
            wheel.color.r = 0.15
            wheel.color.g = 0.15
            wheel.color.b = 0.15
            wheel.color.a = 1.0
            markers.markers.append(wheel)

        # Publish markers
        self._marker_pub.publish(markers)
        self._single_pub.publish(red_box)

        # Publish map (latched so only needs publishing once, but keep refreshing)
        self._map_pub.publish(self._make_map())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MarkerPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
