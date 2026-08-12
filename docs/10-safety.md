# FrontierX Safety Architecture

> Document: 10 - Safety Architecture
> Version: 0.2.0

---

## 1. Safety Architecture Overview

FrontierX separates centralized intelligence from body-local control. The central AI brain plans at the task and skill level. Each robot body owns real-time motor control, controller timing, emergency stop behavior, watchdogs, local obstacle avoidance, and hardware protection.

The `frontierx_brain.safety.policy_supervisor` module is the central deterministic gate before skill execution. The `frontierx_diagnostics` and `frontierx_control` packages provide robot-side health, watchdog, e-stop, and actuator safety behavior.

---

## 2. Non-Negotiable AI Boundary

The LLM/VLM must never directly control motors or low-level actuators. Forbidden AI plan fields include `cmd_vel`, PWM, torque, voltage, motor IDs, raw joint commands, and direct velocity-controller requests.

The AI may request only verified skills, for example navigation, inspection, search, docking, manipulation, aerial scan, wait, query world, and report status.

---

## 3. Central Policy Controls

- Action whitelist validation before execution.
- Forbidden low-level control parameter detection.
- Global emergency stop gate.
- Robot-local e-stop state gate.
- Battery threshold gate.
- Geofence validation for navigation and patrol skills.
- Parameter sanitization, including maximum velocity limits when a skill accepts them.
- Robot leases to prevent conflicting task ownership.

---

## 4. Body-Local Deterministic Controls

- Rate and velocity limiting for motion commands.
- Proximity halt guard using local perception or range sensors.
- Watchdog monitoring for command freshness and process health.
- Hardware emergency stop independent of the AI brain.
- Battery, thermal, and motor-driver protection.
- Local obstacle avoidance and collision prevention.

---

## 5. Failure Behavior

If a robot reports stale heartbeat, low battery, e-stop, fault, lost localization, blocked path, or unsafe local conditions, the central brain must stop dispatching new skills to that body and either re-plan with another capable body or ask for operator intervention.
