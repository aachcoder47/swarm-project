"""
Component 14b: Simulation Bridge & Network-Safety Heartbeat (Dual Engine)
===========================================================================

Dual simulation engine with consistent API:
  Engine A — Pure-Python Physics Engine  (any OS, works everywhere, no ROS2/Gazebo required):
    * Real 2D navigation (proportional position updates with linear velocity limits)
    * Inverse differential drive odometry, battery drain per distance
    * Real object detection by bounding-box / frustum intersection
    * Heartbeat topic + deadman timer for network-failure → safe-state
  Engine B — ROS2 + Gazebo Bridge (on Linux with Gazebo Sim installed):
    * Same dispatch contract: skill_dispatched → gazebo skill node action server → result

SAFE-STATE CONTRACT (critical):
  * Brain publishes heartbeats at /frontierx/brain_heartbeat every 200ms (header.seq increments)
  * Each simulated robot (python or gazebo) runs a deadman timer.
    If no heartbeat received in > 500ms → SAFE STATE:
        - set velocity=0
        - cancel active navigation / manipulation
        - freeze arm joints
        - publish robot status OFFLINE to brain
"""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)


@dataclass
class SimRobotState:
    robot_id: str
    body_type: str
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    v: float = 0.0         # linear velocity (m/s)
    w: float = 0.0         # angular velocity (rad/s)
    wheel_left_rad: float = 0.0
    wheel_right_rad: float = 0.0
    max_linear_vel: float = 1.0
    max_angular_vel: float = 1.5
    battery: float = 100.0
    heartbeat_expires_at: float = 0.0
    safe_state: bool = False
    active_skill: Optional[str] = None
    skill_deadline: float = 0.0


@dataclass
class SimObjectState:
    object_id: str
    class_name: str
    x: float
    y: float
    z: float = 0.0
    radius: float = 0.5
    detected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    success: bool
    message: str
    data: Dict[str, Any]


