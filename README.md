<div align="center">

<img src="docs/assets/frontierx_logo.svg" alt="FrontierX Labs" width="120"/>

# FrontierX - Central AI Multi-Body Robotics Platform

**FrontierX Labs** | Robotics · Autonomous Systems · Embedded Systems · Semiconductor Research

[![ROS 2 Humble](https://img.shields.io/badge/ROS%202-Humble-blue?logo=ros)](https://docs.ros.org/en/humble/)
[![Isaac Sim](https://img.shields.io/badge/NVIDIA-Isaac%20Sim-76B900?logo=nvidia)](https://developer.nvidia.com/isaac-sim)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)
[![Build](https://github.com/frontierx-labs/frontierx-robotics/actions/workflows/ros2-build.yml/badge.svg)](.github/workflows/ros2-build.yml)

> *One centralized AI brain coordinating many capability-based robot bodies, from simulation to physical fleets.*

[**Documentation**](docs/) · [**Roadmap**](ROADMAP.md) · [**Dashboard**](dashboard/index.html) · [**Contributing**](CONTRIBUTING.md)

</div>

---

## What Is FrontierX?

**FrontierX** is a deep-tech robotics platform built around one centralized AI brain and multiple heterogeneous robot bodies connected wirelessly through ROS 2/DDS and IP networking. The central brain understands natural-language commands, reasons about tasks, selects the right body by capability, dispatches verified skills, monitors execution, consumes sensor feedback, updates a world model, and re-plans when needed.

The system treats each robot as a capability-based body rather than hard-coding intelligence to one robot. The first body is **FrontierX Scout**, a wheeled UGV for simulation-first autonomy work. The architecture is designed to expand to tracked robots, robotic arms, quadrupeds, drones, and future custom bodies.

The LLM/VLM layer is intentionally isolated from low-level control. It can request approved skills such as navigation, inspection, docking, manipulation, object search, aerial scan, and reporting. It must never directly command motors, PWM, torque, velocity controllers, or actuator loops. Real-time motor control and safety remain local to each robot body.

### Platform Capabilities

| Capability | Status |
|------------|--------|
| Central AI command interface | In progress |
| Provider-neutral LLM/VLM abstraction | In progress |
| Robot registry and capability matching | In progress |
| Skill execution engine | In progress |
| Multi-robot orchestration and leases | In progress |
| Safety and policy supervisor | In progress |
| World model and task memory | In progress |
| ROS 2 bridge for approved skills | In progress |
| Sensor data and perception pipeline | In progress |
| Isaac Sim simulation interface | In progress |
| Nav2 ground navigation | Planned |
| MoveIt 2 manipulation support | Planned |
| Web dashboard and API gateway | In progress |

---

## Architecture Overview

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

## Repository Structure

```text
frontierx-robotics/
|-- src/
|   |-- frontierx_brain/             # Central AI brain, planner, registries, orchestration, APIs
|   |-- frontierx_interfaces/        # Custom ROS 2 msgs, srvs, actions
|   |-- frontierx_robot_description/ # Body descriptions, URDF/Xacro, meshes, TF
|   |-- frontierx_bringup/           # Master launch files
|   |-- frontierx_sim/               # Isaac Sim / Gazebo integration
|   |-- frontierx_control/           # Robot-side control, watchdogs, safety
|   |-- frontierx_localization/      # EKF, AMCL config
|   |-- frontierx_mapping/           # SLAM Toolbox nodes
|   |-- frontierx_navigation/        # Nav2 configuration
|   |-- frontierx_perception/        # Camera/LiDAR pipeline, detection, tracking
|   |-- frontierx_tasks/             # Verified skills and action servers
|   |-- frontierx_robot_agent/       # Legacy single-agent package, being superseded by frontierx_brain
|   |-- frontierx_diagnostics/       # Health monitor, safety watchdog
|   |-- frontierx_data/              # Benchmarks, bag recording
|   `-- frontierx_visualization/     # RViz2, Foxglove layouts
|-- config/                          # Nav2, localization, SLAM, perception, robot configs
|-- docker/                          # Dockerfile + Compose stack
|-- docs/                            # Architecture documents
|-- dashboard/                       # Web project dashboard
|-- scripts/                         # Setup, build, test scripts
|-- tests/                           # Integration tests
`-- .github/workflows/               # CI/CD pipelines
```

---

## Quick Start

### Prerequisites

- Ubuntu 22.04 LTS (or WSL2 on Windows)
- NVIDIA GPU with CUDA 12.x
- Docker + Docker Compose
- NVIDIA Container Toolkit
- NVIDIA Omniverse account (free) for Isaac Sim

### 1. Clone the repository

```bash
git clone https://github.com/frontierx-labs/frontierx-robotics.git
cd frontierx-robotics
```

### 2. Run setup

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 3. Build Docker stack

```bash
cp docker/.env.example docker/.env
# Edit docker/.env with your paths
docker compose -f docker/docker-compose.yml build
```

### 4. Launch simulation

```bash
./scripts/launch_sim.sh
```

### 5. Build ROS 2 workspace

```bash
./scripts/build.sh
source install/setup.bash
```

### 6. View in browser (Windows-compatible)

Open `dashboard/index.html` in any browser to see the project dashboard.

---

## First Body: Scout UGV Specification

**FrontierX Scout** is the first supported robot body: a differential-drive UGV used for simulation-first development and ground-navigation skills.

| Parameter | Value |
|-----------|-------|
| Drive type | Differential (2-wheel) |
| Support | 2× caster wheels |
| Base footprint | 300mm × 250mm |
| Height | ~360mm (with sensor mast) |
| Sim mass | ~3.5 kg |
| Max velocity | 0.5 m/s |
| Max angular velocity | 1.0 rad/s |
| LiDAR | 360° 2D, 12m range |
| RGB Camera | 1280×720, 30 FPS, 69° FOV |
| Depth Camera | 640×480, 30 FPS, 0.3–3.0m |
| IMU | 6-DOF, 100 Hz |
| Compute (sim) | NVIDIA GPU (Isaac Sim) |
| Compute (target) | NVIDIA Jetson Orin Nano |

---

## Development Phases

See [ROADMAP.md](ROADMAP.md) for the full 12-month plan.

| Phase | Focus | Target |
|-------|-------|--------|
| 0 | Foundations | Month 1 |
| 1 | Isaac Sim + URDF | Month 2 |
| 2 | ROS 2 bridge + teleop | Month 3 |
| 3 | Odometry + EKF | Month 4 |
| 4 | SLAM | Month 5 |
| 5 | Nav2 | Month 6 |
| 6 | Perception | Month 7 |
| 7 | Sensor fusion | Month 8 |
| 8 | Object-aware nav | Month 9 |
| 9 | World model | Month 10 |
| 10 | AI agent | Month 11 |
| 11 | Full MVP demo | Month 12 |

---

## Documentation

| Document | Description |
|----------|-------------|
| [01 — System Architecture](docs/01-system-architecture.md) | Full system overview |
| [02 — Robot Description](docs/02-robot-description.md) | URDF, frames, sensors |
| [03 — ROS 2 Architecture](docs/03-ros2-architecture.md) | Nodes, topics, services, actions |
| [04 — Simulation](docs/04-simulation.md) | Isaac Sim setup and configuration |
| [05 — Perception](docs/05-perception.md) | Camera pipeline, YOLO, tracking |
| [06 — Localization](docs/06-localization.md) | EKF, odometry, AMCL |
| [07 — Navigation](docs/07-navigation.md) | Nav2, planners, costmaps |
| [08 — Task Planning](docs/08-task-planning.md) | Task executor, BT |
| [09 — AI Agent](docs/09-ai-agent.md) | LLM agent, tools, safety |
| [10 — Safety](docs/10-safety.md) | Safety architecture |
| [11 — Testing](docs/11-testing.md) | Test strategy, benchmarks |
| [12 — Sim-to-Real](docs/12-sim-to-real.md) | Physical deployment |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Simulator | NVIDIA Isaac Sim (PhysX, RTX) |
| Middleware | ROS 2 Humble |
| SLAM | SLAM Toolbox |
| Navigation | Nav2 |
| Localization | robot_localization (EKF) |
| Perception | YOLOv8, OpenCV, PyTorch, TensorRT |
| Tracking | ByteTrack |
| AI Agent | LLama 3.1 via ollama + custom tools |
| Languages | Python 3.10, C++17 |
| Containers | Docker + Compose |
| CI/CD | GitHub Actions |
| Visualization | RViz2, Foxglove Studio |

---

## License

Apache License 2.0 — See [LICENSE](LICENSE)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<div align="center">

**FrontierX Labs** — *Building the machines of tomorrow.*

[frontierxlabs.com](https://frontierxlabs.com) · [GitHub](https://github.com/frontierx-labs) · [YouTube](https://youtube.com/@frontierxlabs)

</div>
"# swarm-project" 
