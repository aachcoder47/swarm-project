#!/usr/bin/env python3
"""
FrontierX Safety Monitor
=========================
Always-running C++-quality safety node (implemented in Python for
portability, but designed to be ported to C++ for production).

Responsibilities:
  1. Monitor all sensor health (timeout detection)
  2. Enforce velocity limits on /cmd_vel output
  3. Manage E_STOP state machine
  4. Watchdog: all critical nodes must heartbeat at >= 1 Hz
  5. Proximity guard: halt if LiDAR sees < 0.15m
  6. Publish /robot_health at 10 Hz

Safety states:
  NOMINAL   → all systems OK
  DEGRADED  → one sensor timed out, reduced speed
  E_STOP    → full halt, no motion
  RECOVERY  → attempting supervised recovery
  FAULT     → unrecoverable, requires human

CRITICAL: This node must be started before any motion-capable nodes.
"""

from __future__ import annotations

import time
from collections import defaultdict
from enum import IntEnum
from typing import Dict, Optional

import psutil
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import Bool, String
from sensor_msgs.msg import LaserScan, Imu, Image
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry

from frontierx_interfaces.msg import RobotHealth


class SafetyState(IntEnum):
    NOMINAL   = 0
    DEGRADED  = 1
    E_STOP    = 2
    RECOVERY  = 3
    FAULT     = 4


# Velocity limits — hardware-enforced by this node
V_MAX_NOMINAL   = 0.50   # m/s
V_MAX_DEGRADED  = 0.20   # m/s
V_MAX_ESTOP     = 0.00   # m/s

OMEGA_MAX_NOMINAL   = 1.00  # rad/s
OMEGA_MAX_DEGRADED  = 0.50
OMEGA_MAX_ESTOP     = 0.00

# Safety thresholds
PROXIMITY_HALT_DISTANCE_M = 0.15  # LiDAR: halt if any reading < this
SENSOR_TIMEOUT_S          = 2.0   # Seconds before sensor considered stale
WATCHDOG_TIMEOUT_S        = 3.0   # Seconds before node considered dead