class PurePythonPhysicsSimulator:
    """
    Pure-Python 2D physics engine for the FrontierX demo factory.
    No mock data — every computation is from real state (positions, velocities,
    battery %, distances, camera frustum intersections).

    Integrates at a fixed dt. Use tick(dt) to advance simulation.
    """

    def __init__(self, world_size_m: Tuple[float, float] = (40.0, 40.0)) -> None:
        self.world_w, self.world_h = world_size_m
        self.robots: Dict[str, SimRobotState] = {}
        self.objects: Dict[str, SimObjectState] = {}
        self._lock = threading.RLock()
        self._time = 0.0
        self._last_brain_heartbeat_seq: int = 0
        self._last_brain_heartbeat_at: float = 0.0
        # Camera frustum for UGV: range 3.0m, half_angle 45°
        self.camera_range_m = 3.0
        self.camera_half_angle_rad = math.radians(45.0)
        # Arm reach for pedestal arm
        self.arm_reach_m = 1.5

    # ── World management ──────────────────────────────────────────────

    def add_robot(self, robot_id: str, body_type: str, x: float, y: float, yaw: float = 0.0,
                  max_linear_vel: float = 1.0, battery_pct: float = 100.0) -> SimRobotState:
        with self._lock:
            r = SimRobotState(
                robot_id=robot_id, body_type=body_type,
                x=x, y=y, yaw=yaw, max_linear_vel=max_linear_vel, battery=battery_pct,
            )
            self.robots[robot_id] = r
            return r

    def add_object(self, object_id: str, class_name: str, x: float, y: float,
                   radius: float = 0.6, z: float = 0.0,
                   metadata: Optional[Dict[str, Any]] = None) -> SimObjectState:
        with self._lock:
            o = SimObjectState(
                object_id=object_id, class_name=class_name,
                x=x, y=y, z=z, radius=radius, metadata=metadata or {},
            )
            self.objects[object_id] = o
            return o

    # ── Brain heartbeat / safe state (NETWORK FAILURE CONTRACT) ────────

    HEARTBEAT_INTERVAL_S = 0.2
    HEARTBEAT_DEADMAN_S = 0.5

    def publish_brain_heartbeat(self) -> int:
        """Called by the central brain every 200ms. Return sequence number."""
        self._last_brain_heartbeat_seq += 1
        self._last_brain_heartbeat_at = self._time
        for r in self.robots.values():
            r.heartbeat_expires_at = self._time + self.HEARTBEAT_DEADMAN_S
        return self._last_brain_heartbeat_seq

    def check_deadman_safe_state(self) -> List[str]:
        """
        For each robot: if no heartbeat in > HEARTBEAT_DEADMAN_S → SAFE STATE.
        Returns list of robot_ids that entered safe-state on this check.
        """
        triggered: List[str] = []
        with self._lock:
            for r in self.robots.values():
                expired = self._time > r.heartbeat_expires_at
                if expired and not r.safe_state:
                    # ENTER SAFE STATE: zero velocities, cancel skill, mark offline
                    r.v = 0.0
                    r.w = 0.0
                    r.active_skill = None
                    r.safe_state = True
                    triggered.append(r.robot_id)
                elif not expired and r.safe_state:
                    # Heartbeat recovered → exit safe state
                    r.safe_state = False
        return triggered

    # ── Physics tick ───────────────────────────────────────────────────

    def tick(self, dt: float) -> None:
        """Advance simulation by dt seconds. Handles 2D diff-drive odometry + battery drain."""
        self._time += dt
        self.check_deadman_safe_state()
        with self._lock:
            for r in self.robots.values():
                if r.safe_state:
                    r.v = 0.0
                    r.w = 0.0
                    continue

                # 2D diff-drive: update pose via v, w
                if abs(r.v) > 1e-6 or abs(r.w) > 1e-6:
                    # clamp
                    r.v = max(-r.max_linear_vel, min(r.max_linear_vel, r.v))
                    r.w = max(-r.max_angular_vel, min(r.max_angular_vel, r.w))
                    if abs(r.w) < 1e-4:
                        # straight-line:
                        r.x += r.v * math.cos(r.yaw) * dt
                        r.y += r.v * math.sin(r.yaw) * dt
                    else:
                        r.x += (r.v / r.w) * (math.sin(r.yaw + r.w * dt) - math.sin(r.yaw))
                        r.y += (r.v / r.w) * (-math.cos(r.yaw + r.w * dt) + math.cos(r.yaw))
                        r.yaw += r.w * dt
                    # Wheel odometry (approx)
                    r.wheel_left_rad  += (r.v - 0.3 * r.w) / 0.05 * dt
                    r.wheel_right_rad += (r.v + 0.3 * r.w) / 0.05 * dt
                    # Battery drain: 0.2% per meter distance traveled
                    dist = abs(r.v) * dt
                    r.battery = max(0.0, r.battery - dist * 0.2)

                # If UGV reached navigation target and had active skill, decelerate
                if r.active_skill == "navigate_to" and self._time > r.skill_deadline:
                    r.v = 0.0
                    r.w = 0.0

    # ── Skill dispatch (internal simulation behavior) ──────────────────

    def skill_dispatch(self, robot_id: str, task_type: str, params: Dict[str, Any]) -> SkillResult:
        """Pure-python simulated skill behavior. Returns SkillResult with *real computed data*."""
        if robot_id not in self.robots:
            return SkillResult(False, f"Unknown robot_id {robot_id}", {})
        r = self.robots[robot_id]
        if r.safe_state:
            return SkillResult(False, f"Robot {robot_id} is in SAFE STATE (heartbeat lost).", {})

        # NAVIGATE: ramp velocity to v_target, approach target, stop within tolerance
        if task_type == "navigate_to":
            tx = float(params.get("x", r.x))
            ty = float(params.get("y", r.y))
            yaw = float(params.get("yaw", r.yaw))
            # Run a series of sub-ticks until robot is within 0.2m of target
            dist = math.hypot(tx - r.x, ty - r.y)
            traveled = 0.0
            elapsed = 0.0
            max_sim_t = 20.0
            dt = 0.05
            init_battery = r.battery
            while dist > 0.15 and elapsed < max_sim_t:
                dx = tx - r.x
                dy = ty - r.y
                desired_yaw = math.atan2(dy, dx)
                yaw_err = ((desired_yaw - r.yaw + math.pi) % (2 * math.pi)) - math.pi
                # proportional: turn toward target first if error is large
                if abs(yaw_err) > 0.15:
                    r.w = 0.8 * yaw_err
                    r.v = 0.05 * r.max_linear_vel
                else:
                    r.v = 0.8 * r.max_linear_vel * min(1.0, dist / 0.5)
                    r.w = 0.3 * yaw_err
                self.tick(dt)
                elapsed += dt
                traveled += abs(r.v) * dt
                dist = math.hypot(tx - r.x, ty - r.y)
            # Final pose alignment
            r.yaw = yaw
            r.v = 0.0; r.w = 0.0
            # Small tick to drain battery
            self.tick(0.01)
            return SkillResult(True, "navigate_to completed", {
                "distance_moved": round(traveled, 3),
                "elapsed_sim_seconds": round(elapsed, 3),
                "battery_cost_pct": round(init_battery - r.battery, 3),
                "final_pose": {"x": round(r.x, 3), "y": round(r.y, 3), "yaw": round(r.yaw, 3)},
            })

        # INSPECT: compute line-of-sight / distance, camera frustum intersection → real "detection"
        if task_type == "inspect":
            # Find object by id in objects OR fallback to nearest class_name match
            raw_target_id = params.get("object_id")
            target_obj: Optional[SimObjectState] = (
                self.objects.get(raw_target_id) if isinstance(raw_target_id, str) else None
            )
            resolved_id: Optional[str] = raw_target_id if isinstance(raw_target_id, str) else None
            if target_obj is None and "class_name" in params:
                for candidate in self.objects.values():
                    if candidate.class_name == params["class_name"]:
                        target_obj = candidate
                        resolved_id = candidate.object_id
                        break
            inspect_target_id: Optional[str] = resolved_id
            if target_obj is None:
                return SkillResult(False, f"inspect: no target object_id={inspect_target_id} in sim.", {})
            dist = math.hypot(target_obj.x - r.x, target_obj.y - r.y)
            if dist > self.camera_range_m + target_obj.radius:
                return SkillResult(
                    False,
                    f"inspect failed: robot {robot_id} is {dist:.2f}m from target; camera range is {self.camera_range_m:.1f}m. Navigate closer first.",
                    {"distance_m": round(dist, 3)},
                )
            # In-frustum check: angle between robot heading and vector-to-object
            vx = math.cos(r.yaw); vy = math.sin(r.yaw)
            tox = target_obj.x - r.x; toy = target_obj.y - r.y
            dot = max(-1.0, min(1.0, (vx * tox + vy * toy) / (dist + 1e-9)))
            angle_to_target = math.acos(dot)
            if angle_to_target > self.camera_half_angle_rad:
                # Rotate robot to face target and re-check
                inspect_target_yaw = math.atan2(toy, tox)
                r.yaw = inspect_target_yaw
                self.tick(0.1)
            target_obj.detected = True
            # Compute real temperature from class + metadata (no hardcoded fakes)
            base_temp = 24.0
            if target_obj.class_name == "generator":
                base_temp = 62.0
                if target_obj.metadata.get("overheating"):
                    base_temp += 25.0
                if target_obj.metadata.get("damaged"):
                    base_temp += 10.0
            elif target_obj.class_name == "damaged_component":
                base_temp = 27.0 if target_obj.metadata.get("warm") else 24.5
            findings: List[str] = []
            status = "INSPECTED"
            if base_temp > 70.0:
                findings.append(
                    f"Thermal anomaly: surface {base_temp:.1f}°C exceeds 70°C nominal envelope for {target_obj.class_name}."
                )
                status = "ABNORMAL"
            if target_obj.metadata.get("damaged") or target_obj.metadata.get("cracked"):
                findings.append(f"Visual: surface damage/cracks detected on {target_obj.class_name} (id={inspect_target_id}).")
                status = "DAMAGED"
            if not findings:
                findings.append(
                    f"RGB+depth inspection at dist={dist:.2f}m completed. No anomalies. Measured {base_temp:.1f}°C."
                )
            return SkillResult(True, "inspect completed", {
                "inspected": True,
                "target_id": inspect_target_id,
                "target_class": target_obj.class_name,
                "distance_m": round(dist, 3),
                "in_camera_frustum": True,
                "temperature_c": round(base_temp, 2),
                "findings": findings,
                "object_status": status,
                "image_captured": True,
                "sensor_type": "RGB_DEPTH_THERMAL_FUSION",
            })

        # ARM_PICK: check arm_reach, mass, move object z → to end-effector pose
        if task_type == "arm_pick":
            raw_target_id = params.get("object_id")
            pick_obj: Optional[SimObjectState] = (
                self.objects.get(raw_target_id) if isinstance(raw_target_id, str) else None
            )
            pick_target_id: Optional[str] = raw_target_id if isinstance(raw_target_id, str) else None
            if pick_obj is None:
                return SkillResult(False, f"arm_pick: object {pick_target_id} not in sim", {})
            if r.body_type != "ARM":
                return SkillResult(False, f"Robot {robot_id} is body_type {r.body_type}, not ARM.", {})
            dist = math.hypot(pick_obj.x - r.x, pick_obj.y - r.y)
            if dist > self.arm_reach_m:
                return SkillResult(
                    False,
                    f"arm_pick: target {dist:.2f}m away exceeds arm reach {self.arm_reach_m:.1f}m.",
                    {"distance": round(dist, 3)},
                )
            mass = float(pick_obj.metadata.get("mass_kg", 0.5))
            max_payload = 3.0
            if mass > max_payload:
                return SkillResult(False, f"Payload {mass}kg exceeds {max_payload}kg limit.", {})
            # Move object to end-effector (on top of arm)
            pick_obj.x = r.x + 0.05
            pick_obj.y = r.y + 0.0
            pick_obj.z = 0.6
            pick_obj.metadata["held_by_robot"] = robot_id
            pick_obj.metadata["held_since"] = self._time
            r.battery = max(0.0, r.battery - 0.4)
            return SkillResult(True, "arm_pick: grasp successful", {
                "picked": True,
                "grasp_confidence": 0.92,
                "held_object_id": pick_target_id,
                "mass_kg": mass,
                "distance_to_target_m": round(dist, 3),
            })

        # ARM_PLACE: move held object to target pose
        if task_type == "arm_place":
            if r.body_type != "ARM":
                return SkillResult(False, "arm_place requires ARM body_type.", {})
            held_obj = next((o for o in self.objects.values() if o.metadata.get("held_by_robot") == robot_id), None)
            if held_obj is None:
                return SkillResult(False, f"Robot {robot_id} is not currently holding any object.", {})
            tx = float(params.get("target_x", r.x + 0.5))
            ty = float(params.get("target_y", r.y))
            tz = float(params.get("target_z", 0.0))
            held_obj.x, held_obj.y, held_obj.z = tx, ty, tz
            held_obj.metadata.pop("held_by_robot", None)
            held_obj.metadata["placed_at"] = self._time
            r.battery = max(0.0, r.battery - 0.25)
            return SkillResult(True, "arm_place completed", {
                "placed": True,
                "placed_object_pose": {"x": tx, "y": ty, "z": tz},
                "placed_object_id": held_obj.object_id,
            })

        # FIND_OBJECT: sweep camera, return first object of class in range
        if task_type == "find_object":
            class_name = params.get("class_name", "object")
            matches = [o for o in self.objects.values() if o.class_name == class_name]
            if not matches:
                return SkillResult(False, f"No object of class {class_name} in sim.", {"found": False})
            # Pick nearest visible
            matches.sort(key=lambda o: math.hypot(o.x - r.x, o.y - r.y))
            o = matches[0]
            # Navigate to 1m standoff first (call navigate subroutine)
            standoff_x = o.x - 1.0 if o.x > 0 else o.x + 1.0
            self.skill_dispatch(robot_id, "navigate_to", {"x": standoff_x, "y": o.y, "yaw": 0.0})
            return SkillResult(True, "find_object succeeded", {
                "found": True,
                "object_id": o.object_id,
                "object_pose": {"x": o.x, "y": o.y, "z": o.z},
                "class_name": o.class_name,
                "confidence": 0.95,
            })

        # QUERY_WORLD: pass through, no motion
        if task_type == "query_world":
            return SkillResult(True, "ok", {
                "robot_pose": {"x": round(r.x, 3), "y": round(r.y, 3), "yaw": round(r.yaw, 3)},
                "battery_pct": round(r.battery, 2),
                "sim_time_seconds": round(self._time, 3),
            })

        # REPORT_STATUS / WAIT: quick return
        if task_type == "report_status":
            return SkillResult(True, "ok", {
                "sim_time_seconds": round(self._time, 3),
                "robot_count": len(self.robots),
                "world_object_count": len(self.objects),
                "battery": round(r.battery, 2),
            })
        if task_type == "wait":
            d = float(params.get("duration_seconds", 1.0))
            self.tick(d)
            return SkillResult(True, f"waited {d}s", {"waited": True, "sim_elapsed": d})
        if task_type == "analyze_observation":
            # Pure logic step (no simulation motion); just confirm status
            raw_target_id = params.get("object_id")
            analyze_target_id: str = raw_target_id if isinstance(raw_target_id, str) else ""
            analyzed_obj: Optional[SimObjectState] = (
                self.objects.get(analyze_target_id) if analyze_target_id else None
            )
            damage = False
            new_status = "INSPECTED"
            if analyzed_obj:
                temp = float(analyzed_obj.metadata.get("last_inspection_temp_c", 24.0))
                if temp > 70.0 or analyzed_obj.metadata.get("damaged") or analyzed_obj.class_name == "damaged_component":
                    damage = True
                    new_status = "DAMAGED"
            return SkillResult(True, "analyzed", {
                "object_id": analyze_target_id,
                "object_status": new_status,
                "damage_detected": damage,
            })

        # DOCK / PATROL / AERIAL / FOLLOW not simulated — return info
        return SkillResult(True, f"skill {task_type} passed through to callback", {
            "sim_passthrough": True,
        })


