# FrontierX Scout — Simulation Architecture (Isaac Sim)

> **Document:** 04 — Simulation Architecture  
> **Version:** 0.1.0  
> **Primary Simulator:** NVIDIA Isaac Sim (PhysX, RTX, USD, Omniverse)

---

## 1. Overview

FrontierX Labs adheres to a **simulation-first** engineering strategy. Before deploying to physical hardware, the entire robotics stack—including state estimation, SLAM, Nav2, 3D perception, persistent world modeling, and natural-language LLM planning—is validated in high-fidelity photorealistic simulations powered by **NVIDIA Isaac Sim**.

---

## 2. Simulation Environment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NVIDIA Isaac Sim                        │
│                                                             │
│  ┌──────────────────┐ ┌──────────────────┐ ┌─────────────┐  │
│  │ PhysX 5 Rigid    │ │ RTX Raytracing   │ │ USD Scene   │  │
│  │ Body Dynamics    │ │ Photoreal Camera │ │ Digital Twin│  │
│  └────────┬─────────┘ └────────┬─────────┘ └──────┬──────┘  │
│           │                    │                  │         │
│  ┌────────▼────────────────────▼──────────────────▼──────┐  │
│  │               Simulated FrontierX Scout               │  │
│  │  - Diff Drive Articulation                           │  │
│  │  - RTX Lidar Sensor                                  │  │
│  │  - RGB-D Camera Sensor                               │  │
│  │  - IMU Sensor Plugin                                 │  │
│  └─────────────────────────┬────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────┘
                             │ Omni ROS 2 Bridge (DDS)
┌────────────────────────────▼────────────────────────────────┐
│                    ROS 2 Middleware                         │
│  /scan  /camera/image_raw  /camera/depth/image_raw  /imu/data│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Sensor Models & Noise Configurations

To prevent building an idealized controller that fails on real physical hardware, synthetic noise models match commercial hardware specifications:

### 3.1 2D LiDAR (RTX Lidar)
- **Plugin:** `omni.isaac.ros2_bridge.ROS2Lidar`
- **Range:** 0.12 m – 12.0 m
- **Resolution:** 360 rays / 360° sweep (1.0° resolution)
- **Update Frequency:** 10 Hz
- **Noise:** Gaussian range noise ($\mu = 0.0$, $\sigma = 0.01\text{ m}$) + 0.5% random dropouts

### 3.2 RGB Camera (RTX Camera)
- **Resolution:** 1280 × 720 px @ 30 FPS
- **Field of View:** 69° Horizontal FOV
- **Noise:** Per-pixel chromatic noise + lens distortion parameters ($k_1, k_2, p_1, p_2$)

### 3.3 Depth Camera
- **Resolution:** 640 × 480 px @ 30 FPS
- **Effective Depth Range:** 0.3 m – 3.0 m
- **Noise:** Distance-squared noise model ($e(d) = 0.0015 \times d^2\text{ m}$)

### 3.4 IMU Sensor
- **Update Frequency:** 100 Hz
- **Gyroscope Noise Density:** $0.00014\text{ rad/s}/\sqrt{\text{Hz}}$, random walk $0.00001\text{ rad/s}^2/\sqrt{\text{Hz}}$
- **Accelerometer Noise Density:** $0.0016\text{ m/s}^2/\sqrt{\text{Hz}}$, random walk $0.00002\text{ m/s}^3/\sqrt{\text{Hz}}$

---

## 4. Digital Twin Environments

We maintain progressive USD test environments in `src/frontierx_sim/usd/`:

1. **Level 1 — Empty Room:** Ground plane, perimeter walls (base calibration).
2. **Level 2 — Furnished Office:** Tables, chairs, sofas, bookshelves (SLAM & Nav2 baseline).
3. **Level 3 — Warehouse Digital Twin:** Racks, pallets, cardboard boxes, charging dock (industrial benchmark).
4. **Level 4 — Dynamic Environment:** Moving human characters (Nav2 dynamic obstacle avoidance).

---

## 5. Sim-to-Real Pipeline

```
Simulation (Isaac Sim)
        ↓
Hardware-in-the-Loop (HIL) Testbed
        ↓
Low-Cost Physical Prototype (Jetson Orin Nano + RPLIDAR)
        ↓
Controlled Commercial Testing
```

Only the ROS 2 hardware bridge package (`frontierx_sim` vs `frontierx_control`) changes between Isaac Sim and the real robot. All high-level autonomy logic remains 100% identical.
