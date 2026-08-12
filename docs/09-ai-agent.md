# FrontierX Central AI Brain

> Document: 09 - AI Brain and Agent Architecture
> Version: 0.2.0

---

## 1. Overview

The `frontierx_brain` package is the central intelligence layer for the FrontierX multi-body robotics platform. It accepts natural-language commands, builds structured task plans, selects capable robot bodies, dispatches verified skills, monitors execution, stores task memory, and updates the world model from sensor and perception feedback.

The legacy `frontierx_robot_agent` package remains in the repository for earlier single-robot experiments, but the target architecture is the centralized `frontierx_brain` package.

The AI provider is abstracted behind an LLM/VLM interface. The platform can use OpenAI-compatible APIs, local models, or future VLA models without coupling task orchestration to one provider.

---

## 2. Brain Responsibilities

- Parse text, voice, API, and dashboard commands.
- Convert user intent into a Pydantic-validated `TaskPlan`.
- Query the world model for known objects, places, and recent observations.
- Use the robot and capability registries to select an appropriate body.
- Request verified skills such as `navigate_to`, `inspect`, `find_object`, `dock`, `arm_pick`, `arm_place`, and `aerial_scan`.
- Monitor execution feedback and re-plan when the environment or robot state changes.
- Record observations, findings, task history, and reports.

---

## 3. Safety Boundary

The LLM/VLM operates at the high-level planning layer only. It never communicates directly with `/cmd_vel`, PWM, torque, joint controllers, motor drivers, or actuator firmware.

Execution path:

1. AI output creates strict JSON matching the `TaskPlan` schema.
2. Pydantic validates structure and bounds.
3. Safety / Policy Supervisor checks action whitelist, forbidden low-level fields, geofence, battery, e-stop, and robot status.
4. Multi-Robot Orchestrator acquires a lease for the chosen body.
5. Skill Execution Engine dispatches only approved skill requests through the ROS 2 Bridge.
6. Robot-local controllers, watchdogs, and safety systems handle real-time motion.

---

## 4. Example

User command:

```text
Go to the generator, inspect it, identify anything abnormal, and return.
```

Expected plan shape:

```json
{
  "steps": [
    {"task_type": "navigate_to", "required_capabilities": ["navigate_ground"]},
    {"task_type": "inspect", "required_capabilities": ["thermal_inspection", "object_search"]},
    {"task_type": "navigate_to", "required_capabilities": ["navigate_ground"]},
    {"task_type": "report_status", "required_capabilities": []}
  ]
}
```

The brain chooses a capable body and requests skills. The body handles motor control, obstacle avoidance, emergency stop behavior, and hardware safety locally.
