"""
Core Canonical Schemas — Single Source of Truth
================================================
All capability IDs, skill/task types, robot body types, and shared Pydantic
models live here. Every module imports from this file instead of defining
its own strings. Eliminates drift between LLM prompt, safety whitelist,
and capability matchmaker.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# CAPABILITY IDS  (canonical string constants — never duplicated elsewhere)
# ──────────────────────────────────────────────────────────────────────

class Capability(str, Enum):
    NAVIGATE_GROUND      = "navigate_ground"
    NAVIGATE_AERIAL      = "navigate_aerial"
    MANIPULATE_ARM       = "manipulate_arm"
    THERMAL_INSPECTION   = "thermal_inspection"
    VISUAL_INSPECTION    = "visual_inspection"
    LIDAR_3D             = "lidar_3d"
    HEAVY_PAYLOAD        = "heavy_payload"
    STAIR_CLIMB          = "stair_climb"
    OBJECT_SEARCH        = "object_search"
    DOCKING              = "docking"
    CAPTURE_RGB          = "capture_rgb"
    CAPTURE_DEPTH        = "capture_depth"
    GRASP                = "grasp"


CAPABILITY_DESCRIPTIONS: Dict[Capability, str] = {
    Capability.NAVIGATE_GROUND:    "Ground-based locomotion on flat terrain.",
    Capability.NAVIGATE_AERIAL:    "Aerial flight (multirotor or fixed-wing).",
    Capability.MANIPULATE_ARM:     "Robotic arm with at least 5-DoF manipulation.",
    Capability.THERMAL_INSPECTION: "Thermal/IR camera for heat-based inspection.",
    Capability.VISUAL_INSPECTION:  "RGB camera for visual inspection tasks.",
    Capability.LIDAR_3D:           "3D LiDAR or depth sensor for point-cloud mapping.",
    Capability.HEAVY_PAYLOAD:      "Can carry payload over 10 kg.",
    Capability.STAIR_CLIMB:        "Able to climb stairs (tracked or legged).",
    Capability.OBJECT_SEARCH:      "Can actively search for a named object in space.",
    Capability.DOCKING:            "Can autonomously dock to charging station.",
    Capability.CAPTURE_RGB:        "Has active RGB camera stream.",
    Capability.CAPTURE_DEPTH:      "Has active depth camera stream.",
    Capability.GRASP:              "Gripper or end-effector capable of grasping objects.",
}


# ──────────────────────────────────────────────────────────────────────
# TASK / SKILL TYPES  (single whitelist — planning prompt, safety, SkillRegistry)
# ──────────────────────────────────────────────────────────────────────

class SkillType(str, Enum):
    NAVIGATE_TO     = "navigate_to"
    FIND_OBJECT     = "find_object"
    FOLLOW_PERSON   = "follow_person"
    PATROL          = "patrol"
    DOCK            = "dock"
    INSPECT         = "inspect"
    REPORT_STATUS   = "report_status"
    QUERY_WORLD     = "query_world"
    WAIT            = "wait"
    ARM_PICK        = "arm_pick"
    ARM_PLACE       = "arm_place"
    AERIAL_SCAN     = "aerial_scan"
    ANALYZE_OBSERVATION = "analyze_observation"


SKILL_REQUIRED_CAPABILITIES: Dict[SkillType, List[Capability]] = {
    SkillType.NAVIGATE_TO:        [Capability.NAVIGATE_GROUND],
    SkillType.FIND_OBJECT:        [Capability.OBJECT_SEARCH, Capability.CAPTURE_RGB],
    SkillType.FOLLOW_PERSON:      [Capability.NAVIGATE_GROUND, Capability.CAPTURE_RGB, Capability.OBJECT_SEARCH],
    SkillType.PATROL:             [Capability.NAVIGATE_GROUND],
    SkillType.DOCK:               [Capability.DOCKING],
    SkillType.INSPECT:            [Capability.CAPTURE_RGB, Capability.VISUAL_INSPECTION],
    SkillType.REPORT_STATUS:      [],
    SkillType.QUERY_WORLD:        [],
    SkillType.WAIT:               [],
    SkillType.ARM_PICK:           [Capability.MANIPULATE_ARM, Capability.GRASP],
    SkillType.ARM_PLACE:          [Capability.MANIPULATE_ARM],
    SkillType.AERIAL_SCAN:        [Capability.NAVIGATE_AERIAL, Capability.CAPTURE_RGB, Capability.LIDAR_3D],
    SkillType.ANALYZE_OBSERVATION: [Capability.CAPTURE_RGB],
}


ALLOWED_ACTION_WHITELIST: set = {s.value for s in SkillType}


# ──────────────────────────────────────────────────────────────────────
# ROBOT BODY TYPES
# ──────────────────────────────────────────────────────────────────────

class RobotBodyType(str, Enum):
    UGV       = "UGV"
    TRACKED   = "TRACKED"
    ARM       = "ARM"
    QUADRUPED = "QUADRUPED"
    DRONE     = "DRONE"
    CUSTOM    = "CUSTOM"


COMPATIBLE_BODY_TYPES_PER_SKILL: Dict[SkillType, List[RobotBodyType]] = {
    SkillType.NAVIGATE_TO:   [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED],
    SkillType.FIND_OBJECT:   [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED, RobotBodyType.DRONE],
    SkillType.FOLLOW_PERSON: [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED],
    SkillType.PATROL:        [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.DRONE, RobotBodyType.QUADRUPED],
    SkillType.DOCK:          [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED],
    SkillType.INSPECT:       [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED, RobotBodyType.DRONE, RobotBodyType.ARM],
    SkillType.REPORT_STATUS: list(RobotBodyType),
    SkillType.QUERY_WORLD:   list(RobotBodyType),
    SkillType.WAIT:          list(RobotBodyType),
    SkillType.ARM_PICK:      [RobotBodyType.ARM],
    SkillType.ARM_PLACE:     [RobotBodyType.ARM],
    SkillType.AERIAL_SCAN:   [RobotBodyType.DRONE],
    SkillType.ANALYZE_OBSERVATION: [RobotBodyType.UGV, RobotBodyType.TRACKED, RobotBodyType.QUADRUPED, RobotBodyType.DRONE, RobotBodyType.ARM],
}


# ──────────────────────────────────────────────────────────────────────
# ROBOT STATUS
# ──────────────────────────────────────────────────────────────────────

class RobotStatus(str, Enum):
    IDLE       = "IDLE"
    BUSY       = "BUSY"
    CHARGING   = "CHARGING"
    FAULT      = "FAULT"
    E_STOPPED  = "E_STOPPED"
    OFFLINE    = "OFFLINE"


# ──────────────────────────────────────────────────────────────────────
# TASK STATUS
# ──────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"
    REPLANNING  = "REPLANNING"
    CANCELLED   = "CANCELLED"


# ──────────────────────────────────────────────────────────────────────
# POSE
# ──────────────────────────────────────────────────────────────────────

class Pose(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float  = 0.0
    pitch: float = 0.0
    yaw: float   = 0.0
    frame_id: str = "map"


# ──────────────────────────────────────────────────────────────────────
# SKILL DEFINITION  (canonical contract for each skill)
# ──────────────────────────────────────────────────────────────────────

class SkillDefinition(BaseModel):
    skill_id: SkillType
    description: str
    required_capabilities: List[Capability] = Field(default_factory=list)
    input_params_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    compatible_body_types: List[RobotBodyType] = Field(default_factory=list)
    default_timeout_seconds: float = 60.0
    max_retries: int = 1
    safety_constraints: List[str] = Field(default_factory=list)
    cancellation_behavior: str = "STOP_AND_RELEASE"
    requires_perception: bool = False


CANONICAL_SKILL_DEFINITIONS: List[SkillDefinition] = [
    SkillDefinition(
        skill_id=SkillType.NAVIGATE_TO,
        description="Navigate the robot to a target (x,y) location on the map.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.NAVIGATE_TO],
        input_params_schema={
            "x":        {"type": "float", "description": "Target X coordinate in map frame (m)."},
            "y":        {"type": "float", "description": "Target Y coordinate in map frame (m)."},
            "yaw":      {"type": "float", "description": "Optional target heading (rad).", "optional": True},
        },
        output_schema={
            "success": {"type": "bool"},
            "final_pose": {"type": "Pose"},
            "distance_moved": {"type": "float"},
        },
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.NAVIGATE_TO],
        default_timeout_seconds=120.0,
        max_retries=2,
        safety_constraints=[
            "geofence_enforced",
            "max_linear_velocity_enforced",
            "local_obstacle_avoidance_body_side",
        ],
        requires_perception=False,
    ),
    SkillDefinition(
        skill_id=SkillType.FIND_OBJECT,
        description="Search for a named object in the world model or by exploring.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.FIND_OBJECT],
        input_params_schema={
            "class_name": {"type": "str", "description": "Object class to search for (e.g. 'generator')."},
            "object_id":  {"type": "str", "description": "Optional specific known object ID.", "optional": True},
        },
        output_schema={
            "found": {"type": "bool"},
            "object_id": {"type": "str"},
            "object_pose": {"type": "Pose"},
            "confidence": {"type": "float"},
        },
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.FIND_OBJECT],
        default_timeout_seconds=180.0,
        max_retries=1,
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.INSPECT,
        description="Inspect a target object using available sensors and report findings.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.INSPECT],
        input_params_schema={
            "object_id":    {"type": "str", "description": "Object ID in world model to inspect."},
            "inspection_mode": {"type": "str", "description": "VISUAL or THERMAL", "default": "VISUAL"},
        },
        output_schema={
            "inspected": {"type": "bool"},
            "temperature_c": {"type": "float"},
            "object_status": {"type": "str"},
            "findings": {"type": "List[str]"},
            "image_captured": {"type": "bool"},
        },
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.INSPECT],
        default_timeout_seconds=90.0,
        max_retries=1,
        safety_constraints=[
            "minimum_standoff_distance_from_object",
        ],
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.REPORT_STATUS,
        description="Report current robot and world-model status.",
        required_capabilities=[],
        input_params_schema={},
        output_schema={"report": {"type": "dict"}},
        compatible_body_types=list(RobotBodyType),
        default_timeout_seconds=10.0,
        max_retries=0,
        requires_perception=False,
    ),
    SkillDefinition(
        skill_id=SkillType.QUERY_WORLD,
        description="Query the central world model by object class or criteria.",
        required_capabilities=[],
        input_params_schema={
            "class_name": {"type": "str", "optional": True},
            "object_id":  {"type": "str", "optional": True},
            "status":     {"type": "str", "optional": True},
        },
        output_schema={"matches": {"type": "List[WorldObject]"}},
        compatible_body_types=list(RobotBodyType),
        default_timeout_seconds=5.0,
        max_retries=0,
        requires_perception=False,
    ),
    SkillDefinition(
        skill_id=SkillType.ARM_PICK,
        description="Use a robotic arm to pick up a target object.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.ARM_PICK],
        input_params_schema={
            "object_id": {"type": "str", "description": "World-model object ID to pick up."},
        },
        output_schema={
            "picked": {"type": "bool"},
            "grasp_confidence": {"type": "float"},
            "held_object_id": {"type": "str"},
        },
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.ARM_PICK],
        default_timeout_seconds=60.0,
        max_retries=2,
        safety_constraints=[
            "workspace_envelope_enforced",
            "max_payload_check",
            "force_torque_safety_body_side",
        ],
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.ARM_PLACE,
        description="Place the currently held object at a target position.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.ARM_PLACE],
        input_params_schema={
            "target_x": {"type": "float"},
            "target_y": {"type": "float"},
            "target_z": {"type": "float"},
        },
        output_schema={"placed": {"type": "bool"}, "placed_object_pose": {"type": "Pose"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.ARM_PLACE],
        default_timeout_seconds=45.0,
        max_retries=1,
        requires_perception=False,
    ),
    SkillDefinition(
        skill_id=SkillType.WAIT,
        description="Pause execution for a fixed duration (seconds).",
        required_capabilities=[],
        input_params_schema={"duration_seconds": {"type": "float", "default": 1.0}},
        output_schema={"waited": {"type": "bool"}},
        compatible_body_types=list(RobotBodyType),
        default_timeout_seconds=30.0,
        max_retries=0,
        requires_perception=False,
    ),
    SkillDefinition(
        skill_id=SkillType.DOCK,
        description="Autonomously dock to a charging station.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.DOCK],
        input_params_schema={},
        output_schema={"docked": {"type": "bool"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.DOCK],
        default_timeout_seconds=120.0,
        max_retries=2,
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.PATROL,
        description="Visit a series of waypoints and report observations.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.PATROL],
        input_params_schema={
            "waypoints": {"type": "List[Tuple[float,float]]", "description": "List of (x,y) waypoints."},
        },
        output_schema={"patrol_completed": {"type": "bool"}, "observations": {"type": "list"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.PATROL],
        default_timeout_seconds=300.0,
        max_retries=0,
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.FOLLOW_PERSON,
        description="Follow a detected person maintaining a safe distance.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.FOLLOW_PERSON],
        input_params_schema={"person_id": {"type": "str", "optional": True}},
        output_schema={"following": {"type": "bool"}, "distance_to_person": {"type": "float"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.FOLLOW_PERSON],
        default_timeout_seconds=600.0,
        max_retries=0,
        safety_constraints=["minimum_person_standoff_0.5m"],
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.AERIAL_SCAN,
        description="UAV performs a 3D aerial scan of a rectangular region.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.AERIAL_SCAN],
        input_params_schema={
            "min_x": {"type": "float"}, "max_x": {"type": "float"},
            "min_y": {"type": "float"}, "max_y": {"type": "float"},
            "altitude": {"type": "float"},
        },
        output_schema={"scan_completed": {"type": "bool"}, "pointcloud_size_points": {"type": "int"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.AERIAL_SCAN],
        default_timeout_seconds=300.0,
        max_retries=1,
        requires_perception=True,
    ),
    SkillDefinition(
        skill_id=SkillType.ANALYZE_OBSERVATION,
        description="Analyze the latest sensor/inspection observation from a given robot and update world model object status.",
        required_capabilities=SKILL_REQUIRED_CAPABILITIES[SkillType.ANALYZE_OBSERVATION],
        input_params_schema={"object_id": {"type": "str"}, "inspection_data": {"type": "dict"}},
        output_schema={"object_status": {"type": "str"}, "damage_detected": {"type": "bool"}},
        compatible_body_types=COMPATIBLE_BODY_TYPES_PER_SKILL[SkillType.ANALYZE_OBSERVATION],
        default_timeout_seconds=30.0,
        max_retries=0,
        requires_perception=False,
    ),
]


def get_skill_definition(skill_id: SkillType) -> Optional[SkillDefinition]:
    for s in CANONICAL_SKILL_DEFINITIONS:
        if s.skill_id == skill_id:
            return s
    return None
