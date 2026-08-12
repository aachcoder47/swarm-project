# FrontierX Scout — Robot Description

> **Document:** 02 — Robot Description
> **Version:** 0.1.0

---

## 1. Overview

The **FrontierX Scout** is a small, compact differential-drive autonomous mobile robot designed for indoor environments. It is optimized for simulation-first development on NVIDIA Isaac Sim, with a clear path to deployment on low-cost physical hardware.

---

## 2. Physical Specification

| Parameter | Value |
|-----------|-------|
| Drive type | Differential (2 powered wheels) |
| Support | 2× passive caster wheels |
| Base dimensions (L×W×H) | 300mm × 250mm × 100mm (chassis) |
| Total height (with sensor mast) | ~360mm |
| Wheel diameter | 100mm |
| Wheel width | 30mm |
| Wheel separation (center-to-center) | 280mm |
| Simulation mass | ~3.5 kg |
| Max linear velocity | 0.5 m/s |
| Max angular velocity | 1.0 rad/s |

---

## 3. Sensor Suite

### 3.1 2D LiDAR
- **Frame:** `laser_frame`
- **Scan topic:** `/scan` (`sensor_msgs/LaserScan`)
- **Specification:**
  - 360° horizontal sweep
  - Range: 0.12m – 12.0m
  - Angular resolution: 1°
  - Update rate: 10 Hz
  - Noise: Gaussian (σ = 10mm)
- **Physical target:** RPLIDAR A2M8 / Sick TiM551
- **Position:** Top of sensor mast, z = +0.320m from base_footprint

### 3.2 RGB Camera
- **Frame:** `camera_link` / `camera_optical_frame`
- **Image topic:** `/camera/image_raw` (`sensor_msgs/Image`)
- **Camera info:** `/camera/camera_info` (`sensor_msgs/CameraInfo`)
- **Specification:**
  - Resolution: 1280 × 720
  - Frame rate: 30 FPS
  - Horizontal FOV: 69° (1.204 rad)
  - Noise: Gaussian (σ = 7 DN)
- **Physical target:** USB camera / IMX219
- **Position:** Front of chassis, x = +135mm, z = +70mm

### 3.3 Depth Camera
- **Frame:** `camera_depth_frame` / `camera_depth_optical_frame`
- **Depth topic:** `/camera/depth/image_raw`
- **Point cloud:** `/camera/depth/points` (`sensor_msgs/PointCloud2`)
- **Specification:**
  - Resolution: 640 × 480
  - Frame rate: 30 FPS
  - Horizontal FOV: 60° (1.047 rad)
  - Range: 0.3m – 3.0m
  - Noise: Gaussian (σ = 2mm)
- **Physical target:** Intel RealSense D435i
- **Position:** Co-located with RGB camera (15mm horizontal offset)

### 3.4 IMU
- **Frame:** `imu_link`
- **Topic:** `/imu/data` (`sensor_msgs/Imu`)
- **Specification:**
  - 6-DOF (3-axis accelerometer + 3-axis gyroscope)
  - Update rate: 100 Hz
  - Gyro noise: 0.00014 rad/s/√Hz
  - Accel noise: 0.0016 m/s²/√Hz
- **Physical target:** MPU-6050 / ICM-42688
- **Position:** Base center, z = +10mm

### 3.5 Wheel Encoders
- **Data source:** Joint states from motor controller
- **Topics:** `/joint_states` (`sensor_msgs/JointState`), `/odom` (`nav_msgs/Odometry`)
- **Joints:** `wheel_left_link_joint`, `wheel_right_link_joint`
- **Data:** Position (radians), velocity (rad/s)

---

## 4. TF Frame Tree

All frames follow **REP-103** (standard units) and **REP-105** (mobile robot frames).

```
map                     ← Global reference frame (produced by SLAM/AMCL)
└── odom                ← Odometry origin (continuous, no jumps)
    └── base_footprint  ← Robot's 2D ground projection (z = 0)
        └── base_link   ← Robot body center (+100mm above floor)
            ├── wheel_left_link           ← Left drive wheel
            ├── wheel_right_link          ← Right drive wheel
            ├── caster_front_link         ← Front caster (passive)
            ├── caster_rear_link          ← Rear caster (passive)
            ├── sensor_mast               ← Vertical sensor mast
            │   └── laser_frame           ← 2D LiDAR (top of mast)
            ├── camera_link               ← RGB camera body
            │   └── camera_optical_frame  ← Camera optical (REP-103: Z fwd)
            ├── camera_depth_frame        ← Depth camera body
            │   └── camera_depth_optical_frame ← Depth optical frame
            └── imu_link                  ← IMU sensor
```

