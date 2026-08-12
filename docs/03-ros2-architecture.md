# FrontierX Multi-Body ROS 2 Architecture

> **Document:** 03 - ROS 2 Architecture  
> **Version:** 0.2.0  
> **Platform:** Central AI brain with multiple robot bodies

---

## 1. Overview

The **FrontierX** ROS 2 stack is organized around one central AI brain and multiple robot bodies communicating over DDS. The brain-side packages handle command parsing, planning, capability matching, skill execution, monitoring, and APIs. Body-side packages handle localization, navigation, perception, control, diagnostics, and local safety for each robot.

---

## 2. ROS 2 Package Summary

| Package Name | Type | Description |
|--------------|------|-------------|
| `frontierx_brain` | `ament_python` | Central AI command interface, planner, registries, policy supervisor, orchestrator, API gateway, ROS 2 bridge |
| `frontierx_interfaces` | `ament_cmake` | Custom msg, srv, and action definitions |
| `frontierx_robot_description` | `ament_cmake` | URDF/Xacro models, mesh geometries, TF tree, and RViz configs |
| `frontierx_bringup` | `ament_python` | Master launch files for simulation, navigation, and real hardware bringup |
| `frontierx_sim` | `ament_python` | Isaac Sim ROS 2 bridge connectors, synthetic sensor managers, Gazebo fallbacks |
| `frontierx_control` | `ament_cmake` | Body-local hardware interfaces, watchdogs, local safety, and low-level controllers |
| `frontierx_localization` | `ament_python` | EKF (`robot_localization`) state estimation, IMU/Odom calibration wrappers |
| `frontierx_mapping` | `ament_python` | SLAM Toolbox integration, map server, frontier-based auto exploration |
| `frontierx_navigation` | `ament_python` | Nav2 configuration, custom planner/controller plugins, waypoint follower |
| `frontierx_perception` | `ament_python` | YOLOv8 object detector, ByteTrack multi-object tracking, 3D spatial localizer |
| `frontierx_tasks` | `ament_python` | Verified skill/action servers exposed to the central brain |
| `frontierx_robot_agent` | `ament_python` | Legacy single-agent package; superseded by `frontierx_brain` for the multi-body architecture |
| `frontierx_diagnostics` | `ament_cmake` | Hardware safety monitor, watchdog node, E-Stop manager, health status publisher |
| `frontierx_data` | `ament_python` | Benchmark metric logging, automated bag recording, performance evaluation |
| `frontierx_visualization` | `ament_python` | RViz2 layouts, Foxglove Studio dashboards, 3D world model marker generator |

---

## 3. Topic Architecture

### 3.1 Sensor Data Topics

| Topic Name | Message Type | Publisher | Rate | QoS Profile | Description |
|------------|--------------|-----------|------|-------------|-------------|
| `/scan` | `sensor_msgs/LaserScan` | Sim / LiDAR Driver | 10 Hz | Sensor Data | 2D LiDAR range sweep |
| `/camera/image_raw` | `sensor_msgs/Image` | Sim / RGB Camera | 30 Hz | Sensor Data | Raw RGB camera frame (1280x720) |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Sim / Camera Driver | 30 Hz | Reliable | Intrinsic calibration parameters |
| `/camera/depth/image_raw` | `sensor_msgs/Image` | Sim / Depth Camera | 30 Hz | Sensor Data | 32-bit float depth image (640x480) |
| `/camera/depth/points` | `sensor_msgs/PointCloud2` | `depth_image_proc` | 15 Hz | Sensor Data | Projected 3D point cloud |
| `/imu/data` | `sensor_msgs/Imu` | Sim / IMU Driver | 100 Hz | Sensor Data | 6-DOF linear accel and gyro rates |
| `/odom` | `nav_msgs/Odometry` | Controller / Sim | 50 Hz | Sensor Data | Raw wheel encoder odometry |
| `/joint_states` | `sensor_msgs/JointState` | `robot_state_publisher` | 50 Hz | Reliable | Joint positions & velocities |

### 3.2 State Estimation & Mapping Topics

