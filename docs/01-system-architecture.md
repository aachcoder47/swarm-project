# FrontierX Multi-Body Robotics Platform - System Architecture

> Document: 01 - System Architecture
> Version: 0.2.0
> Platform: Centralized AI brain with heterogeneous robot bodies

---

## 1. Overview

FrontierX is a deep-tech robotics platform built around one centralized AI brain and multiple physical or simulated robot bodies connected over ROS 2/DDS and IP networking. The brain runs on a powerful workstation, server, or edge cluster. Each body keeps deterministic real-time control, local safety, watchdogs, emergency stop behavior, and hardware-specific drivers onboard.

The system treats every robot as a capability-bearing body, not as a hard-coded extension of one robot type. A wheeled UGV, tracked rover, arm, quadruped, drone, or future custom robot can join the fleet by registering its body type, live state, available skills, sensor streams, and safety envelope.

The AI operates only at the command, task, and skill level. It may request verified skills such as navigation, inspection, docking, manipulation, search, and reporting. It must never directly command motors, PWM, torque, velocity controllers, or actuator loops.

---

## 2. Primary Architecture

```text
                    USER
                     |
              Text / Voice API
                     |
                     v
              COMMAND INTERFACE
                     |
                     v
             AI COMMAND PARSER
                     |
                     v
              TASK PLANNER
                     |
        +------------+-------------+
        |                          |
        v                          v
   WORLD MODEL               ROBOT REGISTRY
        |                          |
        |                    CAPABILITY MATCH
        |                          |
        +------------+-------------+
                     |
                     v
              TASK EXECUTOR
                     |
                     v
             SAFETY SUPERVISOR
                     |
                     v
             SKILL EXECUTION
                     |
                     v
                  ROS 2 / DDS
                     |
        +------------+-------------+
        |            |             |
        v            v             v
     BODY 01      BODY 02       BODY 03
      UGV          ARM        QUADRUPED
        |            |             |
     Sensors      Sensors       Sensors
        |            |             |
        +------------+-------------+
                     |
                     v
              SENSOR EVENTS
                     |
                     v
               PERCEPTION
                     |
                     v
               WORLD MODEL
                     |
                     +----> TASK PLANNER
```

---

## 3. Core Components

| # | Component | Responsibility |
|---|-----------|----------------|
| 1 | AI Command Interface | Accept text, voice, API, and dashboard commands. |
| 2 | AI Reasoning / Task Planner | Convert intent into structured, validated task plans. |
| 3 | Robot Registry | Track robot bodies, status, leases, battery, pose, and connection state. |
| 4 | Capability Registry | Match task requirements to body capabilities. |
| 5 | Skill Execution Engine | Execute verified skills step by step or in coordinated groups. |
| 6 | World Model | Maintain objects, locations, semantic state, and observations. |
| 7 | Task Memory | Store task history, observations, failures, and reports. |
| 8 | Robot State Monitor | Consume heartbeats and telemetry; detect stale or unsafe bodies. |
| 9 | Multi-Robot Orchestrator | Allocate bodies, manage leases, prevent conflicting commands. |
| 10 | Safety / Policy Supervisor | Enforce action whitelists, geofences, battery limits, and AI isolation. |
| 11 | ROS 2 Bridge | Convert approved skill calls into ROS 2 actions/services/topics. |
| 12 | Sensor Data Pipeline | Normalize sensor events from each body. |
| 13 | Perception Interface | Run or call perception models and publish semantic observations. |
| 14 | Simulation Interface | Connect Isaac Sim, Gazebo when useful, and mock bodies to the same brain APIs. |
| 15 | Teleoperation Fallback | Provide operator control without bypassing local safety. |
| 16 | Logging / Observability | Emit structured logs, metrics, traces, and audit records. |
| 17 | Web Dashboard | Show fleet state, tasks, world model, logs, and live telemetry. |
| 18 | API Gateway | Expose FastAPI and WebSocket interfaces for external clients. |

---

## 4. Control Boundaries

### Central Brain Responsibilities

- Understand natural-language commands.
- Build task plans with skill-level actions.
- Select capable bodies using live registry data.
- Request verified navigation, inspection, manipulation, scan, docking, and reporting skills.
- Monitor execution feedback and sensor events.
- Update the world model and task memory.
- Re-plan when a body fails, a path is blocked, or new observations change the task.

### Robot Body Responsibilities

- Motor control and actuator loops.
- Encoder, IMU, and hardware timing.
- Local obstacle avoidance and collision prevention.
- Emergency stop and watchdog enforcement.
- Battery safety and thermal limits.
- Hardware drivers and controller-specific safety limits.

### Hard Rule

The LLM/VLM layer never writes directly to actuator topics or parameters. Forbidden AI outputs include `cmd_vel`, PWM, torque, voltage, motor IDs, raw joint commands, and direct velocity-controller requests. The safety supervisor rejects any task step that attempts to cross this boundary.

---

## 5. Example Execution Flow

User command:

```text
Go to the generator, inspect it, identify anything abnormal, and return.
```

System behavior:

