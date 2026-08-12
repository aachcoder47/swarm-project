# FrontierX Scout — Development Roadmap

> **Simulation-first autonomous mobile robotics platform**
> Built by FrontierX Labs

---

## Guiding Principle

> Build a technically credible autonomous robotics platform in simulation first.
> Measure everything. Publish the work. Then transfer to hardware.

---

## Phase 0 — Foundations *(Month 1)*

**Goal:** Establish the development environment and core competencies.

### Deliverables
- [ ] Ubuntu 22.04 LTS development environment
- [ ] ROS 2 Humble installed and configured
- [ ] Docker + NVIDIA Container Toolkit
- [ ] Git / GitHub organization
- [ ] Complete repository scaffold
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] `ros2 run demo_nodes_cpp talker` running in Docker
- [ ] All documentation structure in place

### Skills
- Linux command line
- Git / GitHub workflow
- Python 3 / C++17 basics
- ROS 2 concepts (nodes, topics, services, actions)
- Docker fundamentals

### Exit Criteria
✅ Developer can spin up ROS 2 Humble in Docker on a fresh machine in under 10 minutes.

---

## Phase 1 — Isaac Sim + Robot Model *(Month 2)*

**Goal:** FrontierX Scout spawns in Isaac Sim with all sensors publishing to ROS 2 topics.

### Deliverables
- [ ] NVIDIA Isaac Sim configured with ROS 2 bridge
- [ ] FrontierX Scout URDF/Xacro complete
- [ ] All sensors publishing:
  - `/scan` (LiDAR)
  - `/camera/image_raw` (RGB)
  - `/camera/depth/image_raw` (Depth)
  - `/imu/data` (IMU)
  - `/joint_states` (Encoders)
- [ ] TF tree correct: `map → odom → base_footprint → base_link → sensors`
- [ ] RViz2 visualization of Scout + all sensor data
- [ ] USD scene: empty room test environment

### Exit Criteria
✅ Scout spawns in Isaac Sim. All 5 sensor streams visible in RViz2. TF tree has zero broken links.

---

## Phase 2 — ROS 2 Bridge + Teleoperation *(Month 3)*

**Goal:** Scout can be teleoperated via keyboard with correct odometry and TF.

### Deliverables
- [ ] Isaac Sim ↔ ROS 2 full bidirectional bridge
- [ ] Keyboard teleoperation (`teleop_twist_keyboard`)
- [ ] Differential-drive controller publishing `/odom`
- [ ] Joint state publisher
- [ ] TF broadcaster (`odom → base_footprint`)
- [ ] Twist multiplexer (priority: e-stop > task > teleop)
- [ ] Emergency stop topic (`/e_stop`)

### Exit Criteria
✅ Scout drives in Isaac Sim, odometry tracks motion, TF updates in real-time. E-stop halts motion immediately.

---

## Phase 3 — Odometry + EKF Localization *(Month 4)*

**Goal:** Accurate robot state estimation fusing wheel odometry and IMU.

### Deliverables
- [ ] `robot_localization` EKF node fusing `/odom` + `/imu/data`
- [ ] Odometry drift characterization over 5m / 10m
- [ ] Position error < 5cm over 5m straight-line path
- [ ] Heading error < 2° over 90° turn
- [ ] Automated evaluation script with metrics
- [ ] Benchmark report: odometry accuracy

### Exit Criteria
✅ EKF-filtered odometry error < 5cm / 5m. Automated benchmark passes.

---

## Phase 4 — SLAM Autonomous Mapping *(Month 5)*

**Goal:** Scout can autonomously explore and build a map of an unknown environment.

### Deliverables
- [ ] SLAM Toolbox (online async) integrated
- [ ] Manual exploration mode (drive while mapping)
- [ ] Map save (`/map_saver_server`)
- [ ] Map reload + localization with saved map
- [ ] Isaac Sim test environment: furnished room (Level 2)
- [ ] Mapping accuracy evaluation vs ground truth
- [ ] Benchmark: mapping time, accuracy, CPU usage

### Exit Criteria
✅ Scout maps a 10m×10m room. Map saved, reloaded. Localization error < 10cm against saved map.

---

## Phase 5 — Nav2 Autonomous Navigation *(Month 6)*

**Goal:** Scout navigates autonomously to goals, avoiding static obstacles.

### Deliverables
- [ ] Nav2 stack (BT navigator, AMCL, global + local planners, costmaps)
- [ ] Navigate to 5 waypoints with 0 collisions
- [ ] Static obstacle avoidance (furniture, walls)
- [ ] Recovery behaviors (spin, backup, clear costmap)
- [ ] Re-planning on blocked path
- [ ] Test environments: Level 1 (empty), Level 2 (furniture), Level 3 (obstacles)
- [ ] Benchmark: success rate, path length, time to goal, collision count

### Exit Criteria
✅ 5/5 goal success rate in furnished room. 0 collisions. Re-planning on blocked path verified.

---

## Phase 6 — Computer Vision + Perception *(Month 7)*

**Goal:** Scout detects, classifies, and tracks objects in its camera stream.

### Deliverables
- [ ] YOLOv8 integration (ROS 2 node)
- [ ] ByteTrack multi-object tracking
- [ ] Object depth estimation (camera + depth fusion)
- [ ] 3D object pose in robot frame
- [ ] Detection topics: `/perception/detections`, `/perception/tracks`
- [ ] Synthetic training data from Isaac Sim
- [ ] Benchmark: mAP on common objects (chair, table, box, person)

### Exit Criteria
✅ mAP > 80% on 10 object classes in Isaac Sim. Tracking ID stable across 30-frame occlusion. FPS > 20.