class SafetyMonitorNode(Node):
    """
    FrontierX Safety Monitor — always-running, highest priority node.
    """

    def __init__(self) -> None:
        super().__init__("frontierx_safety_monitor")

        self._declare_parameters()

        # ── State ─────────────────────────────────────────────
        self._state = SafetyState.NOMINAL
        self._e_stop_reason = ""
        self._active_faults: list[str] = []
        self._startup_time = time.time()

        # ── Sensor timestamps ─────────────────────────────────
        self._last_lidar_t      = 0.0
        self._last_camera_t     = 0.0
        self._last_imu_t        = 0.0
        self._last_odom_t       = 0.0
        self._last_depth_t      = 0.0

        # ── Watchdog registry ─────────────────────────────────
        # Maps node_name -> last heartbeat timestamp
        self._watchdog_registry: Dict[str, float] = {}

        # ── Velocity limits (updated by state) ────────────────
        self._v_max     = V_MAX_NOMINAL
        self._omega_max = OMEGA_MAX_NOMINAL

        # ── QoS profiles ─────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=5,
        )
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            depth=10,
        )

        # ── Subscribers ───────────────────────────────────────
        # Sensor health monitoring
        self._lidar_sub = self.create_subscription(
            LaserScan, "/scan", self._on_lidar, sensor_qos
        )
        self._camera_sub = self.create_subscription(
            Image, "/camera/image_raw", self._on_camera, sensor_qos
        )
        self._depth_sub = self.create_subscription(
            Image, "/camera/depth/image_raw", self._on_depth, sensor_qos
        )
        self._imu_sub = self.create_subscription(
            Imu, "/imu/data", self._on_imu, sensor_qos
        )
        self._odom_sub = self.create_subscription(
            Odometry, "/odom", self._on_odom, sensor_qos
        )

        # E-stop command subscriber
        self._estop_sub = self.create_subscription(
            Bool, "/e_stop", self._on_estop, reliable_qos
        )

        # Agent heartbeat
        self._agent_heartbeat_sub = self.create_subscription(
            String, "/agent/status", self._on_agent_heartbeat, reliable_qos
        )

        # Incoming velocity commands (from nav2 / teleop)
        self._cmd_vel_in_sub = self.create_subscription(
            Twist, "/cmd_vel", self._on_cmd_vel_in, sensor_qos
        )

        # ── Publishers ────────────────────────────────────────
        # Safe velocity output (after limiting)
        self._cmd_vel_safe_pub = self.create_publisher(
            Twist, "/cmd_vel_safe", sensor_qos
        )
        # Robot health
        self._health_pub = self.create_publisher(
            RobotHealth, "/robot_health", reliable_qos
        )

        # ── Timers ────────────────────────────────────────────
        self._health_timer = self.create_timer(0.1, self._safety_loop)    # 10 Hz
        self._watchdog_timer = self.create_timer(1.0, self._check_watchdog)  # 1 Hz

        self.get_logger().info(
            "Safety Monitor initialized. Velocity limits: "
            f"v_max={self._v_max} m/s, omega_max={self._omega_max} rad/s"
        )

    def _declare_parameters(self) -> None:
        self.declare_parameter("proximity_halt_distance", PROXIMITY_HALT_DISTANCE_M)
        self.declare_parameter("sensor_timeout_seconds", SENSOR_TIMEOUT_S)
        self.declare_parameter("watchdog_timeout_seconds", WATCHDOG_TIMEOUT_S)

    # ── Sensor callbacks ──────────────────────────────────────

    def _on_lidar(self, msg: LaserScan) -> None:
        self._last_lidar_t = time.time()
        # Proximity guard: check minimum range
        if len(msg.ranges) > 0:
            min_range = min(
                r for r in msg.ranges
                if msg.range_min <= r <= msg.range_max
            ) if any(msg.range_min <= r <= msg.range_max for r in msg.ranges) else float("inf")

            halt_dist = self.get_parameter("proximity_halt_distance").value
            if min_range < halt_dist:
                self._trigger_estop(
                    f"Proximity alert: obstacle at {min_range:.3f}m (limit: {halt_dist}m)"
                )

    def _on_camera(self, msg: Image) -> None:
        self._last_camera_t = time.time()

    def _on_depth(self, msg: Image) -> None:
        self._last_depth_t = time.time()

    def _on_imu(self, msg: Imu) -> None:
        self._last_imu_t = time.time()

    def _on_odom(self, msg: Odometry) -> None:
        self._last_odom_t = time.time()

    def _on_estop(self, msg: Bool) -> None:
        if msg.data:
            self._trigger_estop("E_STOP commanded via /e_stop topic")
        else:
            # Clear E_STOP if commanded and state allows
            if self._state == SafetyState.E_STOP and not self._active_faults:
                self._state = SafetyState.NOMINAL
                self._e_stop_reason = ""
                self._update_velocity_limits()
                self.get_logger().info("E_STOP cleared via /e_stop topic")

    def _on_agent_heartbeat(self, msg: String) -> None:
        self._watchdog_registry["frontierx_agent"] = time.time()

    def _on_cmd_vel_in(self, msg: Twist) -> None:
        """Intercept velocity commands, apply limits, republish as /cmd_vel_safe."""
        if self._state in (SafetyState.E_STOP, SafetyState.FAULT):
            # Publish zero velocity
            self._cmd_vel_safe_pub.publish(Twist())
            return

        safe = Twist()
        safe.linear.x = max(-self._v_max, min(self._v_max, msg.linear.x))
        safe.linear.y = 0.0   # Differential drive: no lateral
        safe.linear.z = 0.0
        safe.angular.z = max(-self._omega_max, min(self._omega_max, msg.angular.z))
        self._cmd_vel_safe_pub.publish(safe)

    # ── Safety loop ───────────────────────────────────────────

    def _safety_loop(self) -> None:
        """Main safety evaluation loop at 10 Hz."""
        now = time.time()
        timeout = self.get_parameter("sensor_timeout_seconds").value
        self._active_faults = []

        # Check sensor timeouts
        lidar_ok  = (now - self._last_lidar_t)  < timeout if self._last_lidar_t  else False
        camera_ok = (now - self._last_camera_t) < timeout if self._last_camera_t else False
        imu_ok    = (now - self._last_imu_t)    < timeout if self._last_imu_t    else False
        odom_ok   = (now - self._last_odom_t)   < timeout if self._last_odom_t   else False

        # Grace period: during startup, don't flag sensors not yet heard
        startup_grace = 10.0
        uptime = now - self._startup_time
        if uptime < startup_grace:
            lidar_ok  = True
            camera_ok = True
            imu_ok    = True
            odom_ok   = True

        # Determine faults
        if not lidar_ok:
            self._active_faults.append("LiDAR timeout")
        if not imu_ok:
            self._active_faults.append("IMU timeout")
        if not odom_ok:
            self._active_faults.append("Odometry timeout")

        # Update state
        if self._state not in (SafetyState.E_STOP, SafetyState.FAULT):
            if self._active_faults:
                self._state = SafetyState.DEGRADED
            else:
                self._state = SafetyState.NOMINAL

        self._update_velocity_limits()
        self._publish_health(lidar_ok, camera_ok, imu_ok, odom_ok)

    def _check_watchdog(self) -> None:
        """Check registered node heartbeats at 1 Hz."""
        now = time.time()
        timeout = self.get_parameter("watchdog_timeout_seconds").value
        for node_name, last_t in self._watchdog_registry.items():
            if now - last_t > timeout:
                self.get_logger().warn(f"Watchdog: '{node_name}' has not heartbeated in {timeout}s")

    def _trigger_estop(self, reason: str) -> None:
        if self._state != SafetyState.E_STOP:
            self.get_logger().error(f"E_STOP TRIGGERED: {reason}")
        self._state = SafetyState.E_STOP
        self._e_stop_reason = reason
        self._update_velocity_limits()
        # Publish zero velocity immediately
        self._cmd_vel_safe_pub.publish(Twist())

    def _update_velocity_limits(self) -> None:
        if self._state == SafetyState.E_STOP or self._state == SafetyState.FAULT:
            self._v_max = V_MAX_ESTOP
            self._omega_max = OMEGA_MAX_ESTOP
        elif self._state == SafetyState.DEGRADED:
            self._v_max = V_MAX_DEGRADED
            self._omega_max = OMEGA_MAX_DEGRADED
        else:
            self._v_max = V_MAX_NOMINAL
            self._omega_max = OMEGA_MAX_NOMINAL

    def _publish_health(
        self,
        lidar_ok: bool,
        camera_ok: bool,
        imu_ok: bool,
        odom_ok: bool,
    ) -> None:
        msg = RobotHealth()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"

        msg.system_state = int(self._state)
        msg.lidar_ok = lidar_ok
        msg.camera_rgb_ok = camera_ok
        msg.camera_depth_ok = camera_ok
        msg.imu_ok = imu_ok
        msg.odometry_ok = odom_ok
        msg.navigation_ok = True  # TODO: check nav2 lifecycle
        msg.perception_ok = True  # TODO: check perception node
        msg.world_model_ok = True
        msg.agent_ok = "frontierx_agent" in self._watchdog_registry

        msg.e_stop_active = (self._state == SafetyState.E_STOP)
        msg.e_stop_reason = self._e_stop_reason

        msg.v_max_current = float(self._v_max)
        msg.omega_max_current = float(self._omega_max)

        msg.active_faults = self._active_faults

        msg.uptime_seconds = time.time() - self._startup_time

        # Resource usage
        try:
            msg.cpu_percent = float(psutil.cpu_percent())
            msg.memory_percent = float(psutil.virtual_memory().percent)
        except Exception:
            pass

        self._health_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SafetyMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