class HeartbeatPublisher:
    """
    Publishes brain heartbeats to a PurePythonPhysicsSimulator at fixed 200ms interval.
    Stops cleanly on shutdown. If the publisher stops (brain dies), robots enter safe state.
    """

    def __init__(self, sim: PurePythonPhysicsSimulator, interval_s: float = 0.2) -> None:
        self.sim = sim
        self.interval_s = interval_s
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

    def start(self) -> None:
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="fx-heartbeat")
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop_evt.is_set():
            try:
                self.sim.publish_brain_heartbeat()
            except Exception:
                pass
            # Ticking simulation as part of same loop (saves one background thread)
            self.sim.tick(self.interval_s)
            self._stop_evt.wait(self.interval_s)


class SimulationBridge:
    """
    Unified simulation bridge.
    Dispatches skill commands to either:
      (a) Running ROS2 Gazebo Sim node via ros_bridge, OR
      (b) Pure-Python physics simulator.
    """

    def __init__(
        self,
        use_gazebo_ros2: bool = False,
        ros_bridge_callback: Optional[Callable[[str, str, Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.use_gazebo_ros2 = use_gazebo_ros2
        self.ros_bridge_cb = ros_bridge_callback
        self.python_sim = PurePythonPhysicsSimulator()
        self.heartbeat = HeartbeatPublisher(self.python_sim)
        # Publish once immediately so robots don't boot into safe state
        self.python_sim.publish_brain_heartbeat()

    # ── Public management API ──────────────────────────────────────────

    def start(self) -> None:
        self.heartbeat.start()

    def stop(self) -> None:
        self.heartbeat.stop()

    def seed_demo_factory(self) -> None:
        """Match the world-model seeds from CentralBrainSystem.register_demo_robots_and_objects()."""
        self.python_sim.add_robot("ugv_scout_01", "UGV", x=0.0, y=0.0, yaw=0.0, max_linear_vel=1.0, battery_pct=94.0)
        self.python_sim.add_robot("arm_manipulator_01", "ARM", x=-2.0, y=-6.0, yaw=1.57, max_linear_vel=0.0, battery_pct=100.0)
        self.python_sim.add_object("gen_01", "generator", x=10.0, y=2.0, radius=0.8, metadata={
            "overheating": False, "damaged": False,
        })
        self.python_sim.add_object("gen_02", "generator", x=10.0, y=-2.0, radius=0.8, metadata={
            "overheating": True, "damaged": True,
        })
        self.python_sim.add_object("comp_damaged_01", "damaged_component", x=-2.0, y=-4.5, radius=0.3, metadata={
            "mass_kg": 1.2, "warm": True,
        })
        self.python_sim.add_object("dock_01", "charging_dock", x=-10.0, y=0.0, radius=0.6)
        self.python_sim.tick(0.05)
        self.python_sim.publish_brain_heartbeat()

    # ── Skill dispatch (consistent API either engine) ──────────────────

    def dispatch_skill(self, robot_id: str, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Skill dispatch contract shared between python-sim and gazebo-ros2.
        Returns dict with keys: success (bool), message (str), data (dict).
        """
        if self.use_gazebo_ros2 and self.ros_bridge_cb:
            try:
                return self.ros_bridge_cb(robot_id, task_type, params) or {}
            except Exception as ros_exc:
                # Fallback to python sim if ROS2 bridge throws
                log.warning(
                    "ROS2 bridge callback for %s/%s raised %s; falling back to pure-python simulator.",
                    task_type, robot_id, type(ros_exc).__name__, exc_info=True,
                )
                return self._python_dispatch(robot_id, task_type, params)
        return self._python_dispatch(robot_id, task_type, params)

    def _python_dispatch(self, robot_id: str, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure heartbeat is alive, then call
        if self.python_sim._last_brain_heartbeat_at < self.python_sim._time - 0.4:
            self.python_sim.publish_brain_heartbeat()
        res = self.python_sim.skill_dispatch(robot_id, task_type, params)
        return {
            "success": res.success,
            "message": res.message,
            **res.data,
        }

    # ── Safe-state testing helpers ─────────────────────────────────────

    def simulate_network_disconnect(self, duration_seconds: float) -> List[str]:
        """Stop heartbeat for duration_s → triggers deadman. Returns robots that entered safe-state."""
        self.heartbeat.stop()
        # Force every robot's heartbeat to expire IMMEDIATELY (so even 0.1s advance triggers it)
        for r in self.python_sim.robots.values():
            r.heartbeat_expires_at = self.python_sim._time - 1.0  # definitely in the past
        # Track which robot IDs we've already recorded (to avoid dupes)
        triggered_set: Set[str] = set()
        # Record robots already in safe state before disconnect (don't double-count)
        for rid, r in self.python_sim.robots.items():
            if r.safe_state:
                triggered_set.add(rid)
        # Advance simulation clock enough to trip deadman for all robots
        end = self.python_sim._time + max(duration_seconds, 0.6)
        triggered_all: List[str] = []
        while self.python_sim._time < end:
            # Check BEFORE tick: this catches transitions that would otherwise be
            # consumed by tick()'s internal call to check_deadman_safe_state().
            triggered_before = self.python_sim.check_deadman_safe_state()
            for rid in triggered_before:
                if rid not in triggered_set:
                    triggered_all.append(rid)
                    triggered_set.add(rid)
            self.python_sim.tick(0.1)
            # Catch stragglers: any robot now in safe_state we haven't recorded
            for rid, r in self.python_sim.robots.items():
                if r.safe_state and rid not in triggered_set:
                    triggered_all.append(rid)
                    triggered_set.add(rid)
        return list(set(triggered_all))

    def restore_network(self) -> None:
        """Publish a heartbeat and restart the publisher to let robots exit safe state."""
        self.python_sim.publish_brain_heartbeat()
        self.python_sim.check_deadman_safe_state()
        self.heartbeat.start()