---

## Phase 7 — Sensor Fusion + World Model *(Month 8)*

**Goal:** Scout maintains a persistent, spatially-aware world model.

### Deliverables
- [ ] LiDAR + Camera + Depth fusion
- [ ] Object localization in map frame (3D pose per detected object)
- [ ] World model node: persistent object registry
- [ ] World model API: `QueryWorldModel` service
- [ ] Object localization error < 10cm
- [ ] World model persists across navigation sessions
- [ ] Visualization: world objects in RViz2 as markers

### Exit Criteria
✅ Scout detects 5 objects, localizes each to < 10cm in map frame. World model reloads correctly after restart.

---

## Phase 8 — Object-Aware Navigation *(Month 9)*

**Goal:** Scout can navigate to named objects in the world model.

### Deliverables
- [ ] CLI command: `ros2 action send_goal /find_object ...`
- [ ] Find-object behavior: search if unknown, navigate if known
- [ ] Object-goal navigation: drive to within 0.5m of object
- [ ] Object verification on arrival (visual confirmation)
- [ ] Test environment: Level 4 (moving obstacles)
- [ ] Dynamic obstacle avoidance upgrade

### Exit Criteria
✅ "Find the red box" command locates and navigates to target in < 60s. 5/5 success rate.

---

## Phase 9 — Persistent World Model *(Month 10)*

**Goal:** World model and maps persist across full system restarts.

### Deliverables
- [ ] SQLite / JSON world model persistence
- [ ] Map + object state serialization / deserialization
- [ ] Session continuity: objects known from previous run
- [ ] World model update on re-detection
- [ ] Stale object handling (TTL, re-verification)
- [ ] Test: 5 full restart cycles, objects retained

### Exit Criteria
✅ 100% object retention across 5 restarts. Stale object correctly marked after 60s absence.

---

## Phase 10 — AI Robot Agent *(Month 11)*

**Goal:** Natural-language commands drive autonomous behavior via structured AI agent.

### Deliverables
- [ ] ollama + LLaMA 3.1 8B local inference
- [ ] FrontierX Robot Agent: LLM → structured task plan → ROS 2
- [ ] Agent tools: `navigate_to`, `find_object`, `follow_person`, `patrol`, `dock`, `report_status`
- [ ] Safety validator between LLM output and robot actions
- [ ] CLI chat interface
- [ ] Web interface for commands
- [ ] Voice input (optional, whisper.cpp)

### Example commands working
```
"Go to the kitchen"
"Find the red box"
"Follow me"
"Patrol the room"
"Report status"
```

### Exit Criteria
✅ 8/10 NL commands correctly understood and executed in Isaac Sim. Safety layer blocks 100% of invalid actions.

---

## Phase 11 — Full MVP Demo *(Month 12)*

**Goal:** Complete, recorded demonstration of all 20 MVP capabilities.

### Demo Scenario
**User:** *"Find the red box and take me to it."*

```
Understand command
      ↓
Search world model
      ↓
If unknown → explore and search
      ↓
Navigate to object
      ↓
Avoid obstacles dynamically
      ↓
Verify object visually
      ↓
Arrive within 0.5m
      ↓
Report: "I found the red box at position (x,y). Arrived."
```

### MVP Checklist
- [ ] Custom robot model in Isaac Sim
- [ ] ROS 2 integration
- [ ] RGB camera, depth camera, LiDAR, IMU, odometry
- [ ] EKF localization
- [ ] SLAM mapping
- [ ] Autonomous navigation (Nav2)
- [ ] Static + dynamic obstacle avoidance
- [ ] YOLOv8 object detection
- [ ] ByteTrack object tracking
- [ ] Sensor-fused world model
- [ ] Task planner
- [ ] Natural-language interface
- [ ] Safety layer
- [ ] Autonomous task execution
- [ ] Performance benchmarks published
- [ ] Digital-twin environment
- [ ] Demo video published
- [ ] Technical blog post published
- [ ] GitHub repository public

### Exit Criteria
✅ Full 5-minute recorded demo. All 20 MVP criteria verified. Public GitHub repository with documentation live.

---

## Phase 8+ — Physical Hardware *(Post Month 12)*

**Goal:** Transfer validated simulation stack to low-cost physical hardware.

### Target Platform
- NVIDIA Jetson Orin Nano (compute)
- Raspberry Pi / STM32 (motor control)
- RPLIDAR A1M8 (LiDAR)
- Intel RealSense D435i (RGB-D + IMU)
- DC gear motors + encoders
- Custom chassis (3D printed initially)

### Sim-to-Real Strategy
1. Only hardware interface layer changes
2. All autonomy logic unchanged
3. Hardware-in-the-loop testing
4. Controlled indoor environment first
5. Iterative real-world validation

---

## Performance Targets (MVP)

| Metric | Target |
|--------|--------|
| Navigation success rate | > 90% |
| Collision rate | < 1 per 10 goals |
| Localization error | < 10cm |
| Object detection mAP | > 80% |
| Perception FPS | > 20 Hz |
| Task completion (NL commands) | > 80% |
| Safety layer effectiveness | 100% invalid actions blocked |
| System startup time | < 60s |

---

## Long-Term Vision (2027+)

```
FrontierX Scout (Consumer)
        ↓
FrontierX Patrol (Inspection)
        ↓
FrontierX Arm (Manipulation)
        ↓
FrontierX Industrial
        ↓
FrontierX Semiconductor Integration
        ↓
Fully Proprietary Hardware Stack
```

---

*Last updated: August 2026 | FrontierX Labs*
