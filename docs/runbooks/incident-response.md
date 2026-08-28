# Incident Response Runbook

> **Audience:** On-call engineers
> **Last updated:** 2026-08-29

---

## Incident Severity Levels

| Level | Description | Response SLA |
|-------|-------------|-------------|
| **P1 — Critical** | Robot physical safety risk, uncontrolled motion | Immediate |
| **P2 — High** | Fleet-wide outage, all robots offline | 15 min |
| **P3 — Medium** | Single robot unresponsive, degraded ops | 1 hour |
| **P4 — Low** | Dashboard unavailable, non-critical service down | 4 hours |

---

## Scenario 1: Robot Enters Safe State (EMERGENCY_STOP)

**Symptoms:** Robot stops moving, logs show `SAFE_STATE` or `EMERGENCY_STOP` mode.

**Immediate actions:**

```bash
# 1. Check safety monitor logs
docker logs frontierx_safety --tail 50

# 2. Check ROS 2 diagnostics topic
docker exec frontierx_ros2_core bash -c "
  source /opt/ros/humble/setup.bash &&
  source /opt/ros_ws/install/setup.bash &&
  ros2 topic echo /diagnostics --once"

# 3. Check network watchdog timeout
docker logs frontierx_ros2_core 2>&1 | grep -i "watchdog\|estop\|safe_state"
```

**Recovery steps:**

```bash
# Clear safe state by restarting safety monitor
docker restart frontierx_safety

# Verify robot cleared safe state
docker exec frontierx_ros2_core bash -c "
  source /opt/ros/humble/setup.bash &&
  ros2 topic echo /robot_status --once"
```

**Escalation:** If robot does not clear safe state after restart, perform physical hardware reset.

---

## Scenario 2: All Robots Disconnected from Cloud

**Symptoms:** Fleet dashboard shows 0 robots online.

```bash
# 1. Check DDS network
docker exec frontierx_ros2_core bash -c "
  source /opt/ros/humble/setup.bash && ros2 node list"

# 2. Check foxglove bridge
docker logs frontierx_foxglove --tail 30

# 3. Restart core stack in order
docker restart frontierx_ros2_core
sleep 10
docker restart frontierx_navigation frontierx_safety frontierx_foxglove
```

---

## Scenario 3: Navigation Stack Failure (Nav2 Down)

```bash
# Check navigation logs
docker logs frontierx_navigation --tail 50 | grep -i "error\|warn\|failed"

# Check if map is being received
docker exec frontierx_navigation bash -c "
  source /opt/ros/humble/setup.bash &&
  ros2 topic hz /map --window 5"

# Restart navigation
docker restart frontierx_navigation
```

---

## Scenario 4: LLM Agent Unresponsive

```bash
# Check ollama health
curl http://localhost:11435/api/tags

# Check agent logs
docker logs frontierx_agent --tail 50

# Restart ollama + agent
docker restart frontierx_ollama
sleep 30
docker restart frontierx_agent
```

---

## Collecting Diagnostics for Escalation

```bash
#!/bin/bash
# Run this script and attach the output to any escalation ticket
echo "=== FrontierX Diagnostic Dump ===" > /tmp/frontierx_diag.txt
echo "Timestamp: $(date -u)" >> /tmp/frontierx_diag.txt
docker ps >> /tmp/frontierx_diag.txt
echo "=== Container Logs ===" >> /tmp/frontierx_diag.txt
for c in frontierx_ros2_core frontierx_navigation frontierx_safety; do
  echo "--- $c ---" >> /tmp/frontierx_diag.txt
  docker logs "$c" --tail 100 2>&1 >> /tmp/frontierx_diag.txt
done
echo "Diagnostics saved to /tmp/frontierx_diag.txt"
```