1. Command Interface receives the command.
2. Task Planner resolves intent, known objects, and required skills.
3. World Model locates the generator or asks for search if uncertain.
4. Capability Registry selects a body with ground navigation and inspection sensors.
5. Skill Execution Engine requests `navigate_to(generator)`.
6. Safety Supervisor checks action type, robot state, battery, and geofence.
7. ROS 2 Bridge dispatches the approved Nav2 action.
8. Robot body handles controllers, local avoidance, watchdogs, and e-stop.
9. Sensor Pipeline and Perception Interface analyze RGB/LiDAR/thermal feedback.
10. World Model and Task Memory store observations and findings.
11. Planner re-plans if anomalies, blocked routes, or faults appear.
12. Executor requests return/dock and generates a report.

---

## 6. Technology Stack

| Layer | Technology |
|-------|------------|
| Core language | Python 3.11+ |
| Robotics middleware | ROS 2 Humble or Jazzy, using DDS for robot communication |
| Simulation | NVIDIA Isaac Sim as primary simulator; Gazebo Sim for lightweight validation where supported |
| Navigation | Nav2 |
| Manipulation | MoveIt 2 when arm bodies are added |
| AI abstraction | Provider-neutral LLM/VLM interface supporting OpenAI-compatible APIs, local models, and future VLA models |
| Backend APIs | FastAPI |
| Schemas | Pydantic |
| Persistent data | PostgreSQL |
| Transient state/events | Redis where useful |
| Live updates | WebSocket |
| Deployment | Docker |
| Testing | pytest |
| Observability | OpenTelemetry-compatible structured logging where practical |

The architecture must not tightly couple the central brain to one AI provider. Model backends are replaceable behind the LLM/VLM abstraction.

---

## 7. ROS 2 Package Map

| Package | Role |
|---------|------|
| `frontierx_brain` | Central AI command interface, planner, registries, orchestrator, memory, policy, API, ROS bridge, and simulation adapters. |
| `frontierx_interfaces` | Shared ROS 2 messages, services, and actions. |
| `frontierx_robot_description` | Body descriptions, URDF/Xacro, meshes, and RViz assets. |
| `frontierx_bringup` | Launch files for central brain and robot-side stacks. |
| `frontierx_sim` | Isaac Sim and Gazebo simulation integration. |
| `frontierx_control` | Robot-side control, local safety, watchdogs, and hardware interfaces. |
| `frontierx_localization` | EKF, odometry, AMCL, and pose estimation. |
| `frontierx_mapping` | SLAM Toolbox and map lifecycle. |
| `frontierx_navigation` | Nav2 configuration and navigation behaviors. |
| `frontierx_perception` | Camera, LiDAR, detection, tracking, and semantic perception. |
| `frontierx_tasks` | Verified skill/action servers available to the central brain. |
| `frontierx_diagnostics` | Health monitoring, safety telemetry, and diagnostics. |
| `frontierx_data` | Task logs, benchmark data, and recordings. |
| `frontierx_visualization` | RViz, Foxglove, and dashboard-facing visualization assets. |

---

## 8. Data Flows

### Command to Skill

```text
/user command
  -> command parser
  -> task planner
  -> policy-supervised task plan
  -> capability match
  -> robot lease
  -> skill execution
  -> ROS 2 action/service call
  -> body-local controller
```

### Sensor Feedback to Re-Planning

```text
body sensors
  -> ROS 2 topics
  -> sensor data pipeline
  -> perception interface
  -> semantic observations
  -> world model
  -> task memory
  -> planner re-evaluation
```

### Multi-Robot Coordination

```text
registry heartbeat
  -> state monitor
  -> capability registry
  -> orchestrator lease table
  -> executor dispatch decision
  -> policy supervisor
```

---

## 9. Safety and Policy Invariants

- The central brain only emits skill-level requests.
- Every task step is checked against an action whitelist.
- Every body has a local emergency stop and watchdog independent of the AI brain.
- Robot leases prevent two tasks from controlling the same body at the same time.
- Low battery, stale heartbeat, local e-stop, and geofence violations block execution.
- Teleoperation fallback remains subject to local robot safety limits.
- Direct low-level actuator commands from the AI are treated as policy violations.

---

## 10. Quality Targets

| Attribute | Target |
|-----------|--------|
| Local e-stop response | Less than 50 ms at the robot body |
| Brain-to-skill command validation | Less than 200 ms excluding LLM inference |
| Robot heartbeat timeout | Configurable, default 10 s |
| Navigation control loop | Body-local, typically 20 Hz or higher |
| Localization frequency | 30-100 Hz depending on body and sensors |
| Perception frequency | 10-30 Hz depending on model and hardware |
| LLM planning response | Less than 5 s for normal commands where practical |
| Dashboard telemetry | WebSocket live updates |

---

## Related Documents

- [02 - Robot Description](02-robot-description.md)
- [03 - ROS 2 Architecture](03-ros2-architecture.md)
- [04 - Simulation](04-simulation.md)
- [09 - AI Agent](09-ai-agent.md)
- [10 - Safety](10-safety.md)