| Topic Name | Message Type | Publisher | Rate | Description |
|------------|--------------|-----------|------|-------------|
| `/odometry/filtered` | `nav_msgs/Odometry` | `ekf_node` | 50 Hz | Filtered robot state (Wheel + IMU fusion) |
| `/map` | `nav_msgs/OccupancyGrid` | `slam_toolbox` / `map_server` | 1 Hz | 2D grid map of environment |
| `/map_metadata` | `nav_msgs/MapMetaData` | `slam_toolbox` | Latched | Resolution, origin, and dimensions |
| `/tf` | `tf2_msgs/TFMessage` | Various nodes | Continuous | Dynamic coordinate transforms |
| `/tf_static` | `tf2_msgs/TFMessage` | `robot_state_publisher` | Static | Fixed sensor joint transforms |

### 3.3 Control & Actuation Topics

| Topic Name | Message Type | Publisher | Subscriber | Description |
|------------|--------------|-----------|------------|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 / Teleop | Safety Monitor | Raw velocity command input |
| `/cmd_vel_safe` | `geometry_msgs/Twist` | Safety Monitor | Motor Driver / Sim | Clipped, rate-limited safe command |
| `/e_stop` | `std_msgs/Bool` | User / Diagnostics | Safety Monitor | Hard emergency stop trigger |

### 3.4 Perception & World Model Topics

| Topic Name | Message Type | Publisher | Description |
|------------|--------------|-----------|-------------|
| `/perception/detections` | `frontierx_interfaces/DetectionArray` | `yolo_node` | 2D/3D object detections with bounding boxes |
| `/perception/tracks` | `frontierx_interfaces/DetectionArray` | `bytetrack_node` | Tracked multi-object state with IDs |
| `/perception/markers` | `visualization_msgs/MarkerArray` | Perception | RViz 3D visual bounding boxes |
| `/world_model` | `frontierx_interfaces/WorldModel` | `world_model_node` | Persistent 3D object registry & environment graph |

---

## 4. Service Architecture

| Service Name | Service Type | Server Node | Description |
|--------------|--------------|-------------|-------------|
| `/query_world_model` | `frontierx_interfaces/QueryWorldModel` | `world_model_node` | Query object location or properties |
| `/execute_task` | `frontierx_interfaces/ExecuteTask` | `task_executor_node` | Submit direct single-step command |
| `/set_navigation_mode` | `frontierx_interfaces/SetNavigationMode` | `navigation_manager` | Switch between SLAM, AMCL, and Explore |
| `/reset_robot` | `frontierx_interfaces/ResetRobot` | `safety_monitor_node` | Clear software faults and reset states |
| `/map_server/load_map` | `nav2_msgs/srv/LoadMap` | `map_server` | Reload saved occupancy map |
| `/slam_toolbox/save_map` | `slam_toolbox/srv/SaveMap` | `slam_toolbox` | Save active map to disk |

---

## 5. Action Architecture

| Action Name | Action Type | Action Server Node | Description |
|-------------|-------------|--------------------|-------------|
| `/navigate_to_goal` | `frontierx_interfaces/NavigateToGoal` | `nav2_bt_navigator` | High-level autonomous goal navigation |
| `/find_object` | `frontierx_interfaces/FindObject` | `task_executor_node` | Search environment and navigate to object |
| `/follow_person` | `frontierx_interfaces/FollowPerson` | `task_executor_node` | Follow tracked person maintaining distance |
| `/execute_task_plan` | `frontierx_interfaces/ExecuteTaskPlan` | `task_executor_node` | Execute multi-step LLM-generated JSON plan |
| `/dock` | `frontierx_interfaces/Dock` | `docking_node` | Autonomous docking at charging station |

---

## 6. Quality of Service (QoS) Strategy

1. **Sensor Data (High Frequency, Loss-Tolerant):**
   - Reliability: `BEST_EFFORT`
   - History: `KEEP_LAST`, Depth: 5
   - Durability: `VOLATILE`
   - Used for: `/scan`, `/camera/image_raw`, `/imu/data`, `/cmd_vel`

2. **State & Control (Reliable, Low-Latency):**
   - Reliability: `RELIABLE`
   - History: `KEEP_LAST`, Depth: 10
   - Durability: `VOLATILE`
   - Used for: `/odometry/filtered`, `/robot_health`, `/agent/command`

3. **Static Maps & Transforms (Latched Data):**
   - Reliability: `RELIABLE`
   - History: `KEEP_LAST`, Depth: 1
   - Durability: `TRANSIENT_LOCAL`
   - Used for: `/map`, `/tf_static`, `/camera/camera_info`
