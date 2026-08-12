# FrontierX Scout — Navigation Architecture (Nav2)

> **Document:** 07 — Navigation Architecture  
> **Version:** 0.1.0

---

## 1. Overview

Autonomous movement for the FrontierX Scout is powered by **ROS 2 Nav2**. The stack manages global route planning, dynamic obstacle avoidance costmaps, path smoothing, and recovery behaviors.

---

## 2. Nav2 Component Configuration

- **Behavior Tree Navigator:** Uses `nav2_bt_navigator` to orchestrate navigation tasks.
- **Global Planner:** `NavfnPlanner` (A* / Dijkstra) generating optimal paths across the global costmap.
- **Local Controller:** `RegulatedPurePursuitController` tuned for small differential-drive kinematics ($v_{\max} = 0.5\text{ m/s}, \omega_{\max} = 1.0\text{ rad/s}$).
- **Costmaps:**
  - **Global Costmap:** Static map layer + scan obstacle layer + inflation layer ($0.55\text{ m}$ inflation radius).
  - **Local Costmap:** Rolling window $3\text{ m} \times 3\text{ m}$ @ $5\text{ Hz}$ for dynamic obstacle avoidance.
- **Recovery Behaviors:** Spin ($360^\circ$), Backup ($0.3\text{ m}$), Clear Costmap.
