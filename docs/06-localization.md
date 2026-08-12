# FrontierX Scout — Localization & SLAM

> **Document:** 06 — Localization & SLAM  
> **Version:** 0.1.0

---

## 1. Overview

Localization and mapping form the spatial state estimation backbone of the FrontierX Scout. We employ a dual-layer approach:
1. **Continuous State Estimation:** Extended Kalman Filter (EKF via `robot_localization`) fusing raw wheel odometry and 6-DOF IMU data.
2. **Global Map-Based Localization / Mapping:** `SLAM Toolbox` for active online mapping, and `AMCL` / `SLAM Toolbox Localization Mode` for navigating existing maps.

---

## 2. EKF State Estimation (`robot_localization`)

The EKF node fuses wheel encoder telemetry (`/odom`) and IMU sensor data (`/imu/data`) at 50 Hz.

### 2.1 Fused State Vector
$$\mathbf{x} = \begin{bmatrix} x & y & \theta & \dot{x} & \dot{\theta} & \ddot{x} \end{bmatrix}^T$$

### 2.2 Performance Benchmarks Target
- **Position Drift:** $< 5\text{ cm}$ per $5\text{ m}$ linear translation
- **Heading Error:** $< 2.0^\circ$ per $90^\circ$ rotation

---

## 3. SLAM Toolbox Mapping

Mapping uses **SLAM Toolbox** (Online Async mode), utilizing Ceres solver for graph relaxation and scan matching.

### 3.1 Mapping Workflow
1. **Start:** Launch robot in an unmapped environment (`mode:=mapping`).
2. **Explore:** Teleoperate or run autonomous frontier exploration node.
3. **Build Graph:** LiDAR scans match against occupancy grid pose graph.
4. **Save Map:** Service call `/slam_toolbox/save_map` writes `.yaml` + `.pgm` grid files.
5. **Reload:** Load map in `mode:=localization` for Nav2 operation.