### Frame Definitions

| Frame | Parent | Translation (xyz) | Rotation (rpy) | Notes |
|-------|--------|-------------------|----------------|-------|
| `base_footprint` | `odom` | (0,0,0) | (0,0,0) | Virtual, at ground |
| `base_link` | `base_footprint` | (0,0,0.100) | (0,0,0) | 100mm above floor |
| `wheel_left_link` | `base_link` | (0,+0.140,0) | (0,0,0) | Left drive wheel |
| `wheel_right_link` | `base_link` | (0,-0.140,0) | (0,0,0) | Right drive wheel |
| `caster_front_link` | `base_link` | (+0.120,0,-0.075) | (0,0,0) | Front caster |
| `caster_rear_link` | `base_link` | (-0.120,0,-0.075) | (0,0,0) | Rear caster |
| `sensor_mast` | `base_link` | (0,0,+0.100) | (0,0,0) | Structural |
| `laser_frame` | `sensor_mast` | (0,0,+0.220) | (0,0,0) | LiDAR |
| `camera_link` | `base_link` | (+0.135,0,+0.070) | (0,0,0) | RGB camera |
| `camera_optical_frame` | `camera_link` | (0,0,0) | (-π/2,0,-π/2) | Optical coords |
| `camera_depth_frame` | `camera_link` | (0,+0.015,0) | (0,0,0) | Depth camera |
| `camera_depth_optical_frame` | `camera_depth_frame` | (0,0,0) | (-π/2,0,-π/2) | Depth optical |
| `imu_link` | `base_link` | (0,0,+0.010) | (0,0,0) | IMU |

---

## 5. Inertia Parameters

All links have realistic inertia tensors computed from their geometry and mass.

| Link | Mass (kg) | Geometry | Notes |
|------|-----------|----------|-------|
| `base_link` | 2.500 | Box 300×250×100mm | Chassis + battery + compute |
| `sensor_mast` | 0.100 | Box 20×20×200mm | Aluminum extrusion |
| `wheel_left_link` | 0.200 | Cylinder r=50mm h=30mm | Including hub |
| `wheel_right_link` | 0.200 | Cylinder r=50mm h=30mm | Including hub |
| `caster_front_link` | 0.050 | Sphere r=25mm | Ball caster |
| `caster_rear_link` | 0.050 | Sphere r=25mm | Ball caster |
| `laser_frame` | 0.180 | Cylinder r=40mm h=40mm | RPLIDAR equiv. |
| `camera_link` | 0.070 | Box 25×90×25mm | Camera module |
| `imu_link` | 0.010 | Box 20×20×5mm | IMU board |
| **Total** | **~3.56 kg** | — | Matches target spec |

---

## 6. Collision Model

- Chassis: simplified box geometry
- Wheels: cylinder geometry (exact)
- Casters: sphere geometry (exact)
- Sensor mast: box geometry
- Camera: box geometry

All collision meshes are deliberately simple for computational efficiency in simulation. High-fidelity visual meshes (if any) are in `meshes/visual/`.

---

## 7. ros2_control Interface

The robot uses `ros2_control` for hardware abstraction:

- **Controller:** `diff_drive_controller/DiffDriveController`
- **Command interface:** `velocity` (rad/s per wheel)
- **State interfaces:** `position` (rad), `velocity` (rad/s)
- **Hardware plugin (sim):** `frontierx_control/ScoutHardwareInterface` (Isaac Sim bridge)
- **Hardware plugin (real):** `frontierx_control/ScoutHardwareInterfaceReal` (serial to motor driver)

---

## 8. URDF Files

| File | Purpose |
|------|---------|
| `urdf/scout.urdf.xacro` | Master assembly file |
| `urdf/scout_base.xacro` | Chassis, wheels, casters, ros2_control |
| `urdf/scout_sensors.xacro` | All sensor links, joints, noise params |
| `urdf/scout_gazebo.xacro` | Gazebo/Isaac Sim simulation plugins |

---

## 9. Validation

Run URDF validation (requires Ubuntu + ROS 2):

```bash
# Process Xacro to URDF
xacro src/frontierx_robot_description/urdf/scout.urdf.xacro > /tmp/scout.urdf

# Validate URDF structure and TF tree
check_urdf /tmp/scout.urdf

# View in RViz2
ros2 launch frontierx_robot_description display.launch.py

# Check TF tree
ros2 run tf2_tools view_frames
```

---

## Related Documents

- [01 — System Architecture](01-system-architecture.md)
- [03 — ROS 2 Architecture](03-ros2-architecture.md)
- [06 — Localization](06-localization.md)
